from typing import List
import sys
import pyshacl
from brick_tq_shacl.topquadrant_shacl import infer, validate
import json
from rdflib import Namespace, Literal
import rdflib
import brickschema
from brick_haystack_harmonization.common import lib, get_equip_ref, get_parent, get_most_specific_template
from buildingmotif.namespaces import PARAM
from brickschema.namespaces import SKOS, BRICK, RDFS, A, RDF
from rdflib import XSD
from ontoenv import OntoEnv, Config

M = Namespace("urn:model/")
PH = Namespace("urn:project_haystack/")

ontology = brickschema.Graph().load_file("haystack-ontology/haystack.ttl")
ontology.load_file("data/bh.ttl")

brick = brickschema.Graph().load_file("https://brickschema.org/schema/1.4/Brick.ttl")

env = OntoEnv(Config(search_directories=["."]))
env.import_dependencies(ontology)

def is_marker_tag(tag):
    return isinstance(tag, dict) and tag.get("_kind") == "marker" or isinstance(tag, str)


def equipReftoBrick(subject: rdflib.URIRef, equipRef: rdflib.URIRef, context: brickschema.Graph) -> rdflib.URIRef:
    """
    subject: the subject entity which has an equipRef
    equipRef: the equipRef value

    Outputs the correct Brick relationship
    """
    # if subject is a transitive subClass of brick:Point, then output isPointOf
    query = "ASK { ?s rdf:type/rdfs:subClassOf* brick:Point }"
    if bool(context.query(query, initBindings={"s": subject})):  # type: ignore
        return BRICK.isPointOf
    # if subject is a transitive subClass of brick:Equipment, then output isPartOf
    query = "ASK { ?s rdf:type/rdfs:subClassOf* brick:Equipment }"
    if bool(context.query(query, initBindings={"s": subject})):  # type: ignore
        return BRICK.isPartOf
    raise ValueError(f"Unknown equipRef {equipRef} for entity {subject}")



def haystack_to_rdf(haystack_file: str) -> brickschema.Graph:
    model = brickschema.Graph()
    model.bind("model", M)
    model.bind("ph", PH)
    with open(haystack_file) as f:
        defs = json.load(f)
    rows = defs["rows"]
    for ent in rows:
        # define entity URI using 'id' field
        # handling for both string and dict types
        eid = ent["id"]["val"] if isinstance(ent["id"], dict) else ent["id"]
        model.add((M[eid], A, PH.Entity))
        label = ent.get("dis")
        if label:
            model.add((M[eid], RDFS.label, Literal(label)))

        # define and add marker tags
        marker_tags = [
            t
            for t, v in ent.items()
            if is_marker_tag(t)
        ]
        for mt in marker_tags:
            model.add((M[eid], PH.hasMarkerTag, Literal(mt)))

        # define and add value tags (key-value pairs)
        value_tags = [(t, v) for t, v in ent.items() if not isinstance(v, dict)]
        for key, value in value_tags:
            model.add(
                (
                    M[eid],
                    PH.hasValueTag,
                    [
                        (PH.key, Literal(key, datatype=XSD.string)),
                        (PH.value, Literal(value)),
                    ],
                )
            )

        # define and add ref tags
        ref_tags = [
            (t, v)
            for t, v in ent.items()
            if isinstance(v, dict) and v.get("_kind") == "ref"
            or t in ["siteRef", "equipRef", "pointRef", "weatherStationRef"]
        ]
        for key, value in ref_tags:
            vent = M[value["val"] if isinstance(value, dict) else value]
            model.add(
                (
                    M[eid],
                    PH.hasRefTag,
                    [
                        (PH.key, Literal(key, datatype=XSD.string)),
                        (PH.value, vent),
                    ],
                )
            )
    return model


def handle_entity_with_templates(model: brickschema.Graph, entity: rdflib.URIRef, entity_types: List[rdflib.URIRef]):
    # get the names of the templates out of the entity_types by stripping PARAM
    template_names = [t.split(PARAM)[-1] for t in entity_types]
    base_context = ontology + model + brick
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
        bindings, templ_graph = templ_graph.fill(M)
        bindings.update({"name": entity})

    model += templ_graph

    # get the equipRef of the entity; what is it pointing to?
    equip = get_equip_ref(entity, model)
    if equip is not None:
        # figure out the relationship between the equip and the parent
        relationship = equipReftoBrick(parent, equip, base_context + template.body)
        print(f"Adding relationship {relationship} between {entity} and {equip}")

        # connect the 'parent' of templ_graph to the entity's equipref
        parent_param_str = str(parent).removeprefix(str(PARAM))
        model.add((bindings[parent_param_str], relationship, equip))



def run(haystack_file: str, output_file: str):
    # convert haystack JSOn file into an RDF form
    model = haystack_to_rdf(haystack_file)
    for entity in model.subjects(A, PH.Entity):
        print(entity)
    # adds either the 'uri' or the 'template' as a type to each entity
    infer(model, ontology)
    model.serialize("/tmp/model1.ttl", format="ttl")
    # make a list of all entities whose type is a 'template'
    for entity in model.subjects(A, PH.Entity):
        entity_types = [t for t in model.objects(entity, RDF.type) if t.startswith(PARAM)]
        if not entity_types:
            continue
        handle_entity_with_templates(model, entity, entity_types)

    model.serialize(output_file, format=rdflib.util.guess_format(output_file) or "ttl")


def main():
    if len(sys.argv) < 3:
        print("Usage: ph-to-ttl <haystack JSON file> <output RDF file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
