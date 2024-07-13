import sys
from functools import cache
import brickschema
from brickschema.namespaces import BRICK, SH, A, RDF, OWL, RDFS
from brick_haystack_harmonization.common import validate_uri, get_template_shape, keep_marker_tag_property_shapes
from rdflib import Namespace, URIRef, Literal
from rdflib.util import guess_format
import json
from typing import Tuple


g = brickschema.Graph()
XETO = Namespace("urn:brick-haystack-xeto/")
PH = Namespace("urn:project_haystack/")
g.bind("ph", PH)
g.bind("xeto", XETO)

g.add((URIRef("urn:brick-haystack-xeto"), A, OWL.Ontology))
g.add(
    (
        URIRef("urn:brick-haystack-xeto"),
        OWL.imports,
        URIRef("http://www.w3.org/ns/shacl"),
    )
)
g.add(
    (
        URIRef("urn:brick-haystack-xeto"),
        OWL.imports,
        URIRef("https://brickschema.org/schema/1.4/Brick"),
    )
)


tag_conditions = {}
# HasTag-<tag> is a NodeShape that requires the entity to have a marker tag with the given value
# HasTag-<tag>-Rule is a rule that applies the HasTag-<tag> condition to all entities; if
# the entity has the tag, the rule is satisfied
def get_tag_condition(tag):
    if tag in tag_conditions:
        return tag_conditions[tag]
    condition = PH[f"HasTag-{tag}"]
    g.add((condition, A, SH.NodeShape))
    g.add((condition, A, OWL.Class))
    g.add((condition, SH.property, [
        (A, SH.PropertyShape),
        (SH.path, PH.hasMarkerTag),
        (SH.qualifiedValueShape, [ (SH.hasValue, Literal(tag)) ]),
        (SH.qualifiedMinCount, Literal(1)),
    ]))

    condition_rule = PH[f"HasTag-{tag}-Rule"]
    g.add((condition_rule, A, SH.NodeShape))
    g.add((condition_rule, SH.targetClass, PH.Entity))
    g.add((condition_rule, SH.rule, [
        (A, SH.TripleRule),
        (SH.condition, condition),
        (SH.object, condition),
        (SH.predicate, A),
        (SH.subject, SH.this),
    ]))

    tag_conditions[tag] = condition
    return condition


def read_slots(resolved_repr: dict):
    for library_name, definition in resolved_repr.items():
        for slotname, slotdefn in definition.get("slots", {}).items():
            yield library_name, slotname, slotdefn


def get_base_shape(library_name, name, defn) -> Tuple[URIRef, brickschema.Graph]:
    if validate_uri(defn.get("uri", "")):
        shape = URIRef(defn["uri"])
    else:
        shape = XETO[f"{library_name}::{name}"]
    shapeG = brickschema.Graph()
    shapeG.bind("ph", PH)
    shapeG.bind("xeto", XETO)
    shapeG.add((shape, A, SH.NodeShape))
    shapeG.add((shape, A, OWL.Class))
    shapeG.add((shape, RDFS.label, Literal(name)))
    shapeG.add(
        (shape, SH.rule, [
            (A, SH.TripleRule),
            (SH.object, PH.Entity),
            (SH.predicate, RDF.type),
            (SH.subject, SH.this)
        ])
    )
    shapeG.add((shape, SH.targetClass, PH.Entity))
    return shape, shapeG


def add_slot_to_shape(shape, slotname, slotdefn, shapeG):
    slottype = slotdefn["type"]
    if slottype == "sys::Marker":
        # add the marker tag to the shape. This is a property shape that
        # requires the entity to have a marker tag with the given value
        shapeG.add((shape, SH.property, [
            (A, SH.PropertyShape),
            (SH.path, PH.hasMarkerTag),
            (SH.qualifiedValueShape, [ (SH.hasValue, Literal(slotname)) ]),
            (SH.qualifiedMinCount, Literal(1)),
        ]))



def slot_to_shacl(library_name, name, defn):
    # if there are no slots in the definition, skip
    if "slots" not in defn:
        return

    # get the name of the shape, and create the base shape definition
    shape, shapeG = get_base_shape(library_name, name, defn)

    if "points" in defn["slots"]:
        points = defn["slots"].pop("points")
        print(json.dumps(points, indent=2))
        return
        #raise NotImplementedError("points are not yet supported")
        # TODO...

    for slotname, slotdefn in defn["slots"].items():
        add_slot_to_shape(shape, slotname, slotdefn, shapeG)

    if "template" in defn:
        shapeG.add((shape, PH['hasTemplate'], Literal(defn['template'])))
    brick_class = defn.get("uri")
    if not brick_class:
        #raise ValueError(f"no brick class defined for {library_name}::{name}")
        return

    # add a rule which states if an instance of ph:Entity fulfills the shape
    # requirements, then it is an instance of the shape
    condition = PH[f"HasShape-{name}-Rule"]
    shapeG.add((condition, A, SH.NodeShape))
    shapeG.add((condition, SH.targetClass, PH.Entity))
    shapeG.add((condition, SH.rule, [
        (A, SH.TripleRule),
        (SH.condition, shape),
        (SH.object, URIRef(brick_class)),
        (SH.predicate, A),
        (SH.subject, SH.this),
    ]))

    print(shapeG.cbd(shape).serialize())
    return shape, shapeG


def main():
    global g
    if len(sys.argv) < 3:
        print("Usage: xeto-to-shacl <resolved json file> <output graph file>")
        sys.exit(1)
    resolved_xetos = json.load(open(sys.argv[1]))
    for slot in read_slots(resolved_xetos):
        res = slot_to_shacl(*slot)
        if res is None:
            continue
        shape, shape_graph = res
        g += shape_graph
    g.serialize(sys.argv[2], format=guess_format(sys.argv[2]))


if __name__ == "__main__":
    main()
