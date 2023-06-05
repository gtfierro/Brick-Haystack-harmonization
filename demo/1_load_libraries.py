from rdflib import Namespace, Graph

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model, Template
from typing import Callable, Optional

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.term import Node

from buildingmotif.ingresses.base import (
    GraphIngressHandler,
    RecordIngressHandler,
)
from buildingmotif.ingresses.template import _get_term

# setup our buildingmotif instance
bm = BuildingMOTIF("sqlite:///bmotif.db")
bm.setup_tables()
Library.load_from_libraries_yml("buildingmotif.libraries.yml")
bm.session.commit()
