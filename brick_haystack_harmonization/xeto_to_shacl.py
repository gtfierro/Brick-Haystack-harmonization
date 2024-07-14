import sys
from functools import cache
import brickschema
from brickschema.namespaces import BRICK, SH, A, RDF, OWL, RDFS
from brick_haystack_harmonization.common import validate_uri, get_template_shape, keep_marker_tag_property_shapes
from buildingmotif.dataclasses import Library
from rdflib import Namespace, URIRef, Literal
from rdflib.util import guess_format
import json
from typing import Tuple

class XetoToShacl:
    def __init__(self):
        self.g = brickschema.Graph()
        self.XETO = Namespace("urn:brick-haystack-xeto/")
        self.PH = Namespace("urn:project_haystack/")
        self.g.bind("ph", self.PH)
        self.g.bind("xeto", self.XETO)

        self.g.add((URIRef("urn:brick-haystack-xeto"), A, OWL.Ontology))
        self.g.add(
            (
                URIRef("urn:brick-haystack-xeto"),
                OWL.imports,
                URIRef("http://www.w3.org/ns/shacl"),
            )
        )
        self.g.add(
            (
                URIRef("urn:brick-haystack-xeto"),
                OWL.imports,
                URIRef("https://brickschema.org/schema/1.4/Brick"),
            )
        )

        self.tag_conditions = {}

    def get_tag_condition(self, tag):
        if tag in self.tag_conditions:
            return self.tag_conditions[tag]
        condition = self.PH[f"HasTag-{tag}"]
        self.g.add((condition, A, SH.NodeShape))
        self.g.add((condition, A, OWL.Class))
        self.g.add((condition, SH.property, [
            (A, SH.PropertyShape),
            (SH.path, self.PH.hasMarkerTag),
            (SH.qualifiedValueShape, [(SH.hasValue, Literal(tag))]),
            (SH.qualifiedMinCount, Literal(1)),
        ]))

        condition_rule = self.PH[f"HasTag-{tag}-Rule"]
        self.g.add((condition_rule, A, SH.NodeShape))
        self.g.add((condition_rule, SH.targetClass, self.PH.Entity))
        self.g.add((condition_rule, SH.rule, [
            (A, SH.TripleRule),
            (SH.condition, condition),
            (SH.object, condition),
            (SH.predicate, A),
            (SH.subject, SH.this),
        ]))

        self.tag_conditions[tag] = condition
        return condition

    @staticmethod
    def read_slots(resolved_repr: dict):
        for library_name, definition in resolved_repr.items():
            for slotname, slotdefn in definition.get("slots", {}).items():
                yield library_name, slotname, slotdefn

    def get_base_shape(self, library_name, name, defn) -> Tuple[URIRef, brickschema.Graph]:
        if validate_uri(defn.get("uri", "")):
            shape = URIRef(defn["uri"])
        else:
            shape = self.XETO[f"{library_name}::{name}"]
        shapeG = brickschema.Graph()
        shapeG.bind("ph", self.PH)
        shapeG.bind("xeto", self.XETO)
        shapeG.add((shape, A, SH.NodeShape))
        shapeG.add((shape, A, OWL.Class))
        shapeG.add((shape, RDFS.label, Literal(name)))
        shapeG.add(
            (shape, SH.rule, [
                (A, SH.TripleRule),
                (SH.object, self.PH.Entity),
                (SH.predicate, RDF.type),
                (SH.subject, SH.this)
            ])
        )
        shapeG.add((shape, SH.targetClass, self.PH.Entity))
        return shape, shapeG

    def add_slot_to_shape(self, shape, slotname, slotdefn, shapeG):
        slottype = slotdefn["type"]
        if slottype == "sys::Marker":
            # add the marker tag to the shape. This is a property shape that
            # requires the entity to have a marker tag with the given value
            shapeG.add((shape, SH.property, [
                (A, SH.PropertyShape),
                (SH.path, self.PH.hasMarkerTag),
                (SH.qualifiedValueShape, [(SH.hasValue, Literal(slotname))]),
                (SH.qualifiedMinCount, Literal(1)),
            ]))

    def slot_to_shacl(self, library_name, name, defn):
        # if there are no slots in the definition, skip
        if "slots" not in defn:
            return

        # get the name of the shape, and create the base shape definition
        shape, shapeG = self.get_base_shape(library_name, name, defn)

        if "points" in defn["slots"]:
            points = defn["slots"].pop("points")
            print(json.dumps(points, indent=2))
            return
            # raise NotImplementedError("points are not yet supported")
            # TODO...

        for slotname, slotdefn in defn["slots"].items():
            self.add_slot_to_shape(shape, slotname, slotdefn, shapeG)

        if "template" in defn:
            shapeG.add((shape, self.PH['hasTemplate'], Literal(defn['template'])))
        brick_class = defn.get("uri")
        if not brick_class:
            # raise ValueError(f"no brick class defined for {library_name}::{name}")
            return

        # add a rule which states if an instance of ph:Entity fulfills the shape
        # requirements, then it is an instance of the shape
        condition = self.PH[f"HasShape-{name}-Rule"]
        shapeG.add((condition, A, SH.NodeShape))
        shapeG.add((condition, SH.targetClass, self.PH.Entity))
        shapeG.add((condition, SH.rule, [
            (A, SH.TripleRule),
            (SH.condition, shape),
            (SH.object, URIRef(brick_class)),
            (SH.predicate, A),
            (SH.subject, SH.this),
        ]))

        print(shapeG.cbd(shape).serialize())
        return shape, shapeG

    def run(self, input_file, output_file) -> brickschema.Graph:
        resolved_xetos = json.load(open(input_file))
        for slot in self.read_slots(resolved_xetos):
            res = self.slot_to_shacl(*slot)
            if res is None:
                continue
            shape, shape_graph = res
            self.g += shape_graph
        self.g.serialize(output_file, format=guess_format(output_file))
        Library.load(ontology_graph=str(output_file))
        return self.g

def main():
    if len(sys.argv) < 3:
        print("Usage: xeto-to-shacl <resolved json file> <output graph file>")
        sys.exit(1)
    processor = XetoToShacl()
    processor.run(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
