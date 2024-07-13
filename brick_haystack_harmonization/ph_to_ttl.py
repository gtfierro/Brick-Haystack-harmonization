import sys
import pyshacl
from brick_tq_shacl.topquadrant_shacl import infer, validate
import json
from rdflib import Namespace, Literal
import rdflib
import brickschema
from brick_haystack_harmonization.common import lib, get_equip_ref
from buildingmotif.namespaces import PARAM
from brickschema.namespaces import SKOS, BRICK, RDFS, A, RDF
from rdflib import XSD
from ontoenv import OntoEnv, Config

M = Namespace("urn:model/")
PH = Namespace("urn:project_haystack/")

ontology = brickschema.Graph().load_file("haystack-ontology/haystack.ttl")
ontology.load_file("data/bh.ttl")

model = brickschema.Graph()

model.bind("model", M)
model.bind("ph", PH)

env = OntoEnv(Config(search_directories=["."]))
env.import_dependencies(ontology)

def is_marker_tag(tag):
    return isinstance(tag, dict) and tag.get("_kind") == "marker" or isinstance(tag, str)


def run(haystack_file: str, output_file: str):
    global model
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
    model.serialize("/tmp/model1.ttl", format="ttl")
    print("Start SHACL inference")
    #_, _, report = pyshacl.validate(model, ont_graph=brick, shape_graph=brick, advanced=True, inplace=True, abort_on_first=False)
    #_, _, report = pyshacl.validate(model, ont_graph=brick, shape_graph=brick, advanced=True, inplace=True, abort_on_first=False)
    model = infer(model, ontology)
    model = infer(model, ontology)
    print("model len", len(model))
    model.serialize("/tmp/model2.ttl", format="ttl")
    report = validate(model, ontology)

    model.serialize("/tmp/model3.ttl", format="ttl")

    combined = (model + ontology)

    print("Inferred Brick classes for:")
    res = combined.query("""SELECT DISTINCT ?ent ?type WHERE {
        ?ent rdf:type ?type .
        ?type rdfs:subClassOf* brick:Entity .
        ?ent rdf:type/rdfs:subClassOf* brick:Entity .
        ?ent a ph:Entity  .
        FILTER NOT EXISTS { ?ent a brick:Quantity } .
        FILTER NOT EXISTS { ?ent a brick:Substance } .
    }""")
    for row in res:
        print(row)

    print("template with instance")
    res = combined.query("SELECT ?ent ?template ?type WHERE { ?ent rdf:type ?type . ?type <urn:___param___#hasTemplate> ?template }")
    for row in res:
        ent, template_uri, ent_type = row
        template_name = str(template_uri).removeprefix(PARAM)
        template = lib.get_template_by_name(template_name)
        # get any equipref
        equip = get_equip_ref(ent, model)
        bindings = {
            'name': ent
        }
        if equip is not None:
            bindings['part'] = equip
        print(f"Entity: {ent}, Template: {template_name} bindings: {bindings}")

        templ_graph = template.evaluate(bindings)
        if not isinstance(templ_graph, rdflib.Graph):
            _, templ_graph = templ_graph.fill(M)
        print(templ_graph.serialize(format="ttl"))
        model += templ_graph

    model.serialize("/tmp/model4.ttl", format="ttl")
    ontology.serialize("/tmp/ontology.ttl", format="ttl")

    print("Validate SHACL")
    #valid, _, report = pyshacl.validate(model, advanced=True, inplace=True, abort_on_first=False)
    valid, _, report = validate(model, ontology)

    simple_g = model
    # save simplified model
    #simple_g = rdflib.Graph()
    #entities = model.query("SELECT DISTINCT ?ent WHERE { ?ent rdf:type/rdfs:subClassOf* brick:Entity }")
    #for (ent,) in entities:
    #    simple_g += model.cbd(ent)
    # removes any PH triples
    # for (s, p, o) in simple_g:
    #     if PH in s or PH in p or PH in o:
    #         simple_g.remove((s, p, o))
    #simple_g -= brick

    print('writing to',output_file)
    simple_g.serialize(output_file, format=rdflib.util.guess_format(output_file) or "ttl")

    if not valid:
        print(report)
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("Usage: ph-to-ttl <haystack JSON file> <output RDF file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
