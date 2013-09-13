import json
from flask import Flask, flash, session, render_template, redirect, request, abort, url_for, escape
import redis_wrap
import string, random
import hashlib
from string import zfill
from dscan import DScan

app = Flask(__name__)

# Load configuration
with open("config.json") as fh:
	config=json.loads(fh.read())
assert(config)
app.config.update(config)

dscan = DScan()
store = redis_wrap.get_hash('dscan')

@app.route('/', methods=["GET", "POST"])
def dscanmake():
	if request.method=="GET":
		return render_template("dscan.html")
	if request.method=="POST":
		data = dscan.parseDscan(request.form["dscandata"])
		token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(24))
		while token in store:
			token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(24))
		store[token] = data
		return redirect("/view/"+token)


def color_variant(hex_color, brightness_offset=1):
	""" takes a color like #87c95f and produces a lighter or darker variant """
	if len(hex_color) != 7:
		raise Exception("Passed %s into color_variant(), needs to be in #87c95f format." % hex_color)
	rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
	new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
	new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int] # make sure new values are between 0 and 255
	# hex() produces "0x88", we want just "88"
	return "#" + "".join([hex(i)[2:] for i in new_rgb_int])

def hashstringtocolor(s):
	base = (0, 0, 50)
	md5 = hashlib.md5()
	md5.update(s)
	digest = md5.hexdigest()
	r = int(digest[0:10], 16) % 256
	g = int(digest[10:20], 16) % 256
	b = int(digest[20:30], 16) % 256
	# mix with base
	r = (r + base[0]) / 2
	g = (g + base[1]) / 2
	b = (b + base[2]) / 2
	return '#{:02x}{:02x}{:02x}'.format(r,g,b)

@app.route('/view/<id>')
def dscanview(id):
	data = json.loads(store[id])
	data["categorylist"] = data["categories"].keys()
	if "Ship" in data["categorylist"]:
		data["categorylist"].remove("Ship")
		data["categorylist"] = ["Ship"] + sorted(data["categorylist"])
	else:
		data["categorylist"] = sorted(data["categorylist"])
	data["sizeorder"] = data["sizemap"].keys()
	data["sizeorder"] = sorted(data["sizeorder"], key=lambda x: -sum(data["sizemap"][x].values()))
	data["color_variant"] = color_variant
	data["string2color"] = hashstringtocolor
	return render_template("dscan_results_new.html", **data)


@app.teardown_appcontext
def shutdown_session(exception=None):
	pass

