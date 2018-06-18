from enum import Enum
from numpy import random
from pprint import pformat


class DistributionType(Enum):
    """Types of distributions to sample from.
    """
    UNIFORM = 1,
    GAUSSIAN = 2,
    LAPLACIAN = 3


class Distribution:
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
        else:
            raise NotImplementedError("Distribution type not yet implemented")

    def __str__(self):
        return pformat(self.__dict__, indent=12)

    def __repr__(self):
        return pformat(self.__dict__, indent=12)
