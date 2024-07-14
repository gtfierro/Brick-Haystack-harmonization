from typing import List, Tuple
import importlib_resources
import sys
import pyshacl
from brick_tq_shacl.topquadrant_shacl import infer, validate
import json
from rdflib import Namespace, Literal, OWL, URIRef
import rdflib
import brickschema
from brick_haystack_harmonization.common import lib, get_equip_ref, get_parent, get_most_specific_template, brick, env
from buildingmotif.namespaces import PARAM
from brickschema.namespaces import SKOS, BRICK, RDFS, A, RDF
from rdflib import XSD

class HaystackToRDFTransformer:
    def __init__(self):
        self.M = Namespace("urn:model/")
        self.PH = Namespace("urn:project_haystack/")

        haystack_ontology_path = importlib_resources.files('brick_haystack_harmonization.data').joinpath('haystack.ttl')
        self.ontology = brickschema.Graph().load_file(str(haystack_ontology_path))

        bh_path = importlib_resources.files('brick_haystack_harmonization.data').joinpath('bh.ttl')
        self.ontology.load_file(str(bh_path))
        bh_base_path = importlib_resources.files('brick_haystack_harmonization.data').joinpath('bhbase.ttl')
        self.ontology.load_file(str(bh_base_path))

        self.brick = brick


    def is_marker_tag(self, tag):
        return isinstance(tag, dict) and tag.get("_kind") == "marker" or isinstance(tag, str)

    def equipReftoBrick(self, subject: rdflib.URIRef, equipRef: rdflib.URIRef, context: brickschema.Graph) -> rdflib.URIRef:
        query = "ASK { ?s rdf:type/brick:aliasOf?/rdfs:subClassOf* brick:Point }"
        if bool(context.query(query, initBindings={"s": subject})):  # type: ignore
            return BRICK.isPointOf
        query = "ASK { ?s rdf:type/brick:aliasOf?/rdfs:subClassOf* brick:Equipment }"
        if bool(context.query(query, initBindings={"s": subject})):  # type: ignore
            return BRICK.isPartOf
        raise ValueError(f"Unknown equipRef {equipRef} for entity {subject}")

    def haystack_to_rdf(self, haystack_file: str) -> brickschema.Graph:
        model = brickschema.Graph()
        #model.add((
        # declare ontology and improt brick 1.4
        model.add((URIRef(self.M), A, OWL.Ontology))
        model.bind("model", self.M)
        model.bind("ph", self.PH)
        with open(haystack_file) as f:
            defs = json.load(f)
        rows = defs["rows"]
        for ent in rows:
            eid = ent["id"]["val"] if isinstance(ent["id"], dict) else ent["id"]
            model.add((self.M[eid], A, self.PH.Entity))
            label = ent.get("dis")
            if label:
                model.add((self.M[eid], RDFS.label, Literal(label)))

            marker_tags = [t for t, v in ent.items() if self.is_marker_tag(t)]
            for mt in marker_tags:
                model.add((self.M[eid], self.PH.hasMarkerTag, Literal(mt)))

            value_tags = [(t, v) for t, v in ent.items() if not isinstance(v, dict)]
            for key, value in value_tags:
                model.add(
                    (
                        self.M[eid],
                        self.PH.hasValueTag,
                        [
                            (self.PH.key, Literal(key, datatype=XSD.string)),
                            (self.PH.value, Literal(value)),
                        ],
                    )
                )

            ref_tags = [(t, v) for t, v in ent.items() if isinstance(v, dict) and v.get("_kind") == "ref" or t in ["siteRef", "equipRef", "pointRef", "weatherStationRef"]]
            for key, value in ref_tags:
                vent = self.M[value["val"] if isinstance(value, dict) else value]
                model.add(
                    (
                        self.M[eid],
                        self.PH.hasRefTag,
                        [
                            (self.PH.key, Literal(key, datatype=XSD.string)),
                            (self.PH.value, vent),
                        ],
                    )
                )
        return model

    def handle_entity_with_templates(self, model: brickschema.Graph, entity: rdflib.URIRef, entity_types: List[rdflib.URIRef]):
        template_names = [t.split(PARAM)[-1] for t in entity_types]
        base_context = self.ontology + model + self.brick
        print(f"Entity {entity} has types {template_names} from {entity_types}")
        template = get_most_specific_template([lib.get_template_by_name(t) for t in template_names], base_context)
        if not template:
            print(f"No template found for {entity} inside {entity_types}")
            return

        parent, parent_type = get_parent(template)
        print(f"{entity} is a {template} with parent {parent} and parent type {parent_type}")

        bindings = {"name": entity}
        templ_graph = template.evaluate(bindings)
        if not isinstance(templ_graph, rdflib.Graph):
            bindings, templ_graph = templ_graph.fill(self.M)
            bindings.update({"name": entity})

        model += templ_graph

        equip = get_equip_ref(entity, model)
        if equip is not None:
            print(f"Entity {entity} has equipRef {equip} and parent {parent} for template {template.name}")
            relationship = self.equipReftoBrick(parent, equip, base_context + template.body)
            print(f"Adding relationship {relationship} between {entity} and {equip}")

            parent_param_str = str(parent).removeprefix(str(PARAM))
            model.add((bindings[parent_param_str], relationship, equip))

    def run(self, haystack_file: str) -> Tuple[brickschema.Graph, bool, rdflib.Graph]:
        model = self.haystack_to_rdf(haystack_file)
        infer(model, self.ontology + self.brick)
        for entity in model.subjects(A, self.PH.Entity):
            entity_types = [t for t in model.objects(entity, RDF.type) if t.startswith(PARAM)]
            if not entity_types:
                continue
            self.handle_entity_with_templates(model, entity, entity_types)

        env.import_dependencies(self.brick)
        combined = self.brick.skolemize()

        combined.serialize("/tmp/combined.ttl", format="ttl")
        model.serialize("/tmp/model.ttl", format="ttl")
        valid, _, report = validate(model, combined)
        return model, valid, report

def main():
    if len(sys.argv) < 3:
        print("Usage: ph-to-ttl <haystack JSON file> <output RDF file>")
        sys.exit(1)
    transformer = HaystackToRDFTransformer()
    model, valid, report = transformer.run(sys.argv[1])
    model.serialize(sys.argv[2], format=rdflib.util.guess_format(sys.argv[2]) or "ttl")
    if not valid:
        print(report)
        sys.exit(1)

if __name__ == "__main__":
    main()
