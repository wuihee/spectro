"""Build synthetic spectra from a list of peaks, with a known true answer.

Every generated spectrum comes with a table of the peaks used to make it,
so the analysis functions (peak detection, fitting, deconvolution) can be
checked against the truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from spectro import lineshapes
from spectro.spectrum import Spectrum

Shape = Literal["gaussian", "lorentzian", "pseudo_voigt"]

# About the point spacing of a typical FTIR export.
DEFAULT_X = np.arange(400.0, 4000.0 + 2.0, 2.0)


@dataclass
class Peak:
    """One peak to put into a synthetic spectrum.

    Parameters
    ----------
    center : float
        Peak position (cm⁻¹).
    fwhm : float
        Full width at half maximum (cm⁻¹). Must be positive.
    height : float
        Peak value at `center` (absorbance).
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape; see `spectro.lineshapes`.
    eta : float, default 0.5
        Lorentzian fraction, used only by "pseudo_voigt". Between 0 and 1.

    Raises
    ------
    ValueError
        If `shape` is unknown, `fwhm` is not positive or `eta` is outside
        [0, 1].
    """

    center: float
    fwhm: float
    height: float
    shape: Shape = "pseudo_voigt"
    eta: float = 0.5

    def __post_init__(self) -> None:
        if self.shape not in ("gaussian", "lorentzian", "pseudo_voigt"):
            raise ValueError(f"unknown shape {self.shape!r}")
        if self.fwhm <= 0:
            raise ValueError("fwhm must be positive")
        if not 0 <= self.eta <= 1:
            raise ValueError("eta must be between 0 and 1")

    @property
    def area(self) -> float:
        """Integrated area of the peak over all x (absorbance · cm⁻¹)."""
        gaussian_area = lineshapes.GAUSSIAN_AREA_FACTOR * self.height * self.fwhm
        lorentzian_area = lineshapes.LORENTZIAN_AREA_FACTOR * self.height * self.fwhm
        if self.shape == "gaussian":
            return gaussian_area
        if self.shape == "lorentzian":
            return lorentzian_area
        return self.eta * lorentzian_area + (1 - self.eta) * gaussian_area

    def evaluate(self, x: np.ndarray) -> np.ndarray:
        """Return the peak's values at each `x`.

        Parameters
        ----------
        x : np.ndarray
            Wavenumbers (cm⁻¹).

        Returns
        -------
        np.ndarray
            Peak values, same shape as `x`.
        """
        if self.shape == "gaussian":
            return lineshapes.gaussian(x, self.center, self.fwhm, self.height)
        if self.shape == "lorentzian":
            return lineshapes.lorentzian(x, self.center, self.fwhm, self.height)
        return lineshapes.pseudo_voigt(x, self.center, self.fwhm, self.height, self.eta)


def make_spectrum(
    peaks: list[Peak],
    x: np.ndarray | None = None,
    noise: float = 0.0,
    baseline: tuple[float, ...] | None = None,
    seed: int | None = None,
) -> tuple[Spectrum, pd.DataFrame]:
    """Build an absorbance spectrum from peaks, plus optional baseline and noise.

    Parameters
    ----------
    peaks : list of Peak
        Peaks to add together.
    x : np.ndarray, optional
        Wavenumbers (cm⁻¹). Defaults to 400–4000 cm⁻¹ every 2 cm⁻¹.
    noise : float, default 0.0
        Standard deviation of Gaussian noise added to every point
        (absorbance).
    baseline : tuple of float, optional
        Polynomial coefficients ``(offset, slope, curvature, ...)`` for a
        smooth background; see Notes.
    seed : int, optional
        Seed for the noise, so a spectrum can be reproduced exactly.

    Returns
    -------
    spectrum : Spectrum
        The synthetic spectrum, in absorbance.
    true_peaks : pd.DataFrame
        One row per peak, with columns ``shape, center, fwhm, height, area``.

    Notes
    -----
    The baseline is evaluated on x rescaled to t ∈ [0, 1] across the
    spectrum, b(t) = c₀ + c₁·t + c₂·t² + ..., so each coefficient is
    the size of that term in absorbance units, whatever the x range.
    """
    x = DEFAULT_X.copy() if x is None else np.asarray(x, dtype=float)

    y = np.zeros_like(x)
    for peak in peaks:
        y += peak.evaluate(x)

    if baseline is not None:
        t = (x - x.min()) / (x.max() - x.min())
        y += np.polynomial.polynomial.polyval(t, baseline)

    if noise > 0:
        y += np.random.default_rng(seed).normal(0.0, noise, x.size)

    spectrum = Spectrum(
        x=x, y=y, metadata={"synthetic": True, "noise": noise, "seed": seed}
    )
    return spectrum, peak_table(peaks)


def peak_table(peaks: list[Peak]) -> pd.DataFrame:
    """Summarise peaks as a table, one row per peak.

    Parameters
    ----------
    peaks : list of Peak
        Peaks to summarise.

    Returns
    -------
    pd.DataFrame
        Columns ``shape, center, fwhm, height, area``, sorted by center.
    """
    rows = [
        {
            "shape": p.shape,
            "center": p.center,
            "fwhm": p.fwhm,
            "height": p.height,
            "area": p.area,
        }
        for p in peaks
    ]
    columns = ["shape", "center", "fwhm", "height", "area"]
    table = pd.DataFrame(rows, columns=columns)
    return table.sort_values("center", ignore_index=True)
