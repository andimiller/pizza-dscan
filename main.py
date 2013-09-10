import json
from flask import Flask, flash, session, render_template, redirect, request, abort, url_for, escape
import redis_wrap

from dscan import DScan
import string, random

app = Flask(__name__)

# Load configuration
with open("config.json") as fh:
	config=json.loads(fh.read())
assert(config)
app.config.update(config)

dscan = DScan(redis_wrap.get_hash('dscan_categories'))
store = redis_wrap.get_hash('dscan')

@app.route('/', methods=["GET", "POST"])
def dscanmake():
	if request.method=="GET":
		return render_template("dscan.html")
	if request.method=="POST":
		categorywide, sums, categories, groups, system = dscan.parseDscan(request.form["dscandata"])
		token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(24))
		while token in store:
			token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(24))
		store[token] = json.dumps({"categorywide" : categorywide, "sums" : sums, "categories" : categories, "groups": groups, "system" : system})
		return redirect("/view/"+token)

@app.route('/view/<id>')
def dscanview(id):
	data = json.loads(store[id])
	categorywide = data["categorywide"]
	sums = data["sums"]
	categories = data["categories"]
	groups = data["groups"]
	system = data["system"]
	categorylist = categories.keys()
	print categorylist
	if "Ship" in categorylist:
		categorylist.remove("Ship")
		categorylist = ["Ship"] + sorted(categorylist)
	else:
		categorylist = sorted(categorylist)
	return render_template("dscan_results.html", categorylist=categorylist, categorywide=categorywide, sums=sums, categories=categories, groups=groups, system=system)


@app.teardown_appcontext
def shutdown_session(exception=None):
	pass

