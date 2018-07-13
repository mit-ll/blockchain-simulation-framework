from enum import Enum
import json
from pprint import pformat

import id_bag
import protocols


class ProtocolType(Enum):
    """The various protocol types supported by this framework.
    """

    BITCOIN = 1
    IOTA = 2


class ProtocolSettings:
    """Stores settings related to blockchain protocols.
    """

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

        self.protocol_type = ProtocolType[data['type']]
        if self.protocol_type == ProtocolType.BITCOIN:
            self.accept_depth = data['acceptDepth']
            self.target_ticks_between_generation = data['targetTicksBetweenGeneration']
        elif self.protocol_type == ProtocolType.IOTA:
            self.target_ticks_between_generation = data['targetTicksBetweenGeneration']
            self.alpha = data['alpha']
            self.required_confidence = data['requiredConfidence']
        else:
            raise NotImplementedError("Selected protocol type is not implemented")

    def getMinerClass(self):
        """
        Returns:
            classobj -- The appropriate class for creating miners based on the protocol type.
        """

        if self.protocol_type == ProtocolType.BITCOIN:
            return protocols.bitcoin.Bitcoin
        elif self.protocol_type == ProtocolType.IOTA:
            return protocols.iota.Iota
        else:
            raise NotImplementedError("Selected protocol type is not implemented")

    def isIdBagSingle(self):
        """Returns True if the protocol uses a singleton IdBag, False otherwise.
        """

        if self.protocol_type == ProtocolType.BITCOIN:
            return True  # All bitcoin miners share one "pool" of tx.
        elif self.protocol_type == ProtocolType.IOTA:
            return False  # Iota miners are responsible for their shepherding their own tx.
        else:
            raise NotImplementedError("Selected protocol type is not implemented")

    def getIdBag(self, simulation):
        """Returns and IdBag object for a miner. Each miner should call this before the simulation starts.

        Arguments:
            simulation {Simulation} -- Simulation object that the idBag(s) will use to keep track of the next id.

        Returns:
            IdBag -- The IdBag object the miner should use during the simulation.
        """

        if self.isIdBagSingle():
            return id_bag.getSingleBag(simulation)  # All bitcoin miners share one "pool" of tx.
        else:
            return id_bag.IdBag(simulation)  # Iota miners are responsible for their shepherding their own tx.

    def __str__(self):
        """        
        Returns:
            str -- String representation of object.
        """

        return pformat(self.__dict__, indent=8)

    def __repr__(self):
        """        
        Returns:
            str -- String representation of object.
        """

        return pformat(self.__dict__, indent=8)
