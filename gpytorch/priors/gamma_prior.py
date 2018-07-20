from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from numbers import Number

import torch
from torch.distributions.gamma import Gamma
from gpytorch.priors.prior import TorchDistributionPrior


class GammaPrior(TorchDistributionPrior):
    """Gamma Prior parameterized by concentration and rate

    pdf(x) = beta^alpha / Gamma(alpha) * x^(alpha - 1) * exp(-beta * x)

    were alpha > 0 and beta > 0 are the concentration and rate parameters, respectively.
    """

    def __init__(self, concentration, rate, log_transform=False, size=None):
        if isinstance(concentration, Number) and isinstance(rate, Number):
            concentration = torch.full((size or 1,), float(concentration))
            rate = torch.full((size or 1,), float(rate))
        elif not (torch.is_tensor(concentration) and torch.is_tensor(rate)):
            raise ValueError("concentration and rate must be both either scalars or Tensors")
        elif concentration.shape != rate.shape:
            raise ValueError("concentration and rate must have the same shape")
        elif size is not None:
            raise ValueError("can only set size for scalar concentration and rate")
        super(GammaPrior, self).__init__()
        self.register_buffer("concentration", concentration.view(-1).clone())
        self.register_buffer("rate", rate.view(-1).clone())
        self._log_transform = log_transform
        self._initialize_distributions()

    def _initialize_distributions(self):
        self._distributions = [
            Gamma(concentration=c, rate=r, validate_args=True) for c, r in zip(self.concentration, self.rate)
        ]

    def is_in_support(self, parameter):
        return bool((parameter > 0).all().item())
