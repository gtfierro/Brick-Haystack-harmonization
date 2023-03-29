import csv
from typing import Set

def taglist_to_set(taglist: str) -> Set[str]:
    return set(map(lambda x: x.strip(), taglist.split(",")))


def read_csv(filename: str):
    with open(filename) as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            yield row

def fixup_tags(tags: Set[str]):
    replacements = {
        "Sensor": "sensor",
        "Setpoint": "sp",
        "Command": "cmd",
        "Status": "status",
        "Alarm": "alarm",
    }
    for t in tags.copy():
        if '|' in t:
            tags.remove(t)
            tags.add(t.split('|')[0])
        if '(' in t and ')' in t:
            tags.remove(t)
        elif t in replacements:
            tags.remove(t)
            tags.add(replacements[t])

