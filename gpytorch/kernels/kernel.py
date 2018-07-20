from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from abc import abstractmethod
import torch
from torch.nn import ModuleList
from gpytorch.lazy import LazyEvaluatedKernelVariable, ZeroLazyVariable
from gpytorch.module import Module
from gpytorch.priors._compatibility import _bounds_to_prior
from gpytorch.utils import prod


class Kernel(Module):
    def __init__(
        self,
        has_lengthscale=False,
        ard_num_dims=None,
        log_lengthscale_prior=None,
        active_dims=None,
        batch_size=1,
        log_lengthscale_bounds=None,
    ):
        super(Kernel, self).__init__()
        if active_dims is not None and not torch.is_tensor(active_dims):
            active_dims = torch.tensor(active_dims, dtype=torch.long)
        self.active_dims = active_dims
        self.ard_num_dims = ard_num_dims
        if has_lengthscale:
            lengthscale_num_dims = 1 if ard_num_dims is None else ard_num_dims
            log_lengthscale_prior = _bounds_to_prior(prior=log_lengthscale_prior, bounds=log_lengthscale_bounds)
            self.register_parameter(
                name="log_lengthscale",
                parameter=torch.nn.Parameter(torch.zeros(batch_size, 1, lengthscale_num_dims)),
                prior=log_lengthscale_prior,
            )

    @property
    def lengthscale(self):
        if "log_lengthscale" in self.named_parameters().keys():
            return self.log_lengthscale.exp()
        else:
            return None

    @abstractmethod
    def forward(self, x1, x2, **params):
        raise NotImplementedError()

    def __call__(self, x1_, x2_=None, **params):
        if self.active_dims is not None:
            x1 = x1_.index_select(-1, self.active_dims)
            if x2_ is not None:
                x2 = x2_.index_select(-1, self.active_dims)
        else:
            x1 = x1_
            x2 = x2_

        if x2 is None:
            x2 = x1

        # Give x1 and x2 a last dimension, if necessary
        if x1.ndimension() == 1:
            x1 = x1.unsqueeze(1)
        if x2.ndimension() == 1:
            x2 = x2.unsqueeze(1)
        if not x1.size(-1) == x2.size(-1):
            raise RuntimeError("x1 and x2 must have the same number of dimensions!")

        return LazyEvaluatedKernelVariable(self, x1, x2)

    def __add__(self, other):
        return AdditiveKernel(self, other)

    def __mul__(self, other):
        return ProductKernel(self, other)


class AdditiveKernel(Kernel):
    def __init__(self, *kernels):
        super(AdditiveKernel, self).__init__()
        self.kernels = ModuleList(kernels)

    def forward(self, x1, x2):
        res = ZeroLazyVariable()
        for kern in self.kernels:
            res = res + kern(x1, x2).evaluate_kernel()

        return res


class ProductKernel(Kernel):
    def __init__(self, *kernels):
        super(ProductKernel, self).__init__()
        self.kernels = ModuleList(kernels)

    def forward(self, x1, x2):
        return prod([k(x1, x2).evaluate_kernel() for k in self.kernels])
