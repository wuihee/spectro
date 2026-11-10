"""Plot helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from spectro.spectrum import Spectrum


def plot_spectrum(spectrum: Spectrum, ax: Axes | None = None, **line_kwargs) -> Axes:
    """Draw a spectrum as a line.

    IR convention is to plot wavenumber decreasing left to right, so the
    x-axis is inverted when `x` is in cm⁻¹.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum to draw.
    ax : Axes, optional
        Axes to draw on. If None, a new figure is created.
    **line_kwargs
        Passed to `matplotlib.axes.Axes.plot`, e.g. ``color`` or ``label``.

    Returns
    -------
    Axes
        The axes drawn on, so callers can add more on top.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))

    ax.plot(spectrum.x, spectrum.y, **line_kwargs)
    ax.set_xlabel(
        f"Wavenumber ({spectrum.x_unit})"
        if spectrum.x_unit == "cm⁻¹"
        else spectrum.x_unit
    )
    ax.set_ylabel(spectrum.y_unit.capitalize())

    if spectrum.x_unit == "cm⁻¹" and not ax.xaxis_inverted():
        ax.invert_xaxis()
    return ax
