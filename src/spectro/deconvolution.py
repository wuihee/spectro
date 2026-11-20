"""Separate overlapping peaks by fitting them together, and choose how many there are.

Step 5 fits each peak on its own, so a peak that overlaps another sees it
only as background and loses area. Here the peaks whose fit windows overlap
are grouped into a region, and all peaks in a region are fitted at once, as
a sum of line shapes on a shared straight-line background. How many peaks a
region holds is not taken on trust from detection: models with different
numbers of peaks are fitted and compared with an information criterion (BIC
by default), which rewards a better fit but charges for every extra
parameter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import lmfit
import numpy as np
import pandas as pd

from spectro.fitting import FIT_COLUMNS, _fit_row, peak_model, peak_params
from spectro.preprocessing import smooth
from spectro.spectrum import Spectrum
from spectro.synthetic import Shape

Criterion = Literal["bic", "aic"]
COMPARE_COLUMNS = ["n_peaks", "chisqr", "aic", "bic", "delta_aic", "delta_bic"]


@dataclass
class Region:
    """A stretch of the spectrum whose peaks overlap and are fitted together.

    Parameters
    ----------
    x_range : tuple of float
        (low, high) wavenumbers of the region (cm⁻¹).
    peaks : pd.DataFrame
        The detected peaks inside it, with at least ``center``, ``fwhm``
        and ``height`` columns, sorted by center.
    """

    x_range: tuple[float, float]
    peaks: pd.DataFrame


def find_regions(peaks: pd.DataFrame, window: float = 2.0) -> list[Region]:
    """Group detected peaks into regions of overlapping peaks.

    Each peak covers ±`window` × FWHM around its center, the same span
    `spectro.fitting.fit_peak` fits by default. Peaks whose spans overlap,
    directly or through a chain of neighbours, form one region; a peak that
    overlaps nothing is a region on its own.

    Parameters
    ----------
    peaks : pd.DataFrame
        Detected peaks with ``center``, ``fwhm`` and ``height`` columns
        (cm⁻¹, cm⁻¹, absorbance), e.g. from `spectro.peaks.detect_peaks`.
        ``fwhm`` must not be NaN; fill it first for the output of
        `spectro.peaks.detect_peaks_derivative`.
    window : float, default 2.0
        Half-width of each peak's span in multiples of its FWHM.

    Returns
    -------
    list of Region
        Regions in order of wavenumber.

    Raises
    ------
    ValueError
        If any ``fwhm`` is NaN or not positive.
    """
    fwhm = peaks["fwhm"].to_numpy(dtype=float)
    if not np.all(fwhm > 0):  # also catches NaN
        raise ValueError("every peak needs a positive fwhm; fill NaN widths first")

    table = peaks.sort_values("center", ignore_index=True)
    low = (table["center"] - window * table["fwhm"]).to_numpy()
    high = (table["center"] + window * table["fwhm"]).to_numpy()

    regions: list[Region] = []
    start = 0
    reach = high[0]
    for i in range(1, len(table) + 1):
        if i == len(table) or low[i] > reach:
            members = table.iloc[start:i].reset_index(drop=True)
            x_range = (float(low[start:i].min()), float(reach))
            regions.append(Region(x_range, members))
            start = i
        if i < len(table):
            reach = max(reach, high[i])
    return regions


def fit_region(
    spectrum: Spectrum,
    peaks: pd.DataFrame,
    x_range: tuple[float, float],
    shape: Shape = "pseudo_voigt",
) -> lmfit.model.ModelResult:
    """Fit several peaks at once, as a sum of line shapes plus a straight line.

    Parameters
    ----------
    spectrum : Spectrum
        Baseline-corrected spectrum, **not smoothed** (see
        `spectro.fitting.fit_peak`).
    peaks : pd.DataFrame
        Starting values, one row per peak, with ``center``, ``fwhm`` and
        ``height`` columns (cm⁻¹, cm⁻¹, absorbance).
    x_range : tuple of float
        (low, high) wavenumbers (cm⁻¹) of the region to fit. Every center is
        kept inside it.
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape of every peak.

    Returns
    -------
    lmfit.model.ModelResult
        The fit. Peak ``i`` (in the order of `peaks`) has parameters
        prefixed ``p{i}_``, e.g. ``p0_center``; the background is
        ``bkg_intercept`` and ``bkg_slope``. Use `fit_table` to turn it
        into a peak table.

    Raises
    ------
    ValueError
        If `peaks` is empty, or the region holds fewer points than there
        are parameters.

    Notes
    -----
    The model is f(x) = Σₖ Pₖ(x) + a + b·(x − x̄), where each Pₖ is a line
    shape with its own center, FWHM, height (and η) and x̄ is the middle of
    the region. Fitting all peaks together lets each one take its share of
    the overlap, instead of treating its neighbour as background.

    Overlapping peaks trade off against each other: making one wider and the
    other narrower changes the sum only slightly. Their parameters are then
    strongly correlated, and the standard errors grow to show it. When the
    overlap is so strong that the data can't tell the peaks apart, the
    errors become very large or can't be computed (NaN), and the split
    between the peaks is not meaningful.

    References
    ----------
    .. [1] W. F. Maddams, "The scope and limitations of curve fitting,"
       Appl. Spectrosc. 34, 245–267 (1980).
    .. [2] B. G. M. Vandeginste and L. De Galan, "Critical evaluation of
       curve fitting in infrared spectrometry," Anal. Chem. 47, 2124–2132
       (1975).
    """
    if len(peaks) == 0:
        raise ValueError("need at least one peak to fit")
    low, high = x_range
    inside = (spectrum.x >= low) & (spectrum.x <= high)
    x, y = spectrum.x[inside], spectrum.y[inside]
    middle = (low + high) / 2

    def line(x: np.ndarray, intercept: float, slope: float) -> np.ndarray:
        return intercept + slope * (x - middle)

    model = lmfit.Model(line, prefix="bkg_")
    params = model.make_params(intercept=0.0, slope=0.0)
    for i, (center, fwhm, height) in enumerate(
        peaks[["center", "fwhm", "height"]].to_numpy(dtype=float)
    ):
        peak = peak_model(shape, prefix=f"p{i}_")
        params.update(peak_params(peak, center, fwhm, height, x_range))
        model = model + peak

    n_derived = len(peaks)  # one area per peak
    if len(x) <= len(params) - n_derived:
        raise ValueError(f"only {len(x)} points in the region {x_range}")
    return model.fit(y, params, x=x)


def fit_table(result: lmfit.model.ModelResult, shape: Shape) -> pd.DataFrame:
    """Turn a `fit_region` result into a peak table.

    Parameters
    ----------
    result : lmfit.model.ModelResult
        A fit from `fit_region`.
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}
        Line shape used in the fit.

    Returns
    -------
    pd.DataFrame
        One row per peak, sorted by center, with the columns of
        `spectro.fitting.fit_peaks`. ``rms_residual`` is that of the whole
        region, so it is the same for every peak in it.
    """
    n = sum(1 for name in result.params if name.endswith("_center"))
    rows = [_fit_row(result, shape, prefix=f"p{i}_") for i in range(n)]
    table = pd.DataFrame(rows, columns=FIT_COLUMNS)
    return table.sort_values("center", ignore_index=True)


def compare_peak_counts(
    spectrum: Spectrum,
    region: Region,
    shape: Shape = "pseudo_voigt",
    max_extra: int = 1,
) -> tuple[pd.DataFrame, list[lmfit.model.ModelResult]]:
    """Fit a region with 1, 2, ... peaks and score each fit with AIC and BIC.

    The model with n peaks starts from the n most prominent detected peaks.
    Beyond the detected ones, up to `max_extra` more peaks are added, one at
    a time, where the previous fit leaves the largest bump in its residual:
    that is where a hidden peak would be.

    Parameters
    ----------
    spectrum : Spectrum
        Baseline-corrected spectrum, not smoothed.
    region : Region
        Region to fit, from `find_regions`.
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape of every peak.
    max_extra : int, default 1
        How many peaks to try beyond the detected ones.

    Returns
    -------
    table : pd.DataFrame
        One row per model, with columns ``n_peaks``, ``chisqr`` (sum of
        squared residuals), ``aic``, ``bic`` and ``delta_aic``,
        ``delta_bic`` (difference from the lowest value; 0 marks the
        preferred model).
    results : list of lmfit.model.ModelResult
        The fits, in the same order as the rows.

    Notes
    -----
    For a least-squares fit with N points, k fitted parameters and residual
    sum of squares χ², lmfit computes

        AIC = N ln(χ²/N) + 2k,    BIC = N ln(χ²/N) + k ln N.

    Both reward a smaller χ² and charge for each parameter; BIC charges
    more (ln N ≈ 4–6 for a region of 50–400 points against 2 for AIC), so it
    adds a peak only when the evidence is stronger. Kass and Raftery's scale
    for a difference in BIC: below 2 not worth mentioning, 2–6 positive,
    6–10 strong, above 10 very strong.

    References
    ----------
    .. [1] H. Akaike, "A new look at the statistical model identification,"
       IEEE Trans. Autom. Control 19, 716–723 (1974).
    .. [2] G. Schwarz, "Estimating the dimension of a model," Ann. Stat. 6,
       461–464 (1978).
    .. [3] R. E. Kass and A. E. Raftery, "Bayes factors," J. Am. Stat.
       Assoc. 90, 773–795 (1995).
    .. [4] H. Shinotsuka et al., "Development of spectral decomposition based
       on Bayesian information criterion with estimation of confidence
       interval," Sci. Technol. Adv. Mater. 21, 402–419 (2020).
    """
    order = "prominence" if "prominence" in region.peaks else "height"
    ranked = _starts(region.peaks.sort_values(order, ascending=False))

    results = [
        fit_region(spectrum, ranked.iloc[:n], region.x_range, shape)
        for n in range(1, len(ranked) + 1)
    ]
    for _ in range(max_extra):
        results.append(_add_peak(spectrum, results[-1], region.x_range, shape))

    scores = {name: [_stat(r, name) for r in results] for name in ["aic", "bic"]}
    table = pd.DataFrame(
        {
            "n_peaks": np.arange(1, len(results) + 1),
            "chisqr": [_stat(r, "chisqr") for r in results],
            "aic": scores["aic"],
            "bic": scores["bic"],
            "delta_aic": np.subtract(scores["aic"], min(scores["aic"])),
            "delta_bic": np.subtract(scores["bic"], min(scores["bic"])),
        },
        columns=COMPARE_COLUMNS,
    )
    return table, results


def deconvolve(
    spectrum: Spectrum,
    peaks: pd.DataFrame,
    shape: Shape = "pseudo_voigt",
    window: float = 2.0,
    criterion: Criterion = "bic",
    max_extra: int = 1,
) -> pd.DataFrame:
    """Fit every region of overlapping peaks, choosing the number of peaks in each.

    Parameters
    ----------
    spectrum : Spectrum
        Baseline-corrected spectrum, **not smoothed**.
    peaks : pd.DataFrame
        Detected peaks, e.g. from `spectro.peaks.detect_peaks` on the
        smoothed spectrum, with ``center``, ``fwhm`` and ``height`` columns.
    shape : {"gaussian", "lorentzian", "pseudo_voigt"}, default "pseudo_voigt"
        Line shape of every peak.
    window : float, default 2.0
        Half-width of each peak's span in multiples of its FWHM; see
        `find_regions`.
    criterion : {"bic", "aic"}, default "bic"
        Information criterion used to choose the number of peaks.
    max_extra : int, default 1
        How many peaks to try beyond the detected ones in each region; 0
        only allows fewer.

    Returns
    -------
    pd.DataFrame
        One row per fitted peak, sorted by center, with the columns of
        `spectro.fitting.fit_peaks` plus ``region`` (index of the region the
        peak was fitted in). ``rms_residual`` is per region.

    Notes
    -----
    BIC is the default because it is the more cautious criterion: on
    synthetic spectra AIC sometimes adds a peak that isn't there, which
    then takes area from the real ones.

    A criterion only says the data need another component, not that it is
    a band. Anything the model can't describe, such as baseline left over
    from step 3 that isn't a straight line across the region, also gets
    absorbed by an extra component, which then takes area from the real
    bands [1]_. Check each added peak against the spectrum and against the
    bands the sample should have.

    The criterion can only choose between the models it is offered, and
    each fit starts from detection, the residual or a split peak. If two
    peaks are so close that no fit separates them, the region gets one wide
    peak, or two with unreliable areas. On synthetic pairs of equal bands,
    two peaks were found every time from about 0.6 FWHM apart at a
    signal-to-noise ratio of 50, and from about 0.4 FWHM at 250
    (notebook 06).

    References
    ----------
    .. [1] V. A. Lórenz-Fonfría and E. Padrós, "Curve-fitting overlapped
       bands: quantification and improvement of curve-fitting robustness in
       the presence of errors in the model and in the data," Analyst 129,
       1243–1250 (2004).

    Examples
    --------
    >>> corrected = remove_baseline(raw)
    >>> noise = estimate_noise(corrected)
    >>> found = detect_peaks(smooth(corrected), prominence=5 * noise)
    >>> table = deconvolve(corrected, found)
    """
    tables = []
    for i, region in enumerate(find_regions(peaks, window)):
        scores, results = compare_peak_counts(spectrum, region, shape, max_extra)
        best = results[int(scores[criterion].to_numpy().argmin())]
        tables.append(fit_table(best, shape).assign(region=i))
    table = pd.concat(tables, ignore_index=True)
    return table.sort_values("center", ignore_index=True)


def _add_peak(
    spectrum: Spectrum,
    result: lmfit.model.ModelResult,
    x_range: tuple[float, float],
    shape: Shape,
) -> lmfit.model.ModelResult:
    """Refit with one more peak, trying several starts and keeping the best."""
    fitted = _starts(fit_table(result, shape))
    starts = [_starts(fitted, _residual_peak(result, fitted))]
    # Two peaks that merged into one wide one are better found by splitting it
    # than from the residual, which is then nearly flat.
    for k, (c, w, h) in enumerate(fitted.to_numpy()):
        halves = pd.DataFrame(
            {"center": [c - w / 4, c + w / 4], "fwhm": [w / 2] * 2, "height": [h] * 2}
        )
        starts.append(_starts(fitted.drop(index=k), halves))
    fits = [fit_region(spectrum, start, x_range, shape) for start in starts]
    return min(fits, key=lambda fit: _stat(fit, "chisqr"))


def _residual_peak(
    result: lmfit.model.ModelResult, fitted: pd.DataFrame
) -> pd.DataFrame:
    """Return starting values for a new peak at the largest residual bump."""
    fwhm = float(np.median(fitted["fwhm"].to_numpy()))
    x = np.asarray((result.userkws or {})["x"], dtype=float)
    data = np.asarray(result.data, dtype=float)
    leftover = data - np.asarray(result.best_fit, dtype=float)
    # Smooth so the new peak goes on a real bump, not on a noise spike.
    spacing = float(np.median(np.diff(x)))
    points = int(fwhm / spacing) // 2 * 2 + 1
    window = min(max(points, 5), len(x) // 2 * 2 - 1)
    bump = smooth(Spectrum(x, leftover), window=window, polyorder=2).y
    i = int(np.argmax(bump))
    # A start exactly on the height >= 0 bound can leave the fit stuck there.
    height = max(float(bump[i]), 0.01 * float(np.max(np.abs(data))))
    return pd.DataFrame({"center": [x[i]], "fwhm": [fwhm], "height": [height]})


def _starts(*tables: pd.DataFrame) -> pd.DataFrame:
    """Stack the center, FWHM and height columns of peak tables into one."""
    columns = ["center", "fwhm", "height"]
    values = np.vstack([t[columns].to_numpy(dtype=float) for t in tables])
    return pd.DataFrame(values, columns=columns)


def _stat(result: lmfit.model.ModelResult, name: str) -> float:
    """Return a fit statistic such as ``chisqr`` or ``bic``."""
    # lmfit sets these at run time, so type checkers can't see them.
    return float(getattr(result, name))
