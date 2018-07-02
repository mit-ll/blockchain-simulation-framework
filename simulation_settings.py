from enum import Enum
import json
from pprint import pformat

import logging
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
        """
        Arguments:
            fname {str} -- Filename to load settings from.
        """

        with open(fname, 'r') as settingsFile:
            data = json.load(settingsFile)

        # Load settings.
        self.number_of_executions = data['numberOfExecutions']
        self.topology_selection = TopologySelection[data['topologySelection']]
        self.termination_condition = TerminationCondition[data['terminationCondition']]
        self.termination_value = data['terminationValue']

        self.target_termination_ticks = -1

        # Parameterize in JSON later?
        self.allow_termination_cooldown = True
        self.hard_limit_ticks = 1000  # Should this be a function of the number of miners?

        # Load the other settings objects.
        self.topology = TopologySettings(data['topology'])
        self.protocol = ProtocolSettings(data['protocol'])

    def shouldMakeNewTx(self, simulation):
        """Returns True if the simulation should generate more transactions, False otherwise.

        Arguments:
            simulation {Simulation} -- The simulation in question.
        """
        return not self.shouldFinish(simulation)

    def shouldFinish(self, simulation):
        """Returns True if the simulation termination condition is met, False otherwise.

        Arguments:
            simulation {Simulation} -- The simulation in question.
        """

        if self.termination_condition == TerminationCondition.NUMBER_OF_GENERATED_TRANSACTIONS:
            return simulation.next_id > self.termination_value  # Conditioned on next_id, not len(all_tx) so that reiusses don't count.
        elif self.termination_condition == TerminationCondition.NUMBER_OF_TIME_TICKS:
            return simulation.tick > self.termination_value
        else:
            raise NotImplementedError("Selected termination condition is not implemented.")

    def shouldTerminate(self, simulation):
        """Returns True if the simulation should immediately terminate (termination condition is met and either allow_termination_cooldown is False, cooldown is finished, or hard_limit is reached), False otherwise.

        Arguments:
            simulation {Simulation} -- The simulation in question.
        """

        should_finish = self.shouldFinish(simulation)
        if not should_finish:
            return False
        elif not self.allow_termination_cooldown:
            return True

        if should_finish and self.target_termination_ticks < 0:  # Set the target if it hasn't been set already.
            self.target_termination_ticks = simulation.tick + self.hard_limit_ticks

        if simulation.tick > self.target_termination_ticks:
            logging.info("Terminating due to surpassed hard tick limit.")
            return True

        miners_have_msgs = bool([True for node_id in simulation.graph.nodes if simulation.graph.nodes[node_id]['miner'].queue])
        return not miners_have_msgs

    def __str__(self):
        """        
        Returns:
            str -- String representation of object.
        """

        return pformat(self.__dict__, indent=4)

    def __repr__(self):
        """        
        Returns:
            str -- String representation of object.
        """

        return pformat(self.__dict__, indent=4)
