#!/usr/bin/env python3

import math
import unittest
import torch
import gpytorch


def dist_func(x1, x2):
    dist_module = gpytorch.kernels.kernel.Distance()
    return dist_module._jit_dist(x1, x2, torch.tensor(torch.equal(x1, x2)))


class TestMaternCovariance(unittest.TestCase):
    def test_forward(self):
        for nu in [1 / 2, 3 / 2, 5 / 2]:
            batch_size = (3, 2, 4)
            x1 = torch.randn(*batch_size, 7, 9)
            x2 = torch.randn(*batch_size, 6, 9)
            # Doesn't support ARD
            lengthscale = torch.randn(*batch_size).view(*batch_size, 1, 1) ** 2

            res = gpytorch.functions.MaternCovariance().apply(x1, x2, lengthscale, nu, dist_func)
            scaled_unitless_dist = math.sqrt(nu * 2) * dist_func(x1, x2).div(lengthscale)
            exp_component = torch.exp(-scaled_unitless_dist)
            if nu == 1 / 2:
                actual = exp_component
            elif nu == 3 / 2:
                actual = exp_component * (1 + scaled_unitless_dist)
            elif nu == 5 / 2:
                actual = exp_component * (1 + scaled_unitless_dist + scaled_unitless_dist ** 2 / 3)
            self.assertTrue(torch.allclose(res, actual))

    def test_backward(self):
        for nu in [1 / 2, 3 / 2, 5 / 2]:
            batch_size = (3, 2, 4)
            x1 = torch.randn(*batch_size, 7, 9, dtype=torch.float64)
            x2 = torch.randn(*batch_size, 6, 9, dtype=torch.float64)
            lengthscale = torch.randn(
                *batch_size, dtype=torch.float64, requires_grad=True).view(*batch_size, 1, 1) ** 2
            f = lambda x1, x2, l: gpytorch.functions.MaternCovariance().apply(x1, x2, l, nu, dist_func)
            try:
                torch.autograd.gradcheck(f, (x1, x2, lengthscale))
            except RuntimeError:
                self.fail(f"Gradcheck failed for Matern {nu}")


if __name__ == "__main__":
    unittest.main()
