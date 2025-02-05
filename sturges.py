#!/usr/bin/env python3

import autograd.numpy as np
import matplotlib.pyplot as plt
import nlopt
from autograd import value_and_grad

from tofea.fea2d import FEA2D_T
from tofea.topopt_helpers import simp_parametrization

max_its = 20
volfrac = 0.4
sigma = 0.5
shape = (100, 100)
nelx, nely = shape
cmin, cmax = 1.0, 1e6

fixed = np.zeros((nelx + 1, nely + 1), dtype="?")
load = np.zeros_like(fixed)

fixed[40:60, -1] = 1
load[:, :-10] = 1

fem = FEA2D_T(fixed)
parametrization = simp_parametrization(shape, sigma, cmin, cmax)
x0 = np.full(shape, volfrac)
u = fem.heat_distribution(x0, load)
umax = u.max()


def objective(x):
    x = parametrization(x)
    x = fem(x, load)
    return x


def volume(x):
    x = parametrization(x)
    x = (x - cmin) / (cmax - cmin)
    return np.mean(x)


plt.ion()
fig, ax = plt.subplots(1, 2)
im0 = ax[0].imshow(parametrization(x0).T, cmap="gray_r", vmin=cmin, vmax=cmax)
im1 = ax[1].imshow(parametrization(x0).T)
fig.tight_layout()


def volume_constraint(x, gd):
    v, g = value_and_grad(volume)(x)
    if gd.size > 0:
        gd[:] = g
    return v - volfrac


def nlopt_obj(x, gd):
    c, dc = value_and_grad(objective)(x)
    u = fem.heat_distribution(x, load)
    u = u.reshape(fixed.shape)

    if gd.size > 0:
        gd[:] = dc.ravel()

    im0.set_data(parametrization(x).T)
    im1.set_data(u.T)
    im1.set_clim([0, umax])
    plt.pause(0.1)

    return c


opt = nlopt.opt(nlopt.LD_MMA, x0.size)
opt.add_inequality_constraint(volume_constraint, 1e-6)
opt.set_min_objective(nlopt_obj)
opt.set_lower_bounds(0)
opt.set_upper_bounds(1)
opt.set_maxeval(max_its)
opt.optimize(x0.ravel())

plt.show(block=True)
