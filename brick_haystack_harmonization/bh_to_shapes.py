import sys
import pickle
from brickschema.namespaces import BRICK
from .common import taglist_to_set, read_csv, fixup_tags


def update_base_mapping(mapping: dict, row: dict):
    point_class = row["Brick:PointClass"].replace(" ", "_")
    tags = taglist_to_set(row["Haystack:Markers"])
    tags.add(row["Brick:L1PointClass"])
    tags.add("point")
    fixup_tags(tags)
    mapping[tuple(sorted(tags))] = BRICK[point_class]


def run(filename: str, outputfile: str):
    mapping = {}
    for row in read_csv(filename):
        if row["Meta:State"] == "Base":
            update_base_mapping(mapping, row)
    with open(outputfile, "wb") as f:
        pickle.dump(mapping, f)


def main():
    if len(sys.argv) < 3:
        print("Usage: bh-to-shapes <csv file> <output pickle file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
