import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools
import networkx as nx
import matplotlib.pyplot as plt
from graphviz import Digraph


def nodeLabel(node):
    x = node.tx
    return '<<B>'+str(x.id)+'</B><BR/>'+x.hash()[:4]+'>'


visited = set()


def dagToDig(miner, node, d=None):
    global visited
    i = node.tx.hash()
    if node in visited:
        return d
    if d is None:
        d = Digraph()
        d.graph_attr['rankdir'] = 'RL'
    if node.tx in miner.accepted:
        d.node(i, label=nodeLabel(node), fillcolor='#ffff66', style='filled')
    else:
        d.node(i, label=nodeLabel(node))
    visited.add(node)
    for c in node.children:
        ci = c.tx.hash()
        d.edge(ci, i)
        dagToDig(miner, c, d)
    return d


def plotDag(miner, fname='test.gv'):
    global visited
    visited = set()
    d = dagToDig(miner, miner.root)
    d.render(fname, view=True)


def simplePlot(G, p=None):
    """see https://networkx.github.io/documentation/stable/reference/generated/networkx.drawing.nx_pylab.draw_networkx.html#networkx.drawing.nx_pylab.draw_networkx
    p is pos
    """
    if p:
        nx.draw_networkx(G, with_labels=False, node_size=20, pos=p)
    else:
        nx.draw_networkx(G, with_labels=False, node_size=20)
    plt.show()


def plotGraph(G, title='Network graph made with Python'):
    """from https://plot.ly/python/network-graphs/"""
    plotly.tools.set_credentials_file(
        username='gspend', api_key='E9v3qLGDqVSS5GYw1mYa')

    edge_trace = go.Scatter(
        x=[],
        y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    for edge in G.edges():
        x0, y0 = G.node[edge[0]]['pos']
        x1, y1 = G.node[edge[1]]['pos']
        edge_trace['x'] += [x0, x1, None]
        edge_trace['y'] += [y0, y1, None]

    node_trace = go.Scatter(
        x=[],
        y=[],
        text=[],
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            # colorscale options
            # 'Greys' | 'Greens' | 'Bluered' | 'Hot' | 'Picnic' | 'Portland' |
            # Jet' | 'RdBu' | 'Blackbody' | 'Earth' | 'Electric' | 'YIOrRd' | 'YIGnBu'
            colorscale='YIGnBu',
            reversescale=True,
            color=[],
            size=10,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            ),
            line=dict(width=2)))

    for node in G.nodes():
        x, y = G.node[node]['pos']
        node_trace['x'].append(x)
        node_trace['y'].append(y)

    for node, adj in enumerate(G.adjacency()):
        adjacencies = adj[1]
        node_trace['marker']['color'].append(len(adjacencies))
        node_info = 'Node: '+str(node)+'; Connections: '+str(len(adjacencies))
        node_trace['text'].append(node_info)

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
        title='<br>'+title,
        titlefont=dict(size=16),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        annotations=[dict(showarrow=False, xref="paper", yref="paper", x=0.005, y=-0.002)],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))

    py.plot(fig, filename='networkx')


if __name__ == "__main__":
    g = nx.random_geometric_graph(200, 0.125)
    plotGraph(g)
