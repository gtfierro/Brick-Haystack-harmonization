import brickschema
from brickschema.namespaces import SKOS, BRICK
import os
import pathlib
import sys
from .common import taglist_to_set, read_csv, fixup_tags, clean_brick_classname

g = brickschema.Graph().load_file("Brick.ttl")
seen_classes = set()

def base_to_xeto(row: dict) -> str:
    point_class = clean_brick_classname(row["Brick:PointClass"])
    if point_class in seen_classes:
        return ''
    seen_classes.add(point_class)
    tags = taglist_to_set(row["Haystack:Markers"])
    tags.add(row["Brick:L1PointClass"])
    fixup_tags(tags)
    print(point_class, tags)
    if len(tags) > 1:
        tag_list = ', '.join(tags)
    else:
        tag_list = tags.pop()
    try:
        defn = next(g.objects(subject=BRICK[point_class], predicate=SKOS.definition))
        return f"// {defn}\nBrick_{point_class} : Point {{ {tag_list} }}\n"
    except StopIteration:
        return f"\nBrick_{point_class} : Point {{ {tag_list} }}\n"


# TODO
def subparts_to_xeto(row: dict):
    point_class = clean_brick_classname(row["Brick:PointClass"])
    l0class = row["Subpart:EntityClassL0"]
    l1class = row["Subpart:EntityClassL1"]
    return (point_class, l0class, l1class)


def run(filename: str, outputfile: str):
    statements = []
    for row in read_csv(filename):
        if row["Meta:State"] == "Base":
            statements.append(base_to_xeto(row) + '\n')
        elif row["Meta:State"] == "Subparts":
            subparts_to_xeto(row) # TODO: finish
    # library name
    libfile = pathlib.Path(outputfile).with_name("lib.xeto")
    # create output directory
    os.makedirs(libfile.parent, exist_ok=True)
    # write xeto file
    with open(outputfile, 'w') as f:
        f.writelines(statements)

    # write library file
    with open(libfile, "w") as f:
        f.write("""
pragma: Lib <
  doc: "Generated xeto file"
  version: "3.9.12"
  depends: {
    { lib: "sys" }
    { lib: "ph" }
  }
  org: {
   dis: "Brick xeto file"
   uri: "https://github.com/gtfierro/Brick-Haystack-harmonization"
  }
>""")


def main():
    if len(sys.argv) < 3:
        print("Usage: bh-to-xeto <csv file> <output xeto file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
