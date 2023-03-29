import pickle
from brickschema.namespaces import BRICK
from common import taglist_to_set, read_csv, fixup_tags

def update_base_mapping(mapping: dict, row: dict):
    point_class = row["Brick:PointClass"].replace(' ', '_')
    tags = taglist_to_set(row["Haystack:Markers"])
    tags.add(row["Brick:L1PointClass"])
    tags.add("point")
    fixup_tags(tags)
    mapping[tuple(sorted(tags))] = BRICK[point_class]

def run():
    mapping = {}
    for row in read_csv():
        if row["Meta:State"] == "Base":
            update_base_mapping(mapping, row)
    with open("bh-mapping.pkl", "wb") as f:
        pickle.dump(mapping, f)


if __name__ == "__main__":
    run()
