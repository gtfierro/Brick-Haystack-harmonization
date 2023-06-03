import sys
import pyshacl
import json
from rdflib import Namespace, Literal
import rdflib
import brickschema
from brick_haystack_harmonization.common import lib, get_equip_ref
from buildingmotif.namespaces import PARAM
from brickschema.namespaces import SKOS, BRICK, RDFS, A, XSD

M = Namespace("urn:model/")
PH = Namespace("urn:project_haystack/")

model = brickschema.Graph().load_file("haystack-ontology/haystack.ttl")
model.load_file("data/bh.ttl")
model.load_file("Brick.ttl")
model.bind("model", M)
model.bind("ph", PH)


def run(haystack_file: str, output_file: str):
    global model
    with open(haystack_file) as f:
        defs = json.load(f)
    rows = defs["rows"]
    for ent in rows:
        # define entity URI using 'id' field
        eid = ent["id"]["val"]
        model.add((M[eid], A, PH.Entity))

        # define and add marker tags
        marker_tags = [
            t
            for t, v in ent.items()
            if isinstance(v, dict) and v.get("_kind") == "marker"
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
        ]
        for key, value in ref_tags:
            vent = M[value["val"]]
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
    print("Start SHACL inference")
    _, _, report = pyshacl.validate(model, advanced=True, inplace=True, abort_on_first=False)
    _, _, report = pyshacl.validate(model, advanced=True, inplace=True, abort_on_first=False)

    print("Inferred Brick classes for:")
    res = model.query("SELECT DISTINCT ?ent ?type WHERE { ?ent rdf:type ?type . ?type rdfs:subClassOf* brick:Entity . ?ent rdf:type/rdfs:subClassOf* brick:Entity . ?ent a ph:Entity }")
    for row in res:
        print(row)

    print("template with instance")
    res = model.query("SELECT ?ent ?template WHERE { ?ent rdf:type ?type . ?type <urn:___param___#hasTemplate> ?template }")
    for row in res:
        ent, template_uri = row
        template_name = str(template_uri).removeprefix(PARAM)
        template = lib.get_template_by_name(template_name)
        # get any equipref
        equip = get_equip_ref(ent, model)
        bindings = {
            'name': ent
        }
        if equip is not None:
            bindings['part'] = equip

        templ_graph = template.evaluate(bindings)
        if not isinstance(templ_graph, rdflib.Graph):
            _, templ_graph = templ_graph.fill(M)
        model += templ_graph
        print(">>>", row)


    print("Validate SHACL")
    valid, _, report = pyshacl.validate(model, advanced=True, inplace=True, abort_on_first=False)

    model.serialize(output_file, format=rdflib.util.guess_format(output_file) or "ttl")

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
