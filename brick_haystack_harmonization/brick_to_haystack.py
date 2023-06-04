import sys
import re
import json
from pathlib import Path
import pyshacl
from rdflib import URIRef, Graph
from rdflib.query import ResultRow
from brickschema import Graph
from brickschema.namespaces import RDF
from brick_haystack_harmonization.common import PH

tag_cache = set()


def graph_to_haystack_json(graph: Graph):
    entities = graph.subjects(RDF.type, PH.Entity)
    document = {
        "_kind": "grid",
        "meta": {
            "ver": "3.0",
        },
        "cols": [{'name': 'id'}],
        "rows": []
    }
    for ent in entities:
        assert isinstance(ent, URIRef)
        doc = entity_to_document(ent, graph)
        document['rows'].append(doc)
    for tag in sorted(tag_cache):
        document['cols'].append({'name': tag})
    return document

def entity_to_document(entity: URIRef, graph: Graph) -> dict:
    doc = {
        'id': {'_kind': 'ref', 'val': str(re.split('#|/', entity)[-1])},
    }
    for markerTag in graph.objects(entity, PH.hasMarkerTag):
        tag = str(markerTag)
        tag_cache.add(tag)
        doc[tag] = {'_kind': 'marker'}

    value_tag_query = """SELECT ?key ?value WHERE {
        ?entity ph:hasValueTag ?tag .
        ?tag ph:key ?key .
        ?tag ph:value ?value
    }"""
    for row in graph.query(value_tag_query, initBindings={'entity': entity}):
        assert isinstance(row, ResultRow)
        key, value = row
        tag_cache.add(str(key))
        doc[str(key)] = str(value)  # type: ignore

    ref_tag_query = """SELECT ?key ?value WHERE {
        ?entity ph:hasRefTag ?tag .
        ?tag ph:key ?key .
        ?tag ph:value ?value
    }"""
    for row in graph.query(ref_tag_query, initBindings={'entity': entity}):
        assert isinstance(row, ResultRow)
        key, value = row
        tag_cache.add(str(key))
        doc[str(key)] = {'_kind': 'ref', 'val': str(value)}
    return doc


def run(brick_file: str, output: str):
    g = Graph()
    g.load_file(brick_file)
    g.load_file("data/bh.ttl")
    g.load_file("haystack-ontology/haystack.ttl")

    valid, _, report = pyshacl.validate(g, advanced=True, inplace=True)
    g.serialize(output, format='ttl')
    if not valid:
        print(report)
        sys.exit(1)

    # haystack tags now exist on all entities in the RDF graph.
    # next step is to convert this to JSON
    doc = graph_to_haystack_json(g)
    json_output = Path(output)
    with open(json_output.with_suffix('.json'), 'w') as f:
        json.dump(doc, f)
        

def main():
    if len(sys.argv) < 3:
        print("Usage: brick-to-ph <ttl file> <output>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
