import sys
import pyshacl
from brickschema import Graph

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

def main():
    if len(sys.argv) < 3:
        print("Usage: brick-to-ph <ttl file> <output>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
