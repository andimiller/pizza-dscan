import sqlite3
import re
import datetime
import json
import redis_wrap

isinteresting = lambda x:x["group"] is not None

class DScan():
	def __init__(self):
		self.redisdb = redis_wrap.get_hash('dscan_categories')
		self.redis_sizes = redis_wrap.get_hash('dscan_sizes')
		self.redis_systems = redis_wrap.get_hash('dscan_systems')
		self.db = sqlite3.connect('sqlite-latest.sqlite')
		c = self.db.cursor()
		for row in c.execute("select distinct invTypes.typeName, invGroups.groupName, invCategories.categoryName from invTypes, invGroups, invCategories WHERE invGroups.groupID=invTypes.groupID AND invCategories.categoryID=invGroups.categoryID"):
			try:
				self.redisdb[row[0]] = json.dumps((row[1] or None, row[2] or None))
			except:
				print "could not load row for %s" % row[0]
		for row in c.execute("select invTypes.typeName, dgmTypeAttributes.valueFloat from invTypes, dgmTypeAttributes where dgmTypeAttributes.typeID=invTypes.typeID and dgmTypeAttributes.attributeID=1547"):
			self.redis_sizes[row[0]] = int(row[1])
		for row in c.execute("select mapRegions.regionName, mapSolarSystems.solarSystemName from mapRegions, mapSolarSystems where mapRegions.regionID=mapSolarSystems.regionID"):
			self.redis_systems[row[1]] = row[0]
		c.close()
		print "Database loaded"

	def categorise(self, line):
		result = {}
		result["name"] = line[0]
		result["type"] = line[1]
		result["distance"] = line[2]
		group = json.loads(self.redisdb[result["type"]])
		result["group"] = str(group) and group[0] or None
		result["category"] = str(group) and group[1] or None
		return result

	def buildsizes(self, data):
		sizes = {
				"Frigates": {},
				"Destroyers": {},
				"Cruisers": {},
				"Battlecruisers": {},
				"Battleships": {},
				"Capitals": {},
				"Supercapitals": {}
		}
		for line in data:
			typen = line["type"]
			category = line["category"]
			group = line["group"]
			if line["type"] not in self.redis_sizes:
				continue
			rigsize = int(self.redis_sizes[line["type"]])
			if rigsize==1:
				if group in ["Inderdictor", "Destroyer"]:
					if typen in sizes["Destroyers"]:
						sizes["Destroyers"][typen]+=1
					else:
						sizes["Destroyers"][typen]=1
				else:
					if typen in sizes["Frigates"]:
						sizes["Frigates"][typen]+=1
					else:
						sizes["Frigates"][typen]=1
			if rigsize==2:
				if group in ["Battlecruiser", "Attack Battlecruiser", "Command Ship"]:
					if typen in sizes["Battlecruisers"]:
						sizes["Battlecruisers"][typen]+=1
					else:
						sizes["Battlecruisers"][typen]=1
				else:
					if typen in sizes["Cruisers"]:
						sizes["Cruisers"][typen]+=1
					else:
						sizes["Cruisers"][typen]=1
			if rigsize==3:
				if typen in sizes["Battleships"]:
					sizes["Battleships"][typen]+=1
				else:
					sizes["Battleships"][typen]=1
			if rigsize==4:
				if group in ["Titan", "Supercarrier"]:
					if typen in sizes["Supercapitals"]:
						sizes["Supercapitals"][typen]+=1
					else:
						sizes["Supercapitals"][typen]=1
				else:
					if typen in sizes["Capitals"]:
						sizes["Capitals"][typen]+=1
					else:
						sizes["Capitals"][typen]=1
		return sizes




	def total(self, data):
		categorywide = {}
		sums = {}
		categories = {}
		groups = {}
		for line in data:
			typen = line["type"]
			category = line["category"]
			group = line["group"]
			# large categories
			if category not in categorywide:
				categorywide[category] = {}
			if typen in categorywide[category]:
				categorywide[category][typen] += 1
			else:
				categorywide[category][typen] = 1
			# sums
			if category not in sums:
				sums[category] = 1
			else:
				sums[category] += 1
			# groups
			if group not in groups:
				groups[group] = {}
			if typen in groups[group]:
				groups[group][typen] += 1
			else:
				groups[group][typen]=1
			# categories of groups
			if category not in categories:
				categories[category] = {}
			if group in categories[category]:
				categories[category][group] += 1
			else:
				categories[category][group] = 1
		return categorywide, sums, categories, groups

	def colourize(self, m):
		def f(x):
			colourmap = [
					(0.0*m, "-muted"),
					(0.2*m, ""),
					(0.4*m, ""),
					(0.6*m, "-warning"),
					(0.8*m, "-danger")
			]
			result = ""
			for size, value in colourmap:
				if x<size:
					return result
				else:
					result = value
			return result
		return f

	def sort(self, results):
		finalresults = {}
		for category in results:
			r = results[category]
			maximum = max(r.values())
			c = self.colourize(maximum)
			res = sorted(r.items(), key=lambda x:-x[1])
			tuples = []
			for r in res:
				tuples.append((r[0],r[1], c(r[1])))
			finalresults[category] = tuples

		return finalresults

	def getsystemname(self, data):
		namesources = {
				"Moon": lambda x:x.split()[:-4],
				"Planet": lambda x:x.split()[:-1],
				"Sun": lambda x:x.split()[:-2]
				}
		for item in data:
			if item["group"] in namesources:
				name = " ".join(namesources[item["group"]](item["name"]))
				return name
		return None

	def parseDscan(self, data):
		data = map(lambda x:x.split("\t"), data.split("\n"))
		data = filter(lambda x:len(x)==3 , data)
		data = map(self.categorise, data)
		systemname=self.getsystemname(data)
		if systemname:
			region = self.redis_systems[systemname]
			systemname = (systemname, region)
		data = filter(isinteresting, data)
		categorywide, sums, categories, groups = self.total(data)
		categories = self.sort(categories)
		groups = self.sort(groups)
		categorywide = self.sort(categorywide)
		sizes = self.buildsizes(data)
		sizestotal = 0
		for size in sizes:
			sizestotal+=sum(sizes[size].values())


		results = {"categorywide" : categorywide, "sums" : sums, "categories" : categories, "groups": groups, "system" : systemname, "sizemap": sizes, "sizestotal": sizestotal}

		return json.dumps(results)
