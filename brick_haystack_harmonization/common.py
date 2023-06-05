import buildingmotif
import os
from typing import Optional
import logging
from buildingmotif.dataclasses import Library
import rdflib
from rdflib.term import Node
import rfc3987
from brickschema.namespaces import BRICK, RDFS, SH
import csv
from typing import Set

# set up buildingmotif to read templates
if os.path.exists('/tmp/bmotif.db'):
    bm = buildingmotif.BuildingMOTIF("sqlite://///tmp/bmotif.db", log_level=logging.WARNING)
else:
    bm = buildingmotif.BuildingMOTIF("sqlite://///tmp/bmotif.db", log_level=logging.WARNING)
    bm.setup_tables()
Library.load(ontology_graph='Brick.ttl', overwrite=False)
lib = Library.load(directory='data/bmotif/', overwrite=True)
PH = rdflib.Namespace("urn:project_haystack/")

replacements = {
    "Sensor": "sensor",
    "Setpoint": "sp",
    "Command": "cmd",
    "Status": "status",
    "Alarm": "alarm",
    "Temperature": "temp",
}


def get_template_shape(template_name: str) -> rdflib.Graph:
    """
    Given the name of a template (in data/bmotif/templates.yml),
    it returns the SHACL shape corresponding to the template
    """
    templ = lib.get_template_by_name(template_name)
    print(templ.inline_dependencies().body.serialize())
    return templ.to_nodeshape()


def clean_brick_classname(cls: str) -> str:
    return cls.replace(" ", "_")


def taglist_to_set(taglist: str) -> Set[str]:
    return set(filter(lambda x: x, map(lambda x: x.strip(), taglist.split(","))))


def read_csv(filename: str):
    with open(filename) as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            yield row


def fixup_tags(tags: Set[str]):
    for t in tags.copy():
        if "|" in t:
            tags.remove(t)
            tags.add(t.split("|")[0])
        if "(" in t and ")" in t:
            tags.remove(t)
        if '{' in t or '}' in t:
            tags.remove(t)
        if '.' in t:
            tags.remove(t)
            tags.add(t.replace('.','_'))
        elif t in replacements:
            tags.remove(t)
            tags.add(replacements[t])


def guess_tags(brick: rdflib.Graph, concept: rdflib.URIRef) -> Set[str]:
    tags = brick.objects(concept, BRICK.hasAssociatedTag)
    ret = set()
    for tag in tags:
        tstr = brick.value(tag, RDFS.label)
        tstr = str(tag).split("#")[-1] if tstr is None else str(tstr)
        tstr = replacements.get(tstr, tstr).lower()
        ret.add(tstr)
    return ret


def validate_uri(uri: str) -> bool:
    parsed = rfc3987.parse(uri)
    return parsed["scheme"]


def keep_marker_tag_property_shapes(root: Node, sg: rdflib.Graph):
    """Removes all property shapes that aren't about
    haystack tags"""
    pshapes = list(sg.objects(root, SH.property))
    for pshape in pshapes:
        if not str(sg.value(pshape, SH.path)).startswith(PH):
            sg.remove((root, SH.property, pshape))
            sg.remove((pshape, None, None))


def get_equip_ref(entity: Node, graph: rdflib.Graph) -> Optional[Node]:
    q = """SELECT ?entity ?equip WHERE {
        ?entity ph:hasRefTag ?tag  .
        ?tag ph:key "equipRef"^^xsd:string .
        ?tag ph:value ?equip
    }"""
    for row in graph.query(q, initBindings={"entity": entity}):
        return row[1]
