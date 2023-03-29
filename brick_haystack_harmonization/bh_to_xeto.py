import sys
from .common import taglist_to_set, read_csv, fixup_tags

def base_to_xeto(row: dict) -> str:
    point_class = row["Brick:PointClass"]
    tags = taglist_to_set(row["Haystack:Markers"])
    tags.add(row["Brick:L1PointClass"])
    fixup_tags(tags)
    tag_list = ', '.join(tags)
    return f"Brick_{point_class} : Point {{ {tag_list} }}"


# TODO
def subparts_to_xeto(row: dict):
    point_class = row["Brick:PointClass"]
    l0class = row["Subpart:EntityClassL0"]
    l1class = row["Subpart:EntityClassL1"]
    return (point_class, l0class, l1class)

def run(filename: str, outputfile: str):
    statements = []
    for row in read_csv(filename):
        if row["Meta:State"] == "Base":
            statements.append(base_to_xeto(row) + '\n')
        elif row["Meta:State"] == "Subparts":
            print(subparts_to_xeto(row))
    with open(outputfile, 'w') as f:
        f.writelines(statements)


def main():
    if len(sys.argv) < 3:
        print("Usage: bh-to-xeto <csv file> <output xeto file>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
