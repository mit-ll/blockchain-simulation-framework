from enum import Enum
import json
import networkx
from pprint import pformat

from distribution import Distribution

class TopologyType(Enum):
    """Types of miner topologies.
    """
    STATIC = 1,  # Load the topology from a file.
    GEOMETRIC_UNIFORM_DELAY = 2,
    LOBSTER_UNIFORM_DELAY = 3  # TODO: Toy example that should eventually be removed.
    # TODO: Add appropraite types


class TopologySettings:
    def __init__(self, value):
        """Parses the settings in the value parameter.

        Arguments:
            value {str|dict} -- If a string, it is a pointer to a JSON-encoded file containing the settings. If a dict, then it is the settings.
        """
        if type(value) is str:
            # Treat the value as a file locator.
            with open(value, 'r') as settingsFile:
                data = json.load(settingsFile)
        else:
            data = value

        self.topology_type = TopologyType[data['type']]
        if self.topology_type == TopologyType.STATIC:
            raise NotImplementedError("Static topologies are not yet implemented")
        else:
            self.number_of_miners = data['numberOfMiners']

            if self.topology_type == TopologyType.GEOMETRIC_UNIFORM_DELAY or self.topology_type == TopologyType.LOBSTER_UNIFORM_DELAY:
                # Graphs with uniform delays for message transmission.
                self.network_delay = Distribution(data['networkDelay'])

                if self.topology_type == TopologyType.GEOMETRIC_UNIFORM_DELAY:
                    self.radius = data['radius']
                elif self.topology_type == TopologyType.LOBSTER_UNIFORM_DELAY:
                    self.p1 = data['p1']
                    self.p2 = data['p2']
            else:
                raise NotImplementedError("Selected topology type is not implemented.")

    def generateMinerGraph(self):
        """Generates a miner graph based on the settings in this object.
        """
        if self.topology_type == TopologyType.STATIC:
            raise NotImplementedError("Static topologies are not yet implemented")
        else:
            if self.topology_type == TopologyType.GEOMETRIC_UNIFORM_DELAY or self.topology_type == TopologyType.LOBSTER_UNIFORM_DELAY:
                # Graphs with uniform delays for message transmission.
                if self.topology_type == TopologyType.GEOMETRIC_UNIFORM_DELAY:
                    graph = networkx.random_geometric_graph(self.number_of_miners, self.radius)
                elif self.topology_type == TopologyType.LOBSTER_UNIFORM_DELAY:
                    graph = networkx.random_lobster(self.number_of_miners, self.p1, self.p2)

                for edge in graph.edges:
                    graph.edges[edge]['network_delay'] = self.network_delay
            else:
                raise NotImplementedError("Selected topology type is not implemented.")

    def __str__(self):
        return pformat(self.__dict__, indent=8)

    def __repr__(self):
        return pformat(self.__dict__, indent=8)
