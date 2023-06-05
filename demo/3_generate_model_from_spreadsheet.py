from rdflib import Namespace, Graph, Literal
from buildingmotif.namespaces import bind_prefixes, RDF, RDFS
from buildingmotif import BuildingMOTIF
from ingress import TemplateIngress
from buildingmotif.ingresses.xlsx import XLSXIngress
from buildingmotif.dataclasses import Library, Model, Template

bm = BuildingMOTIF("sqlite:///bmotif.db")
BLDG = Namespace("urn:example/")
PH = Namespace("urn:project_haystack/")

demo_lib = Library.load(name='demolib')
vav_reheat = demo_lib.get_template_by_name("vav-reheat-equip")

reader = XLSXIngress("vav_reheat.xlsx")
generator = TemplateIngress(vav_reheat, None, reader, inline=True)
g = generator.graph(BLDG)
bind_prefixes(g)

#for ent in g.subjects(RDF.type, PH.Entity):
#    label = Literal(str(ent).split('/')[-1])
#    g.add((ent, RDFS.label, label))
for ent in g.subjects(RDF.type):
    #label = Literal(str(ent).split('/')[-1])
    g.add((ent, RDFS.label, Literal(str(ent))))
g.serialize("from-spreadsheet.ttl")
