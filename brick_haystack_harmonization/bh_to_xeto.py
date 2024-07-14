import brickschema
from brickschema.namespaces import SKOS, BRICK, RDFS
from buildingmotif.namespaces import PARAM
import os
from typing import List
import pathlib
import sys
from .common import (
    taglist_to_set,
    read_csv,
    fixup_tags,
    clean_brick_classname,
    guess_tags,
    brick
)

class BHtoXetoConverter:
    
    def __init__(self):
        self.seen_classes = set()
        self.parent_classes = set()
        self.buildingmotif_template_file_content = ''

    def base_to_xeto(self, row: dict) -> str:
        point_class = clean_brick_classname(row["Brick:PointClass"])
        if BRICK[point_class] in self.seen_classes:
            return ""
        self.seen_classes.add(BRICK[point_class])
        tags = taglist_to_set(row["Haystack:Markers"])
        tags.update(taglist_to_set(row["Haystack:CustomMarkers"]))
        tags.add(row["Brick:L1PointClass"])
        fixup_tags(tags)
        if len(tags) > 1:
            tag_list = ", ".join(sorted(tags))
        else:
            tag_list = tags.pop()
        return self.make_statement(point_class, tag_list)

    def equip_to_xeto(self, row: dict) -> str:
        equip_class = clean_brick_classname(row["Subpart:EntityClassL0"])
        if BRICK[equip_class] in self.seen_classes:
            return ""
        self.seen_classes.add(BRICK[equip_class])
        tags = taglist_to_set(row["Haystack:Markers"])
        tags.update(taglist_to_set(row["Haystack:CustomMarkers"]))
        fixup_tags(tags)
        if len(tags) > 1:
            tag_list = ", ".join(sorted(tags))
        else:
            tag_list = tags.pop()
        return self.make_statement(equip_class, tag_list)

    def make_statement(self, point_class: str, tag_list: str) -> str:
        parent = brick.value(subject=BRICK[point_class], predicate=RDFS.subClassOf)

        # do not include these classes as a parent class in the XETO file.
        # This is because they have tags which do not agree with the haystack
        # structure. For example, Air_Quality_Sensor has tags "air" and "quality",
        # which interfere with correct detection of CO2_Sensor, which only has hasytack 
        # tags of "co2", "air", and "sensor"
        parents_to_skip = {
            BRICK.Air_Quality_Sensor,
        }
        # if the parent is in the list of parents to skip, then we should skip this class by
        # replacing 'parent' with parent's parent class as determined by graph 'g'
        while parent in parents_to_skip:
            parent = brick.value(subject=parent, predicate=RDFS.subClassOf)
        if parent is None:
            parent = "Entity"
        else:
            self.parent_classes.add(parent)
            parent = f"Brick_{parent.split('#')[-1].replace('.','').replace('-','')}"

        defn = brick.value(subject=BRICK[point_class], predicate=SKOS.definition)
        if defn is not None:
            return f'// {defn}\nBrick_{point_class.replace(".", "").replace("-","")}: {parent} <uri:"{BRICK[point_class]}"> {{ {tag_list} }}\n'
        else:
            return f'\nBrick_{point_class.replace(".", "").replace("-","")}: {parent} <uri:"{BRICK[point_class]}"> {{ {tag_list} }}\n'

    def subparts_to_xeto(self, row: dict):
        point_class = clean_brick_classname(row["Brick:PointClass"])
        l0class = clean_brick_classname(row["Subpart:EntityClassL0"])
        l1class = clean_brick_classname(row["Subpart:EntityClassL1"])
        tags = taglist_to_set(row["Haystack:Markers"])
        ctags = taglist_to_set(row["Haystack:CustomMarkers"])
        tags.update(ctags)
        fixup_tags(tags)
        assert len(tags) > 0, f'Markers? {row}'
        if len(tags) > 1:
            tag_list = ", ".join(sorted(tags))
        else:
            tag_list = tags.pop()

        xeto_type_name = f"Brick_{l0class}_{point_class}"
        if l1class:
            xeto_type_name = f"Brick_{l1class}_{xeto_type_name}"

        if xeto_type_name in self.seen_classes:
            return ""
        self.seen_classes.add(xeto_type_name)

        # TODO: what is the 'name' of the compound class?
        # TODO: create building motif template
        # TODO: come up with a way of minting names for the points, etc
        if not l1class:
            # l0class hasPoint point_class
            template = f"""
        {xeto_type_name}:
          body: >
            @prefix P: <urn:___param___#> .
            @prefix brick: <https://brickschema.org/schema/Brick#> .
            P:name a brick:{row['Brick:PointClass']} ;
                brick:isPointOf P:part .
            P:part a brick:{row['Subpart:EntityClassL0']} ;
                brick:hasPoint P:name .
          dependencies:
          - template: https://brickschema.org/schema/Brick#{row['Subpart:EntityClassL0']}
            library: https://brickschema.org/schema/1.4/Brick
            args: {{"name": "part"}}
          - template: https://brickschema.org/schema/Brick#{row['Brick:PointClass']}
            library: https://brickschema.org/schema/1.4/Brick
            args: {{"name": "name"}}
                """
        else:
            # l1class hasPoint point_class
            # l0class hasPart l1class
            template = f"""
        {xeto_type_name}:
          body: >
            @prefix P: <urn:___param___#> .
            @prefix brick: <https://brickschema.org/schema/Brick#> .
            P:name a brick:{row['Brick:PointClass']} .
            P:equip a brick:{row['Subpart:EntityClassL0']} ;
                brick:hasPart P:part .
            P:part a brick:{row['Subpart:EntityClassL1']} ;
                brick:hasPoint P:name .
          dependencies:
          - template: https://brickschema.org/schema/Brick#{row['Subpart:EntityClassL0']}
            library: https://brickschema.org/schema/1.4/Brick
            args: {{"name": "equip"}}
          - template: https://brickschema.org/schema/Brick#{row['Subpart:EntityClassL1']}
            library: https://brickschema.org/schema/1.4/Brick
            args: {{"name": "part"}}
          - template: https://brickschema.org/schema/Brick#{row['Brick:PointClass']}
            library: https://brickschema.org/schema/1.4/Brick
            args: {{"name": "name"}}
                """
            pass
        self.buildingmotif_template_file_content += template
        return self.make_templ_statement(point_class, xeto_type_name, tag_list)

    def make_templ_statement(self, point_class: str, template_name: str, tag_list: str) -> str:
        parent = brick.value(subject=BRICK[point_class], predicate=RDFS.subClassOf)
        if parent is None or parent == BRICK["Point"]:
            parent = "Point"
        else:
            self.parent_classes.add(parent)
            parent = f"Brick_{parent.split('#')[-1].replace('.','').replace('-','')}"

        return f'\n{template_name} : {parent} <template:"{template_name}", uri:"{PARAM[template_name]}"> {{ {tag_list} }}\n'

    def run(self, filename: str, xeto_file: str, template_file: str):
        statements = []
        for row in read_csv(filename):
            if 'check' in row.values():
                print(f"Skipping {row} because of 'check'")
                continue
            if row["Meta:State"] == "Base":
                statements.append(self.base_to_xeto(row) + "\n")
            elif row["Meta:State"] == "Subparts":
                statements.append(self.subparts_to_xeto(row) + "\n")
            elif row["Meta:State"] == "Equip":
                statements.append(self.equip_to_xeto(row) + "\n")
            # TODO: add support for locations
        with open(template_file, 'w') as f:
            f.write(self.buildingmotif_template_file_content)

        # compute any classes which show up as parents but aren't already
        # in the file
        while len(self.parent_classes):
            leftover = self.parent_classes - self.seen_classes
            if not leftover:
                break
            for concept in leftover:
                if concept in self.seen_classes:
                    continue
                self.seen_classes.add(concept)

                tags = guess_tags(brick, concept)
                fixup_tags(tags)
                statements.append(self.make_statement(concept.split("#")[-1], ", ".join(tags)))
                self.parent_classes.remove(concept)

        # library name
        libfile = pathlib.Path(xeto_file).with_name("lib.xeto")
        # create output directory
        os.makedirs(libfile.parent, exist_ok=True)
        # write xeto file
        with open(xeto_file, "w") as f:
            f.writelines(statements)
            f.write('Brick_Site : Entity <uri:"https://brickschema.org/schema/Brick#Site"> { site }\n')

        # write library file
        mappings = dict(brick.namespace_manager.namespaces())
        brick_base_uri = mappings["brick"]
        with open(libfile, "w") as f:
            f.write(
                f"""
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
        >"""
            )

def main():
    if len(sys.argv) < 3:
        print("Usage: bh-to-xeto <csv file> <output xeto file>")
        sys.exit(1)
    converter = BHtoXetoConverter()
    converter.run(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
