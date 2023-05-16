import json
from rdflib import BNode, Namespace, Literal
from brickschema import Graph
from brickschema.namespaces import A, SH

g = Graph()
XETO = Namespace("urn:brick-haystack-xeto/")
PH = Namespace("urn:project_haystack/")
g.bind("ph", PH)
g.bind("xeto", XETO)

tag_conditions = {}

def is_ref_tag(defn):
    is_tags = defn.get('is', [])
    return any(t.get('val') == 'ref' for t in is_tags)

def get_tag_condition(tag):
    if tag in tag_conditions:
        return tag_conditions[tag]
    condition = PH[f"HasTag-{tag}"]
    g.add((condition, A, SH.NodeShape))
    g.add((condition, SH.property, [
        (A, SH.PropertyShape),
        (SH.path, PH.hasMarkerTag),
        (SH.hasValue, Literal(tag)),
    ]))
    tag_conditions[tag] = condition
    return condition

with open('defs.json') as f:
    defs = json.load(f)

for defn in defs["rows"]:
    if defn["def"]["_kind"] == "symbol" and is_ref_tag(defn):
        print('-'*10)
        ref_tag = defn["def"]["val"]
        tag_on = defn.get('tagOn', [])
        print(defn["def"]["val"])
        print(defn.get('tagOn'))
        print(defn.get('of'))

        for owning_tag in tag_on:
            tag_val = owning_tag['val']
            condition = get_tag_condition(tag_val)

print(g.serialize())
