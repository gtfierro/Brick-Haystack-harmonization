import buildingmotif
import os
from typing import Optional, List, Tuple
import logging
import brickschema
from buildingmotif.dataclasses import Library, Template
from buildingmotif.utils import template_to_shape, PARAM
import rdflib
from rdflib.term import Node, URIRef
import rfc3987
from brickschema.namespaces import BRICK, RDFS, SH, RDF
import csv
from typing import Set
import importlib_resources
from ontoenv import OntoEnv, Config

A = RDF.type

env = OntoEnv(Config(search_directories=["."]))
env.add("https://brickschema.org/schema/1.4/Brick.ttl")

# set up buildingmotif to read templates
if os.path.exists('bmotif.db'):
    bm = buildingmotif.BuildingMOTIF("sqlite:///bmotif.db", log_level=logging.WARNING, shacl_engine='topquadrant')
    brick_lib = Library.load(ontology_graph='https://brickschema.org/schema/1.4/Brick.ttl', overwrite=False, run_shacl_inference=False)
else:
    bm = buildingmotif.BuildingMOTIF("sqlite:///bmotif.db", log_level=logging.WARNING, shacl_engine='topquadrant')
    bm.setup_tables()
    brick_lib = Library.load(ontology_graph='https://brickschema.org/schema/1.4/Brick.ttl', overwrite=True)
brick = brick_lib.get_shape_collection().graph

# read data/bmotif out of the package data
bmotif_template_path = str(importlib_resources.files('brick_haystack_harmonization.data').joinpath('bmotif'))
lib = Library.load(directory=bmotif_template_path, overwrite=True)


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

    return template_to_shape(templ)

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
    q = """PREFIX ph: <urn:project_haystack/>
    SELECT ?entity ?equip WHERE {
        ?entity ph:hasRefTag ?tag  .
        ?tag ph:key "equipRef"^^xsd:string .
        ?tag ph:value ?equip
    }"""
    for row in graph.query(q, initBindings={"entity": entity}):
        return row[1]


def get_parent(template: Template) -> Tuple[URIRef, URIRef]:
    # get the 'parent' of the template; the "top level" thing.
    # if there is an 'equip' parameter, then the parent is the equip
    # else, if there is a 'part' parameter, then the parent is the part
    # else, the parent is the 'name' parameter
    parent_type = template.body.value(PARAM['equip'], A)
    parent = PARAM['equip']
    if not parent_type:
        parent_type = template.body.value(PARAM['part'], A)
        parent = PARAM['part']
    if not parent_type:
        parent_type = template.body.value(PARAM['name'], A)
        parent = PARAM['name']
    return parent, parent_type


def get_most_specific_template(templates: List[Template], context: brickschema.Graph) -> Template:
    # get the parent type for each template
    template_parent_types = [get_parent(t)[1] for t in templates]
    # the 'most specific' template is the one with the most specific parent type
    # The most specific parent type is the one that isn't a subclass of any other parent type
    for idx, t in enumerate(template_parent_types):
        all_other_types = [p for p in template_parent_types if p != t]
        query = "ASK {" + " UNION ".join([f"{{ {t.n3()} rdfs:subClassOf+ {p.n3()} }}" for p in all_other_types]) + "}"
        if not bool(context.query(query)):
            continue
        print(f"Most specific template is {templates[idx]}")
        return templates[idx]
    return templates[0]
