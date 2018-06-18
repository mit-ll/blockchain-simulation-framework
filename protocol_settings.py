from enum import Enum
import json
from pprint import pformat

import protocols


class ProtocolType(Enum):
    """The various protocol types supported by this framework.
    """
    BITCOIN = 1
    IOTA = 2


class ProtocolSettings:
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
            self.transaction_generation_probability = data['transactionGenerationProbability']
        elif self.protocol_type == ProtocolType.IOTA:
            self.transaction_generation_probability = data['transactionGenerationProbability']
        else:
            raise NotImplementedError("Selected protocol type is not implemented")

    def getMinerClass(self):
        """Gets the appropriate class for creating miners based on the protocol type.
        """
        if self.protocol_type == ProtocolType.BITCOIN:
            return protocols.bitcoin.Bitcoin
        elif self.protocol_type == ProtocolType.IOTA:
            return protocols.iota.Iota
        else:
            raise NotImplementedError("Selected protocol type is not implemented")

    def __str__(self):
        return pformat(self.__dict__, indent=8)

    def __repr__(self):
        return pformat(self.__dict__, indent=8)
