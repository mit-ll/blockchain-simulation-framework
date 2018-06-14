import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools
import networkx as nx
import matplotlib.pyplot as plt

# == start bitcoin ==================


def printChain(node, acc=None, t=0):
    s = '  '*t+str(node.tx.id)
    if acc and node.tx in acc:
        s += '*'
    print s
    for c in node.children:
        printChain(c, acc, t+1)


def getNextFork(f, used, sign):
    """output must match sign's sign unless sign == 0"""
    i = 1
    while True:
        out = f + i
        if out not in used:
            if sign == 0 or (sign > 0 and out > 0) or (sign < 0 and out < 0):
                return out
        out = f - i
        if out not in used:
            if sign == 0 or (sign > 0 and out > 0) or (sign < 0 and out < 0):
                return out
        i += 1


def nodesToNx(miner, node, g=None, d=0, f=0, lasty=0):
    """d is depth (x coord)
    f is current fork # (y coord)
    nx.node ids must be hashes (otherwise not unique)
    """
    i = node.tx.hash()
    if g is None:
        g = nx.Graph()
        g.add_node(i)
        g.nodes[i]['y'] = f
        g.nodes[i]['id'] = node.tx.id
    g.nodes[i]['x'] = d
    forks = {}  # maps nx.node id (hash) to fork
    myused = set([0])
    for c in node.children:
        ci = c.tx.hash()
        if ci not in g:
            g.add_node(ci)
        g.add_edge(ci, i)
        if c.tx in miner.accepted:
            assert f not in forks.values()
            forks[ci] = f
        else:
            newf = getNextFork(f, myused, lasty)
            assert not ((lasty < 0 and newf > 0) or (lasty > 0 and newf < 0))
            forks[ci] = newf
            myused.add(newf)
    for c in node.children:
        ci = c.tx.hash()
        myf = forks[ci]
        g.nodes[ci]['y'] = myf
        g.nodes[ci]['id'] = c.tx.id
        nodesToNx(miner, c, g, d+1, myf, g.nodes[i]['y'])
    return g


def plotChain(miner):
    v = nodesToNx(miner, miner.root)
    p = {i: (v.nodes[i]['x'], v.nodes[i]['y']) for i in v.nodes}
    l = {i: v.nodes[i]['id'] for i in v.nodes}
    nx.draw_networkx(v, node_color='#ff6666', node_size=20, pos=p, labels=l)
    plt.show()

# == end bitcoin ====================

# == start iota =====================


def iotaNodesToNx(node, g=None):  # note: this doesn't work for bitcoin because of dupe ids
    i = node.tx.id
    if g is None:
        g = nx.Graph()
        if i not in g:  # only need to do this for the root
            g.add_node(i)
            g.nodes[i]['children'] = 1  # len(node.children)
    for c in node.children:
        ci = c.tx.id
        if ci not in g:
            g.add_node(ci)
            g.nodes[ci]['children'] = len(c.children)
        g.add_edge(ci, i)
        iotaNodesToNx(c, g)
    return g


def plotTangle(root):
    v = iotaNodesToNx(root)
    simplePlot(v, {i: (i*2, v.nodes[i]['children']-1 if i % 2 else (v.nodes[i]['children']-1)*-1)for i in v.nodes})

# == end iota =======================


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
