import pydot
import yaml
from yaml import Loader
import sys


def visualize_taxonomy(taxonomy, output='output.png'):
    """
    'taxonomy' is the yaml-decoded taxonomy file.
    """
    # TODO: color nodes according to defined in Brick and/or Haystack
    graph = pydot.Dot('taxonomy', graph_type='digraph', rankdir='LR')
    for concept_name, concept_defn in taxonomy.items():
        if 'brick' not in concept_defn:
            color = 'orange'
        elif 'haystack' not in concept_defn:
            color = 'blue'
        else:
            color = 'black'
        concept_node = pydot.Node(concept_name, label=concept_name, color=color, penwidth=2)
        graph.add_node(concept_node)
        for parent_concept in concept_defn.get('parents', []):
            parent_node = pydot.Node(parent_concept, label=parent_concept)
            graph.add_node(parent_node)
            graph.add_edge(pydot.Edge(parent_node, concept_node))
    graph.write_png(output)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: visualize_taxonomy <taxonomy.yaml>')
        sys.exit(1)

    if len(sys.argv) == 3:
        output = sys.argv[2]
    else:
        output = 'unified_taxonomy.png'

    taxonomy_file = sys.argv[1]
    taxonomy = yaml.load(open(taxonomy_file), Loader=Loader)
    visualize_taxonomy(taxonomy, output)
