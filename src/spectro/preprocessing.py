"""Clean a raw spectrum before peak analysis: baseline, smoothing, normalisation.

Each function takes a `Spectrum` and returns a new one, and records what it
did in ``metadata["preprocessing"]`` so a processed spectrum carries its own
history. The usual order is baseline → smooth → normalise.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from pybaselines import Baseline
from scipy.signal import savgol_filter

from spectro.spectrum import Spectrum

NormMethod = Literal["max", "area", "vector", "snv"]

# Defaults tuned on the 1801-point synthetic grid (400–4000 cm⁻¹, 2 cm⁻¹ step).
# `lam` is a smoothness penalty whose effect depends on the number of points.
BASELINE_DEFAULTS: dict[str, dict] = {
    "arpls": {"lam": 1e7},
    "asls": {"lam": 1e7, "p": 0.01},
}


def estimate_baseline(spectrum: Spectrum, method: str = "arpls", **kwargs) -> Spectrum:
    """Estimate the smooth background under the peaks.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum to estimate the baseline of, usually in absorbance.
    method : str, default "arpls"
        Name of a `pybaselines.Baseline` method, e.g. "arpls", "asls" or
        "modpoly".
    **kwargs
        Passed to the method, overriding the defaults in
        ``BASELINE_DEFAULTS``, e.g. ``lam=1e6``.

    Returns
    -------
    Spectrum
        The baseline, on the same `x` as `spectrum`.

    Raises
    ------
    ValueError
        If `method` is not a `pybaselines` baseline method.

    Notes
    -----
    The default, arPLS, fits a smooth curve z minimising
    Σ wᵢ (yᵢ − zᵢ)² + λ Σ (Δ²zᵢ)². The second term penalises curvature, so
    larger `lam` gives a stiffer baseline. The weights wᵢ are recomputed each
    iteration so points well above the curve (peaks) get almost no weight,
    while points within the noise of it keep full weight. That makes the
    curve follow the bottom of the spectrum without being dragged up by the
    peaks or down by the noise.

    The older AsLS method uses a fixed small weight `p` above the curve
    instead, which biases it below the true baseline when there is noise and
    lets it ride up under very broad bands such as O–H.

    References
    ----------
    .. [1] S.-J. Baek et al., "Baseline correction using asymmetrically
       reweighted penalized least squares smoothing," Analyst 140,
       250–257 (2015).
    .. [2] pybaselines documentation, https://pybaselines.readthedocs.io
    """
    fitter = Baseline(x_data=spectrum.x)
    fit = getattr(fitter, method, None)
    if method.startswith("_") or not callable(fit):
        raise ValueError(f"unknown baseline method {method!r}")

    options = {**BASELINE_DEFAULTS.get(method, {}), **kwargs}
    baseline, _ = fit(spectrum.y, **options)
    return _record(spectrum, baseline, f"estimate_baseline({method})")


def remove_baseline(spectrum: Spectrum, method: str = "arpls", **kwargs) -> Spectrum:
    """Subtract the estimated baseline, leaving only the peaks.

    Baseline drift (scattering, sample thickness, instrument drift) adds to
    peak heights and areas, so it must go before peaks are measured.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum to correct, usually in absorbance.
    method : str, default "arpls"
        Baseline method; see `estimate_baseline`.
    **kwargs
        Passed to the method, e.g. ``lam=1e6``.

    Returns
    -------
    Spectrum
        `spectrum` minus its baseline.

    Raises
    ------
    ValueError
        If `method` is not a `pybaselines` baseline method.
    """
    baseline = estimate_baseline(spectrum, method, **kwargs)
    return _record(spectrum, spectrum.y - baseline.y, f"remove_baseline({method})")


def smooth(spectrum: Spectrum, window: int = 11, polyorder: int = 3) -> Spectrum:
    """Reduce noise with a Savitzky–Golay filter.

    Unlike a moving average, Savitzky–Golay fits a polynomial in each
    window, so it keeps peak heights and widths much better for the same
    amount of noise removed.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum to smooth. Points should be evenly spaced in `x`.
    window : int, default 11
        Window length in points (odd). Keep it below the narrowest peak's
        FWHM divided by the point spacing; 11 points is 20 cm⁻¹ at 2 cm⁻¹
        spacing.
    polyorder : int, default 3
        Degree of the polynomial fitted in each window. Must be less than
        `window`.

    Returns
    -------
    Spectrum
        The smoothed spectrum.

    Raises
    ------
    ValueError
        If `window` is even, not greater than `polyorder`, or longer than
        the spectrum.

    Notes
    -----
    There is a trade-off. A wider window removes more noise but, once it
    reaches about the FWHM of a peak, starts to flatten it: height drops and
    width grows. A higher `polyorder` keeps peaks sharper but removes less
    noise.

    References
    ----------
    .. [1] A. Savitzky and M. J. E. Golay, "Smoothing and differentiation of
       data by simplified least squares procedures," Anal. Chem. 36,
       1627–1639 (1964).
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    if window <= polyorder:
        raise ValueError("window must be greater than polyorder")
    if window > len(spectrum):
        raise ValueError("window is longer than the spectrum")

    y = savgol_filter(spectrum.y, window, polyorder)
    return _record(spectrum, y, f"smooth({window}, {polyorder})")


def normalize(spectrum: Spectrum, method: NormMethod = "max") -> Spectrum:
    """Rescale a spectrum so different samples can be compared.

    Sample thickness and concentration scale the whole spectrum. Normalising
    removes that overall scale so that spectra differ only in shape.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum to rescale, normally baseline-corrected first.
    method : {"max", "area", "vector", "snv"}, default "max"
        "max" divides by the largest value (tallest peak = 1), good for
        plotting. "area" divides by the integral over `x`. "vector" divides
        by the Euclidean norm. "snv" (standard normal variate) subtracts the
        mean and divides by the standard deviation, common before
        classification.

    Returns
    -------
    Spectrum
        The normalised spectrum. `y_unit` notes the method, e.g.
        "absorbance (max-normalized)".

    Raises
    ------
    ValueError
        If `method` is unknown, or the scale it divides by is not positive
        (e.g. an all-zero spectrum).
    """
    y = spectrum.y
    if method == "max":
        scale = y.max()
    elif method == "area":
        scale = np.trapezoid(y, spectrum.x)
    elif method == "vector":
        scale = np.linalg.norm(y)
    elif method == "snv":
        scale = y.std()
        y = y - y.mean()
    else:
        raise ValueError(f"unknown normalization method {method!r}")

    if scale <= 0:
        raise ValueError(f"cannot normalize by {method}: scale is {scale}")

    unit = f"{spectrum.y_unit} ({method}-normalized)"
    return _record(spectrum, y / scale, f"normalize({method})", y_unit=unit)


def _record(
    spectrum: Spectrum, y: np.ndarray, step: str, y_unit: str | None = None
) -> Spectrum:
    """Return `spectrum` with new `y`, adding `step` to its processing history."""
    result = spectrum.with_y(y, y_unit=y_unit)
    # A new list, so the input's history isn't changed through the shared copy.
    history = [*spectrum.metadata.get("preprocessing", []), step]
    result.metadata["preprocessing"] = history
    return result
