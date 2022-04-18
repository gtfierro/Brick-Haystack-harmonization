import sys
import rdflib
import yaml
from yaml import Loader


def check_brick_hierarchy(graph: rdflib.Graph, taxonomy: dict):
    messages = []
    for concept_name, concept_defn in taxonomy.items():
        brick_class = concept_defn.get("brick")
        if brick_class is None:
            messages.append(f"No Brick class defined for {concept_name}")
            continue
        brick_class_uri = rdflib.URIRef(brick_class)
        if (brick_class_uri, rdflib.RDF.type, rdflib.OWL.Class) not in graph:
            messages.append(
                f"Brick class {brick_class} for {concept_name} not found in graph"
            )
            continue
        children = concept_defn.get("children", [])
        for child_concept in children:
            if child_concept not in taxonomy:
                messages.append(f"Child concept {child_concept} not found in taxonomy")
                continue
            child_concept_uri = taxonomy[child_concept].get("brick")
            if child_concept_uri is None:
                messages.append(f"No Brick class defined for {child_concept}")
                continue
            child_concept_uri = rdflib.URIRef(child_concept_uri)
            if brick_class_uri not in graph.transitive_objects(
                child_concept_uri, rdflib.RDFS.subClassOf
            ):
                messages.append(
                    f"Child concept {child_concept} is not child of "
                    f"brick class {brick_class} for {concept_name}"
                )
                continue
    # messages may not be unique; sort so similar errors are grouped together
    for msg in sorted(set(messages)):
        print(msg)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: check_brick.py <brick_file> <taxonomy_file>")
        sys.exit(1)
    graph = rdflib.Graph()
    graph.parse(sys.argv[1], format="turtle")
    taxonomy = yaml.load(open(sys.argv[2]), Loader=Loader)
    check_brick_hierarchy(graph, taxonomy)
