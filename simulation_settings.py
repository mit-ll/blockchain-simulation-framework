from enum import Enum
import json
from pprint import pformat

from protocol_settings import ProtocolSettings
from topology_settings import TopologySettings


class TopologySelection(Enum):
    """Enumeration of the possible topology selection.
    """
    GENERATE_ONCE = 1
    GENERATE_EACH_TIME = 2


class TerminationCondition(Enum):
    """Enumeration tracking when an individual simulation terminates.
    """
    NUMBER_OF_GENERATED_TRANSACTIONS = 1,
    NUMBER_OF_TIME_TICKS = 2


class SimulationSettings:
    """Handles loading simulation settings information from a file.
    """

    def __init__(self, fname):
        with open(fname, 'r') as settingsFile:
            data = json.load(settingsFile)

        # Load settings.
        self.number_of_executions = data['numberOfExecutions']
        self.topology_selection = TopologySelection[data['topologySelection']]
        self.termination_condition = TerminationCondition[data['terminationCondition']]
        self.termination_value = data['terminationValue']

        # Load the other settings objects
        self.topology = TopologySettings(data['topology'])
        self.protocol = ProtocolSettings(data['protocol'])

    def __str__(self):
        return pformat(self.__dict__, indent=4)

    def __repr__(self):
        return pformat(self.__dict__, indent=4)
