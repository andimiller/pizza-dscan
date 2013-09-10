import sqlite3
import re
import datetime
import json

isinteresting = lambda x:x["group"] is not None

class DScan():
	def __init__(self, redisdb):
		self.redisdb = redisdb
		self.db = sqlite3.connect('ody11-sqlite3-v1.db')
		c = self.db.cursor()
		for row in c.execute("select distinct invTypes.typeName, invGroups.groupName, invCategories.categoryName from invTypes, invGroups, invCategories WHERE invGroups.groupID=invTypes.groupID AND invCategories.categoryID=invGroups.categoryID"):
			self.redisdb[row[0]] = json.dumps((row[1] or None, row[2] or None))
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

	def total(self, data):
		categorywide = {}
		sums = {}
		categories = {}
		groups = {}
		for line in data:
			typen = line["type"]
			category = line["category"]
			group = line["group"]
			if category not in categorywide:
				categorywide[category] = {}
			if typen in categorywide[category]:
				categorywide[category][typen] += 1
			else:
				categorywide[category][typen] = 1
			if category not in sums:
				sums[category] = 1
			else:
				sums[category] += 1
			if group not in groups:
				groups[group] = {}
			if typen in groups[group]:
				groups[group][typen] += 1
			else:
				groups[group][typen]=1

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
		systemname = self.getsystemname(data)
		data = filter(isinteresting, data)
		categorywide, sums, categories, groups = self.total(data)
		categories = self.sort(categories)
		groups = self.sort(groups)
		categorywide = self.sort(categorywide)
		return categorywide, sums, categories, groups, systemname
