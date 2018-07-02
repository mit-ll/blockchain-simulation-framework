import json
import networkx as nx

import transaction


class GraphEncoder(json.JSONEncoder):
    """A JSONEncoder for serialzing networkx.Graph objects.    
    """

    def default(self, obj):
        if isinstance(obj, nx.Graph):
            return {
                "_type": "nx.Graph",
                "value": nx.node_link_data(obj)
            }
        return super(GraphEncoder, self).default(obj)


class GraphDecoder(json.JSONDecoder):
    """A JSONEncoder for deserialzing networkx.Graph objects.    
    """

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        type = obj['_type']
        if type == 'nx.Graph':
            return nx.node_link_graph(obj['value'])
        return obj
