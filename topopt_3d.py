#!/usr/bin/env python3

import os

import autograd.numpy as np
import matplotlib.pyplot as plt
import nlopt
import pyvista as pv
from autograd import tensor_jacobian_product, value_and_grad
from tofem import FEM3D_K, FEM3D_T

from common.topopt.filters import gaussian_filter

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["KMP_WARNINGS"] = "0"


def create_parametrization(shape, sigma, e_min=1e-4, e_max=1.0, p=3.0):
    def parametrization(x):
        x = np.reshape(x, shape)
        x = gaussian_filter(x, sigma)
        x = e_min + x ** p * (e_max - e_min)
        return x

    return parametrization


def create_grid(x, spacing=1.0):
    grid = pv.UniformGrid()
    grid.dimensions = np.array(x.shape) + 1
    grid_shape = np.array(x.shape)
    grid_dims = grid_shape * spacing
    grid.spacing = [spacing] * x.ndim
    grid.origin = [-grid_dims[1] / 2, -grid_dims[2] / 2, 0]
    grid.cell_arrays["values"] = x.flatten(order="F")
    return grid


def run_mech():
    max_its = 100
    volfrac = 0.4
    sigma = 1.0
    shape = (80, 40, 20)
    nx, ny, nz = shape

    dofs = np.arange(3 * (nx + 1) * (ny + 1) * (nz + 1)).reshape(
        nz + 1, nx + 1, ny + 1, 3
    )
    fixed = np.zeros_like(dofs, dtype=bool)
    load = np.zeros_like(dofs)

    fixed[:, 0, :, :] = 1
    load[:, -1, -1, 1] = 1

    x0 = np.full(shape, volfrac)
    fem = FEM3D_K(shape, dofs, fixed, load, z_chunks=10, solver="gpu")
    parametrization = create_parametrization(shape, sigma)

    fig, ax = plt.subplots(2, 1)
    im0 = ax[0].imshow(x0[..., x0.shape[-1] // 2].T, cmap="gray_r", vmin=0, vmax=1)
    im1 = ax[1].imshow(
        parametrization(x0)[..., x0.shape[-1] // 2].T, cmap="gray_r", vmin=0, vmax=1
    )
    ax[0].axis("off")
    ax[1].axis("off")
    fig.tight_layout()
    fig.show()

    def volume_constraint(x, gd):
        v, g = value_and_grad(np.mean)(x)
        if gd.size > 0:
            gd[:] = g
        return v - volfrac

    def nlopt_obj(x, gd):
        design = parametrization(x)
        c, dc = value_and_grad(fem)(design)

        if gd.size > 0:
            gd[:] = tensor_jacobian_product(parametrization)(x, dc).ravel()

        im0.set_array(np.reshape(x, design.shape)[..., design.shape[-1] // 2].T)
        im1.set_array(design[..., design.shape[-1] // 2].T)
        fig.canvas.draw()

        return c

    opt = nlopt.opt(nlopt.LD_MMA, x0.size)
    opt.add_inequality_constraint(volume_constraint)
    opt.set_min_objective(nlopt_obj)
    opt.set_lower_bounds(0)
    opt.set_upper_bounds(1)
    opt.set_maxeval(max_its)
    design = opt.optimize(x0.ravel())

    plt.show(block=True)

    grid = create_grid(np.reshape(design, shape))
    p = pv.Plotter()
    p.add_volume(
        grid, opacity="linear", cmap="gray_r", show_scalar_bar=False, scalars="values",
    )
    p.set_background("w")
    p.show()


def run_temp():
    max_its = 100
    volfrac = 0.4
    sigma = 1.0
    shape = (80, 80, 80)
    nx, ny, nz = shape

    dofs = np.arange((nx + 1) * (ny + 1) * (nz + 1)).reshape(nz + 1, nx + 1, ny + 1)
    fixed = np.zeros_like(dofs, dtype=bool)
    load = np.zeros_like(dofs)

    fixed[35:-35, 35:-35, 0] = 1
    load[..., 5:] = 1

    x0 = np.full(shape, volfrac)
    fem = FEM3D_T(shape, dofs, fixed, load, z_chunks=10, solver="gpu")
    parametrization = create_parametrization(shape, sigma)

    fig, ax = plt.subplots(2, 1)
    im0 = ax[0].imshow(x0[..., x0.shape[-1] // 2].T, cmap="gray_r", vmin=0, vmax=1)
    im1 = ax[1].imshow(
        parametrization(x0)[..., x0.shape[-1] // 2].T, cmap="gray_r", vmin=0, vmax=1
    )
    ax[0].axis("off")
    ax[1].axis("off")
    fig.tight_layout()
    fig.show()

    def volume_constraint(x, gd):
        v, g = value_and_grad(np.mean)(x)
        if gd.size > 0:
            gd[:] = g
        return v - volfrac

    def nlopt_obj(x, gd):
        design = parametrization(x)
        c, dc = value_and_grad(fem)(design)

        if gd.size > 0:
            gd[:] = tensor_jacobian_product(parametrization)(x, dc).ravel()

        im0.set_array(np.reshape(x, design.shape)[..., design.shape[-1] // 2].T)
        im1.set_array(design[..., design.shape[-1] // 2].T)
        fig.canvas.draw()

        return c

    opt = nlopt.opt(nlopt.LD_MMA, x0.size)
    opt.add_inequality_constraint(volume_constraint)
    opt.set_min_objective(nlopt_obj)
    opt.set_lower_bounds(0)
    opt.set_upper_bounds(1)
    opt.set_maxeval(max_its)
    design = opt.optimize(x0.ravel())

    plt.show(block=True)

    grid = create_grid(np.reshape(design, shape))
    p = pv.Plotter()
    # grid = grid.threshold_percent(volfrac)
    # p.add_mesh(
    #     grid, cmap="gray_r", show_scalar_bar=False, scalars="values",
    # )
    p.add_volume(
        grid, opacity="linear", cmap="gray_r", show_scalar_bar=False, scalars="values",
    )
    p.set_background("w")
    p.show()


if __name__ == "__main__":
    run_mech()
    # run_temp()
