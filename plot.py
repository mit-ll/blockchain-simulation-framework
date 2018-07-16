import networkx as nx
import matplotlib.pyplot as plt
from graphviz import Digraph


def nodeLabel(node, miner_id):
    """
    Arguments:
        node {Node} -- Node to generate graphbiz label for.

    Returns:
        str -- Graphviz label for node.
    """

    tx = node.tx
    conf = 0
    if len(tx.confidence_history):
        for e in tx.confidence_history:
            if e.miner_id == miner_id:
                conf = e.state
    return '<<B>%d</B><BR/>%s<BR/>%d<BR/>%d>' % (tx.id, tx.hash[:4], conf, node.weight)


visited = set()


def dagToDig(miner, node, digraph=None):
    """
    Arguments:
        miner {Miner} -- Miner object whose blockchain view is the DAG.
        node {Node} -- Current node being examined in the DAG.

    Keyword Arguments:
        digraph {graphviz.Digraph} -- Directed graph being built. (default: {None})

    Returns:
        graphviz.Digraph -- Graph created from miner's DAG.
    """

    global visited
    node_id = "%s%d" % (node.tx.hash, miner.id)
    if node in visited:
        return digraph
    if digraph is None:
        digraph = Digraph()
        digraph.graph_attr['rankdir'] = 'RL'
    if node.tx in miner.consensed_tx:
        digraph.node(node_id, label=nodeLabel(node, miner.id), fillcolor='#ffff66', style='filled')
    else:
        digraph.node(node_id, label=nodeLabel(node, miner.id))
    visited.add(node)
    for child in node.children:
        child_id = "%s%d" % (child.tx.hash, miner.id)
        digraph.edge(child_id, node_id)
        dagToDig(miner, child, digraph)
    return digraph


def plotDag(miner, fname='test.gv', view_output=True):
    """Plot the DAG of the miner's view of the blockchain.

    Arguments:
        miner {Miner} -- Miner whose DAG we want to plot.

    Keyword Arguments:
        fname {str} -- Filename to output Graphviz DOT File. (default: {'test.gv'})
    """

    global visited
    visited = set()
    digraph = dagToDig(miner, miner.root)
    digraph.render(fname, view=view_output)


def plotAllDags(miners, fname='testall.gv'):
    """Plot the DAGs of the miners' views of the blockchain.

    Arguments:
        miners {list(Miner)} -- Miners whose DAGs we want to plot.

    Keyword Arguments:
        fname {str} -- Filename to output Graphviz DOT File. (default: {'test.gv'})
    """

    global visited
    first_digraph = None
    for miner in miners:
        visited = set()
        digraph = dagToDig(miner, miner.root)
        if not first_digraph:
            first_digraph = digraph
        else:
            first_digraph.subgraph(digraph)
    first_digraph.render(fname, view=True)


def simplePlot(graph, pos=None):
    """Displays a simple matplotlib plot of a networkx graph
    See https://networkx.github.io/documentation/stable/reference/generated/networkx.drawing.nx_pylab.draw_networkx.html#networkx.drawing.nx_pylab.draw_networkx.

    Arguments:
        graph {networkx.Graph} -- Graph to plot

    Keyword Arguments:
        pos {dict} -- Map of graph node id to tuple of x,y coordinates. (default: {None})
    """

    if pos:
        nx.draw_networkx(graph, with_labels=False, node_size=20, pos=pos)
    else:
        nx.draw_networkx(graph, with_labels=False, node_size=20)
    plt.show()


# Reinstate plotly later if desired.
