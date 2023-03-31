import brickschema
from brickschema.namespaces import SKOS, BRICK, RDFS
import os
from typing import List
import pathlib
import sys
from .common import taglist_to_set, read_csv, fixup_tags, clean_brick_classname, guess_tags

g = brickschema.Graph().load_file("Brick.ttl")
seen_classes = set()
parent_classes = set()

def base_to_xeto(row: dict) -> str:
    point_class = clean_brick_classname(row["Brick:PointClass"])
    if BRICK[point_class] in seen_classes:
        return ''
    seen_classes.add(BRICK[point_class])
    tags = taglist_to_set(row["Haystack:Markers"])
    tags.add(row["Brick:L1PointClass"])
    fixup_tags(tags)
    if len(tags) > 1:
        tag_list = ', '.join(sorted(tags))
    else:
        tag_list = tags.pop()
    return make_statement(point_class, tag_list)


def make_statement(point_class: str, tag_list: str) -> str:
    parent = g.value(subject=BRICK[point_class], predicate=RDFS.subClassOf)
    if parent is None or parent == BRICK['Point']:
        parent = "Point"
    else:
        parent_classes.add(parent)
        parent = f"Brick_{parent.split('#')[-1].replace('.','')}"

    defn = g.value(subject=BRICK[point_class], predicate=SKOS.definition)
    if defn is not None:
        return f'// {defn}\nBrick_{point_class.replace(".", "")} : {parent} <uri:"{point_class}"> {{ {tag_list} }}\n'
    else:
        return f'\nBrick_{point_class.replace(".", "")} : {parent} <uri:"{point_class}"> {{ {tag_list} }}\n'


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

    # compute any classes which show up as parents but aren't already
    # in the file
    while len(parent_classes):
        leftover = parent_classes - seen_classes
        if not leftover:
            break
        for concept in leftover:
            if concept in seen_classes:
                continue
            seen_classes.add(concept)

            tags = guess_tags(g, concept)
            fixup_tags(tags)
            statements.append(make_statement(
                concept.split('#')[-1],
                ', '.join(tags)
            ))
            parent_classes.remove(concept)

    # library name
    libfile = pathlib.Path(outputfile).with_name("lib.xeto")
    # create output directory
    os.makedirs(libfile.parent, exist_ok=True)
    # write xeto file
    with open(outputfile, 'w') as f:
        f.writelines(statements)

    # write library file
    mappings = dict(g.namespace_manager.namespaces())
    brick_base_uri = mappings["brick"]
    with open(libfile, "w") as f:
        f.write(f"""
pragma: Lib <
  doc: "Generated xeto file"
  version: "3.9.12"
  baseUri: "{brick_base_uri}"
  depends: {{
    {{ lib: "sys" }}
    {{ lib: "ph" }}
  }}
  org: {{
   dis: "Brick xeto file"
   uri: "https://github.com/gtfierro/Brick-Haystack-harmonization"
  }}
>""")


def main():
    if len(sys.argv) < 3:
        print("Usage: bh-to-xeto <csv file> <output xeto file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
