"""Fit line shapes to detected peaks to measure them with uncertainties.

Detection (`spectro.peaks`) reads center, FWHM and height straight off the data
points. Fitting adjusts a smooth line shape until it matches the data as
closely as possible (least squares), which uses every point across the
peak, gives the area and line shape too, and estimates how uncertain each
value is. Each peak is fitted on its own, in a window around it, on top of
a straight-line background. Fitting several overlapping peaks together is
handled by `spectro.deconvolution`.
"""

from __future__ import annotations

import lmfit
import numpy as np
import pandas as pd

from spectro import lineshapes
from spectro.spectrum import Spectrum
from spectro.synthetic import Shape

FIT_PARAMS = ["center", "fwhm", "height", "area", "eta"]
FIT_COLUMNS = [
    "shape",
    *[name for param in FIT_PARAMS for name in (param, f"{param}_err")],
    "rms_residual",
]

_FUNCTIONS = {
    "gaussian": lineshapes.gaussian,
    "lorentzian": lineshapes.lorentzian,
    "pseudo_voigt": lineshapes.pseudo_voigt,
}
_GA = lineshapes.GAUSSIAN_AREA_FACTOR
_LA = lineshapes.LORENTZIAN_AREA_FACTOR


def peak_model(shape: Shape = "pseudo_voigt", prefix: str = "") -> lmfit.Model:
    """Build an lmfit model of one peak, parameterised like `spectro.synthetic.Peak`.

    Parameters
    ----------
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape; see `spectro.lineshapes`.
    prefix : str, default ""
        Prefix for the parameter names, e.g. ``"p1_"``, so several peaks can
        be added into one model (see `spectro.deconvolution`).

    Returns
    -------
    lmfit.Model
        Model with parameters ``center``, ``fwhm``, ``height`` and, for
        "pseudo_voigt", ``eta``, each with `prefix`. Call `peak_params` for
        starting values and bounds.

    Raises
    ------
    ValueError
        If `shape` is unknown.
    """
    if shape not in _FUNCTIONS:
        raise ValueError(f"unknown shape {shape!r}")
    return lmfit.Model(_FUNCTIONS[shape], prefix=prefix)


def peak_params(
    model: lmfit.Model,
    center: float,
    fwhm: float,
    height: float,
    x_range: tuple[float, float],
) -> lmfit.Parameters:
    """Give starting values, bounds and a derived ``area`` for a `peak_model`.

    Parameters
    ----------
    model : lmfit.Model
        A model from `peak_model`.
    center, fwhm, height : float
        Starting values, e.g. from `spectro.peaks.detect_peaks` (cm⁻¹,
        cm⁻¹, absorbance).
    x_range : tuple of float
        (low, high) wavenumbers of the fit window (cm⁻¹); the center is kept
        inside it.

    Returns
    -------
    lmfit.Parameters
        Parameters ready for ``model.fit``, including ``area`` computed from
        the others, so lmfit also reports its uncertainty.
    """
    p = model.prefix
    low, high = x_range
    params = model.make_params()
    params[f"{p}center"].set(value=center, min=low, max=high)
    params[f"{p}fwhm"].set(value=fwhm, min=1e-3 * fwhm, max=10 * (high - low))
    params[f"{p}height"].set(value=height, min=0)
    if f"{p}eta" in params:
        params[f"{p}eta"].set(value=0.5, min=0, max=1)
        factor = f"({p}eta * {_LA} + (1 - {p}eta) * {_GA})"
    else:
        factor = str(_LA if model.func is lineshapes.lorentzian else _GA)
    params.add(f"{p}area", expr=f"{factor} * {p}height * {p}fwhm")
    return params


def fit_peak(
    spectrum: Spectrum,
    center: float,
    fwhm: float,
    height: float,
    shape: Shape = "pseudo_voigt",
    window: float = 2.0,
    x_range: tuple[float, float] | None = None,
) -> lmfit.model.ModelResult:
    """Fit one line shape plus a straight-line background to one peak.

    Parameters
    ----------
    spectrum : Spectrum
        Baseline-corrected spectrum, **not smoothed** (see Notes).
    center, fwhm, height : float
        Starting values (cm⁻¹, cm⁻¹, absorbance), e.g. a row of
        `spectro.peaks.detect_peaks`.
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape to fit.
    window : float, default 2.0
        Half-width of the fit window in multiples of the starting `fwhm`,
        used when `x_range` is not given.
    x_range : tuple of float, optional
        (low, high) wavenumbers (cm⁻¹) of the fit window, overriding
        `window`.

    Returns
    -------
    lmfit.model.ModelResult
        The fit. ``result.params[name].value`` and ``.stderr`` give each
        parameter and its standard error; the background parameters are
        ``bkg_intercept`` and ``bkg_slope``. ``result.best_fit`` is the
        fitted curve on ``result.userkws["x"]``.

    Raises
    ------
    ValueError
        If the window holds fewer points than there are parameters.

    Notes
    -----
    The fit minimises Σ (yᵢ − f(xᵢ))² with the Levenberg–Marquardt
    algorithm. The background term a + b·(x − center) soaks up any baseline
    left over after baseline removal and the tails of nearby peaks.

    Standard errors come from the covariance matrix of the fit, scaled by
    the reduced chi-square, i.e. by the noise level the residuals show.
    That assumes the noise is independent from point to point. Smoothing
    breaks this: neighbouring points then share noise, so the errors come
    out far too small, and the smoothing also widens the peak. Detect peaks
    on the smoothed spectrum, but fit the unsmoothed one.

    References
    ----------
    .. [1] M. Newville et al., "LMFIT: Non-Linear Least-Squares Minimization
       and Curve-Fitting for Python," Zenodo (2014–2025),
       https://lmfit.github.io/lmfit-py/
    .. [2] W. F. Maddams, "The scope and limitations of curve fitting,"
       Appl. Spectrosc. 34, 245–267 (1980).
    """
    if x_range is None:
        x_range = (center - window * fwhm, center + window * fwhm)
    inside = (spectrum.x >= x_range[0]) & (spectrum.x <= x_range[1])
    x, y = spectrum.x[inside], spectrum.y[inside]

    # Background as a straight line around the peak center, so its slope and
    # intercept aren't strongly correlated.
    def line(x: np.ndarray, intercept: float, slope: float) -> np.ndarray:
        return intercept + slope * (x - center)

    peak = peak_model(shape)
    background = lmfit.Model(line, prefix="bkg_")
    model = peak + background
    params = peak_params(peak, center, fwhm, height, x_range)
    params.update(background.make_params(intercept=0.0, slope=0.0))

    if len(x) <= len(params) - 1:  # area is derived, not fitted
        raise ValueError(f"only {len(x)} points in the fit window {x_range}")
    return model.fit(y, params, x=x)


def fit_peaks(
    spectrum: Spectrum,
    peaks: pd.DataFrame,
    shape: Shape = "pseudo_voigt",
    window: float = 2.0,
) -> pd.DataFrame:
    """Fit every peak in a peak table, one at a time.

    Each window spans ±`window` × FWHM around the peak but stops halfway to
    the neighbouring peaks, so a fit doesn't try to describe another peak.

    Parameters
    ----------
    spectrum : Spectrum
        Baseline-corrected spectrum, not smoothed; see `fit_peak`.
    peaks : pd.DataFrame
        Starting values with ``center``, ``fwhm`` and ``height`` columns,
        e.g. from `spectro.peaks.detect_peaks` run on the smoothed spectrum.
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape fitted to every peak.
    window : float, default 2.0
        Window half-width in multiples of each peak's starting FWHM.

    Returns
    -------
    pd.DataFrame
        One row per peak, sorted by center, with columns ``shape``, then
        ``center``, ``fwhm``, ``height``, ``area`` and ``eta``, each followed
        by its standard error (``center_err``, ...), then ``rms_residual``.
        ``eta`` is NaN unless `shape` is "pseudo_voigt". An error is NaN when
        lmfit can't estimate it, e.g. for a perfect fit to noise-free data,
        and is unreliable for a parameter stuck at a bound (``eta`` of 0
        or 1). The errors cover noise only, not a wrong model or window.
        Compare ``rms_residual`` with `spectro.peaks.estimate_noise`: much
        larger means the shape or window doesn't fit.

    Notes
    -----
    Peaks that overlap strongly are fitted poorly this way, because each fit
    sees the other peak only as background; their areas come out too small.
    `spectro.deconvolution.deconvolve` fits them together.

    Examples
    --------
    >>> corrected = remove_baseline(raw)
    >>> noise = estimate_noise(corrected)
    >>> found = detect_peaks(smooth(corrected), prominence=5 * noise)
    >>> fitted = fit_peaks(corrected, found)
    """
    starts = peaks.sort_values("center")
    centers = starts["center"].to_numpy()
    midpoints = (centers[:-1] + centers[1:]) / 2
    lows = np.r_[-np.inf, midpoints]
    highs = np.r_[midpoints, np.inf]

    rows = []
    for (center, fwhm, height), low, high in zip(
        starts[["center", "fwhm", "height"]].to_numpy(), lows, highs, strict=True
    ):
        x_range = (max(center - window * fwhm, low), min(center + window * fwhm, high))
        result = fit_peak(spectrum, center, fwhm, height, shape, x_range=x_range)
        rows.append(_fit_row(result, shape))
    return pd.DataFrame(rows, columns=FIT_COLUMNS)


def _fit_row(result: lmfit.model.ModelResult, shape: Shape, prefix: str = "") -> dict:
    """Turn one peak of a fit result into one row of the `fit_peaks` table."""
    row: dict = {"shape": shape}
    for name in FIT_PARAMS:
        param = result.params.get(f"{prefix}{name}")
        row[name] = np.nan if param is None else param.value
        stderr = None if param is None else param.stderr
        row[f"{name}_err"] = np.nan if stderr is None else stderr
    row["rms_residual"] = float(
        np.sqrt(np.mean(np.square(np.asarray(result.residual, dtype=float))))
    )
    return row
