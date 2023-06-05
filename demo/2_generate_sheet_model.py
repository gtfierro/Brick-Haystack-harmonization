from rdflib import Namespace, Graph

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model, Template
from typing import Callable, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from buildingmotif.namespaces import bind_prefixes, RDF, RDFS
from buildingmotif.ingresses.base import (
    GraphIngressHandler,
    RecordIngressHandler,
)
from buildingmotif.ingresses.template import _get_term
from brick_haystack_harmonization.common import PH

# setup our buildingmotif instance
bm = BuildingMOTIF("sqlite:///bmotif.db")

# create the model w/ a namespace
BLDG = Namespace("urn:example/")
bldg = Model.create(BLDG)
bind_prefixes(bldg.graph)

nrel_lib = Library.load(name='nrel-templates')
demo_lib = Library.load(name='demolib')
s223 = Library.load(name='http://data.ashrae.org/standard223#')

sensor = nrel_lib.get_template_by_name("sensor").inline_dependencies()
vav_reheat = demo_lib.get_template_by_name("vav-reheat-equip")
vav_reheat.generate_spreadsheet("vav_reheat.xlsx")

rvav1 = BLDG["rvav1"]

bindings, leftover = vav_reheat.inline_dependencies().evaluate(
    {
        "name": rvav1,
        "sup-air-temp-sensor": BLDG["sensor-sat1"],
        "sup-air-flow-sensor": BLDG["sensor-saf1"],
        "sup-air-pressure-sensor": BLDG["sensor-sap1"],
    }
).fill(BLDG)
print(leftover.serialize())
bldg.add_graph(leftover)

for k,v in bindings.items():
    print(f"{k} => {v}")

g = sensor.evaluate(
    {"name": BLDG["sensor-saf1"], "property": bindings["name-sup-air-flow"], "where": bindings["name-dmp-out"]}
)
assert isinstance(g, Graph)
bldg.add_graph(g)
g = sensor.evaluate(
    {"name": BLDG["sensor-sat1"], "property": bindings["name-sup-air-temp"], "where": bindings["name-dmp-out"]}
)
assert isinstance(g, Graph)
bldg.add_graph(g)
g = sensor.evaluate(
    {"name": BLDG["sensor-sap1"], "property": bindings["name-sup-air-pressure"], "where": bindings["name-dmp-out"]}
)
assert isinstance(g, Graph)
bldg.add_graph(g)

for ent in bldg.graph.subjects(RDF.type):
    label = Literal(str(ent).split('/')[-1])
    bldg.graph.add((ent, RDFS.label, Literal(label)))

bldg.graph.serialize('223p-brick-model.ttl')

bm.session.commit()
