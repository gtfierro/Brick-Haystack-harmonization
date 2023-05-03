import sys
import json
from rdflib import Namespace, Literal
import rdflib
import brickschema
from brickschema.namespaces import SKOS, BRICK, RDFS, A

M = Namespace("urn:model/")
PH = Namespace("urn:project_haystack/")

g = brickschema.Graph().load_file("haystack-ontology/haystack.ttl")
model = brickschema.Graph()
model.bind("model", M)
model.bind("ph", PH)


def run(haystack_file: str, output_file: str):
    with open(haystack_file) as f:
        defs = json.load(f)
    rows = defs["rows"]
    for ent in rows:
        eid = ent["id"]["val"]
        model.add((M[eid], A, PH.Entity))
        marker_tags = [
            t
            for t, v in ent.items()
            if isinstance(v, dict) and v.get("_kind") == "marker"
        ]
        for mt in marker_tags:
            model.add((M[eid], PH.hasMarkerTag, Literal(mt)))
        value_tags = [(t, v) for t, v in ent.items() if not isinstance(v, dict)]
        for key, value in value_tags:
            model.add(
                (
                    M[eid],
                    PH.hasValueTag,
                    [
                        (PH.key, Literal(key)),
                        (PH.value, Literal(value)),
                    ],
                )
            )
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
                        (PH.key, Literal(key)),
                        (PH.value, vent),
                    ],
                )
            )

    model.serialize(output_file, format=rdflib.util.guess_format(output_file) or "ttl")


def main():
    if len(sys.argv) < 3:
        print("Usage: ph-to-ttl <haystack JSON file> <output RDF file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
