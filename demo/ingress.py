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
class TemplateIngress(GraphIngressHandler):
    """
    Reads records and attempts to instantiate the given template
    with each record. Produces a graph.

    If 'inline' is True, inlines all templates when they are instantiated.
    """

    def __init__(
        self,
        template: Template,
        mapper: Optional[Callable[[str], str]],
        upstream: RecordIngressHandler,
        inline: bool = False,
    ):
        """
        Create a new TemplateIngress handler

        :param template: the template to instantiate on each record
        :type template: Template
        :param mapper: Function which takes a column name as input and returns
                       the name of the parameter the corresponding cell should
                       be bound to. If None, uses the column name as the
                       parameter name
        :type mapper: Optional[Callable[[str], str]]
        :param upstream: the ingress handler from which to source records
        :type upstream: RecordIngressHandler
        :param inline: if True, inline the template before evaluating it on
                      each row, defaults to False
        :type inline: bool, optional
        """
        self.mapper = mapper if mapper else lambda x: x
        self.upstream = upstream
        if inline:
            self.template = template.inline_dependencies()
        else:
            self.template = template

    def graph(self, ns: Namespace) -> Graph:
        g = Graph()

        records = self.upstream.records
        assert records is not None
        for rec in records:
            bindings = {self.mapper(k): _get_term(v, ns) for k, v in rec.fields.items()}
            templ = self.template.evaluate(bindings)
            if isinstance(templ, Graph):
                g += templ
            else:
                g += templ.fill(ns)[1]
        return g

