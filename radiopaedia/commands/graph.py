from radiopaedia.graph import load_stats, load_graph, load_percentage_of_symmetric_links
import json
import matplotlib.pyplot as plt
import seaborn as sns


def execute(category='anatomy', output='output'):
    graph = load_graph(category)
    stats = load_stats(category)
    print('There are {} % of symmetric links.'.format(int(round(100 * load_percentage_of_symmetric_links(category)))))
    for stat in ['degree_in', 'degree_out', 'pagerank']:
        sns.distplot(stats[stat], bins=20, kde=False)
        plt.savefig('{}/{}_hist.svg'.format(output, stat))
        plt.close()
    print(stats.head())
    with open('{}/graph.json'.format(output), 'w') as f:
        json.dump(graph, f, sort_keys=True)
