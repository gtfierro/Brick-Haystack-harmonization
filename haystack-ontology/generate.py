import json


with open('defs.json') as f:
    defs = json.load(f)

for defn in defs["rows"]:
    if defn["def"]["_kind"] == "marker":
        print(defn)
