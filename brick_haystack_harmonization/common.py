import rdflib
from brickschema.namespaces import BRICK, RDFS
import csv
from typing import Set

replacements = {
    "Sensor": "sensor",
    "Setpoint": "sp",
    "Command": "cmd",
    "Status": "status",
    "Alarm": "alarm",
    "Temperature": "temp",
}


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
