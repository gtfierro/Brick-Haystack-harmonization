import sys
import brickschema
from brickschema.namespaces import BRICK, SH, A, RDF, RDFS, OWL
from brick_haystack_harmonization.common import validate_uri
from rdflib import Namespace, URIRef, BNode, Literal
from rdflib.util import guess_format
import json

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
        URIRef("https://brickschema.org/schema/Brick"),
    )
)

tag_conditions = {}


def get_tag_condition(tag):
    if tag in tag_conditions:
        return tag_conditions[tag]
    condition = PH[f"HasTag-{tag}"]
    g.add((condition, A, SH.NodeShape))
    g.add((condition, A, OWL.Class))
    g.add((condition, SH.property, [
        (A, SH.PropertyShape),
        (SH.path, PH.hasMarkerTag),
        (SH.hasValue, Literal(tag)),
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


def slot_to_shacl(library_name, name, defn):
    # use the URI if it exists and is valid; else construct one
    # TODO: make sure we emit the shape for the buildingmotif template
    if defn.get('template',''):
        print('template name', defn['template'])
        return
    elif validate_uri(defn.get("uri", "")):
        shape = URIRef(defn["uri"])
    else:
        shape = XETO[f"{library_name}::{name}"]

    g.add((shape, A, SH.NodeShape))
    g.add((shape, A, OWL.Class))
    g.add(
        (shape, SH.rule, [
            (A, SH.TripleRule),
            (SH.object, PH.Entity),
            (SH.predicate, RDF.type),
            (SH.subject, SH.this)
        ])
    )
    if "slots" not in defn:
        return
    if "points" in defn["slots"]:
        points = defn["slots"].pop("points")
        # asserts to make sure we are using the expected 'point' construct
        assert points["type"] == "sys::Query", points
        assert points["inverse"] == "ph::Point.equips", points
        assert points["of"] == "ph::Point", points
        for slot in points.get("slots", {}).values():
            if "type" in slot:
                target_shape = XETO[slot["type"]]
                # add a "dependency" on the shape indicated in this slot
                g.add(
                    (
                        shape,
                        SH.property,
                        [
                            (A, SH.PropertyShape),
                            (SH.path, BRICK.hasPoint),
                            (SH.node, target_shape),
                        ],
                    )
                )

    # loop through the rest of the type definition
    for key, keydefn in defn["slots"].items():
        # if it's a marker, add the SHACL requirement
        if keydefn["type"] == "sys::Marker":
            g.add(
                (
                    shape,
                    SH.property,
                    [
                        (A, SH.PropertyShape),
                        (SH.path, PH.hasMarkerTag),
                        (
                            SH.qualifiedValueShape,
                            [
                                (SH.hasValue, Literal(key)),
                            ],
                        ),
                        (SH.qualifiedMinCount, Literal(1)),
                    ],
                )
            )

            condition = get_tag_condition(key)
            # add ruleto infer Brick class
            g.add((XETO[f"infer_brick_rule_{name}"], A, SH.NodeShape))
            g.add((XETO[f"infer_brick_rule_{name}"], SH.targetClass, condition))
            g.add(
                (XETO[f"infer_brick_rule_{name}"], SH.rule, [
                    (A, SH.TripleRule),
                    (SH.condition, shape),
                    (SH.object, shape),
                    (SH.predicate, RDF.type),
                    (SH.subject, SH.this)
                ])
            )

            # add rule to infer tags
            g.add(
                (shape, SH.rule, [
                    (A, SH.TripleRule),
                    (SH.object, Literal(key)),
                    (SH.predicate, PH.hasMarkerTag),
                    (SH.subject, SH.this)
                ])
            )





def main():
    if len(sys.argv) < 3:
        print("Usage: xeto-to-shacl <resolved json file> <output graph file>")
        sys.exit(1)
    resolved_xetos = json.load(open(sys.argv[1]))
    for slot in read_slots(resolved_xetos):
        slot_to_shacl(*slot)
    g.serialize(sys.argv[2], format=guess_format(sys.argv[2]))


if __name__ == "__main__":
    main()
