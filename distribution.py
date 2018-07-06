from enum import Enum
import math
from numpy import random
from pprint import pformat


class DistributionType(Enum):
    """Types of distributions to sample from.
    """

    CONSTANT = 0
    UNIFORM = 1
    GAUSSIAN = 2
    LAPLACIAN = 3
    EXPONENTIAL = 4


class Distribution:
    """Allows for sampling from different types of probabilistic distributions.
    """

    def __init__(self, settings):
        """Parses the settings in the value parameter.

        Arguments:
            settings {dict} -- The setings for the distribution.
        """

        self.distribution_type = DistributionType[settings['type']]
        if self.distribution_type == DistributionType.UNIFORM:
            self.low = settings['low']
            self.high = settings['high']
        elif self.distribution_type == DistributionType.GAUSSIAN or self.distribution_type == DistributionType.LAPLACIAN:
            self.average = settings['average']
            self.standard_deviation = settings['standardDeviation']
        elif self.distribution_type == DistributionType.EXPONENTIAL:
            self.beta = settings['beta']
        elif self.distribution_type == DistributionType.CONSTANT:
            self.value = settings['value']
        else:
            raise NotImplementedError("Distribution type not yet implemented")

    def sample(self, size=None):
        """Samples from the distribution

        Keyword Arguments:
            size {int or tuple of ints} -- Output shape. If the given shape is, e.g., (m, n, k), then m * n * k samples are drawn.
            If size is None (default), a single value is returned if loc and scale are both scalars. Otherwise,
            np.broadcast(loc, scale).size samples are drawn. (default: {None})

        Returns:
            ndarray or scalar -- Drawn samples from the parameterized distribution.
        """

        if self.distribution_type == DistributionType.UNIFORM:
            return random.uniform(self.low, self.high, size)
        elif self.distribution_type == DistributionType.GAUSSIAN:
            return random.normal(self.average, self.standard_deviation, size)
        elif self.distribution_type == DistributionType.LAPLACIAN:
            return random.laplace(self.average, self.standard_deviation, size)
        elif self.distribution_type == DistributionType.EXPONENTIAL:
            return int(math.ceil(random.exponential(self.beta)))
        elif self.distribution_type == DistributionType.CONSTANT:
            return self.value
        else:
            raise NotImplementedError("Distribution type not yet implemented")

    def __str__(self):
        """        
        Returns:
            str -- String representation of object.
        """

        return pformat(self.__dict__, indent=12)

    def __repr__(self):
        """        
        Returns:
            str -- String representation of object.
        """

        return pformat(self.__dict__, indent=12)
