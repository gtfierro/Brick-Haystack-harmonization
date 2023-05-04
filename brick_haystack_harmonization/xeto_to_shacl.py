import sys
import brickschema
from brickschema.namespaces import BRICK, SH, A, RDF, RDFS, OWL
from brick_haystack_harmonization.common import validate_uri
from rdflib import Namespace, URIRef, BNode, Literal
from rdflib.util import guess_format
import json

g = brickschema.Graph()
XETO = Namespace("urn:brick-haystack-xeto/")
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


def read_slots(resolved_repr: dict):
    for library_name, definition in resolved_repr.items():
        for slotname, slotdefn in definition.get("slots", {}).items():
            yield library_name, slotname, slotdefn


def slot_to_shacl(library_name, name, defn):
    # use the URI if it exists and is valid; else construct one
    if validate_uri(defn.get("uri", "")):
        shape = URIRef(defn["uri"])
    else:
        shape = XETO[f"{library_name}::{name}"]

    g.add((shape, A, SH.NodeShape))
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
                        (SH.path, BRICK.hasTag),
                        (SH.value, Literal(key)),
                    ],
                )
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
