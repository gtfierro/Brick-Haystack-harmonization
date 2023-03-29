from common import taglist_to_set, read_csv, fixup_tags

def base_to_xeto(row: dict) -> str:
    point_class = row["Brick:PointClass"]
    tags = taglist_to_set(row["Haystack:Markers"])
    tags.add(row["Brick:L1PointClass"])
    fixup_tags(tags)
    tag_list = ', '.join(tags)
    return f"Brick_{point_class} : Point {{ {tag_list} }}"


def subparts_to_xeto(row: dict) -> str:
    point_class = row["Brick:PointClass"]
    l0class = row["Subpart:EntityClassL0"]
    l1class = row["Subpart:EntityClassL1"]
    return(point_class, l0class, l1class)

def run():
    statements = []
    for row in read_csv():
        if row["Meta:State"] == "Base":
            statements.append(base_to_xeto(row) + '\n')
        elif row["Meta:State"] == "Subparts":
            print(subparts_to_xeto(row))
    with open('brick.xeto', 'w') as f:
        f.writelines(statements)


if __name__ == "__main__":
    run()
