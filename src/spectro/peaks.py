"""Find peaks in a spectrum automatically and measure their center, FWHM and height.

Detection gives the starting point for peak fitting (step 5) and
deconvolution (step 6). There are two methods: `detect_peaks` finds local
maxima and copes with noise; `detect_peaks_derivative` finds minima of the
second derivative, which also reveals shoulders and closely overlapping
bands but needs low-noise data. Both return a peak table with the same
column names as the true peak table from `spectro.synthetic.make_spectrum`,
so results can be compared row by row with `match_peaks`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import signal

from spectro.spectrum import Spectrum

PEAK_COLUMNS = ["center", "fwhm", "height", "prominence"]


def estimate_noise(spectrum: Spectrum) -> float:
    """Estimate the standard deviation of the noise in a spectrum.

    Peaks and baselines are smooth, so they barely change from one point to
    the next, while white noise changes at every point. The second
    difference of `y` therefore holds almost only noise, and a median-based
    spread ignores the few points where peaks do contribute.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum to measure, before smoothing.

    Returns
    -------
    float
        Estimated noise standard deviation (same unit as `y`).

    Notes
    -----
    For independent noise of standard deviation σ, the second difference
    yᵢ₋₁ − 2yᵢ + yᵢ₊₁ has standard deviation √6·σ. The spread is measured
    with the median absolute deviation (MAD), which for normal data is
    σ/1.4826, so σ ≈ 1.4826 · MAD(Δ²y) / √6.

    Smoothing removes exactly the point-to-point changes this relies on, so
    on a smoothed spectrum the estimate is far too low. Estimate the noise
    first, then smooth.
    """
    d2 = np.diff(spectrum.y, n=2)
    mad = np.median(np.abs(d2 - np.median(d2)))
    return float(1.4826 * mad / np.sqrt(6))


def detect_peaks(
    spectrum: Spectrum,
    prominence: float | None = None,
    snr: float = 5.0,
) -> pd.DataFrame:
    """Find the peaks in a spectrum and measure each one.

    A peak is kept only if it stands out from its surroundings by at least
    `prominence`. By default that threshold is `snr` times the noise, so
    bumps made by noise alone are ignored without having to tune anything.

    Parameters
    ----------
    spectrum : Spectrum
        Baseline-corrected spectrum in absorbance, peaks pointing up.
    prominence : float, optional
        Minimum prominence (absorbance) for a peak to be kept. Defaults to
        ``snr * estimate_noise(spectrum)``. Pass it explicitly when
        `spectrum` has been smoothed; see Notes.
    snr : float, default 5.0
        Signal-to-noise ratio used for the default `prominence`.

    Returns
    -------
    pd.DataFrame
        One row per peak, sorted by center, with columns ``center`` (cm⁻¹),
        ``fwhm`` (cm⁻¹), ``height`` and ``prominence`` (absorbance).

    Notes
    -----
    The prominence of a peak is how far it rises above the higher of the
    two lowest points between it and any taller peak on either side. Unlike
    height, it doesn't depend on the baseline level, and a small noise
    wiggle on the shoulder of a big peak has a small prominence even though
    it is high up.

    The center and height come from a parabola through the highest point
    and its two neighbours, so they aren't limited to the point spacing.
    The FWHM is the width at half the *prominence* below the top
    (`scipy.signal.peak_widths`), with the crossing points interpolated
    between data points. For an isolated peak on a flat, corrected baseline
    this is the true FWHM. For overlapping peaks it is not: two equal peaks
    closer than about three-quarters of a FWHM merge into one wider peak,
    and a peak on the shoulder of another is measured from the shoulder.
    Separating them is the job of deconvolution (step 6).

    The default threshold uses `estimate_noise`, which doesn't work on
    smoothed data. To detect on a smoothed spectrum, estimate the noise
    before smoothing::

        noise = estimate_noise(corrected)
        detect_peaks(smooth(corrected), prominence=5 * noise)

    To find shoulders and closely overlapping peaks in low-noise spectra,
    use `detect_peaks_derivative` instead.

    References
    ----------
    .. [1] SciPy documentation, `scipy.signal.find_peaks` and
       `scipy.signal.peak_widths`,
       https://docs.scipy.org/doc/scipy/reference/signal.html
    """
    if prominence is None:
        prominence = snr * estimate_noise(spectrum)
    # A small floor so that flat, noise-free regions don't count as peaks.
    prominence = max(prominence, 1e-12)

    y = spectrum.y
    index, props = signal.find_peaks(y, prominence=prominence)
    widths = signal.peak_widths(y, index, rel_height=0.5)
    left, right = widths[2], widths[3]

    points = np.arange(len(spectrum))
    center, height = _refine_top(spectrum.x, y, index)
    table = pd.DataFrame(
        {
            "center": center,
            "fwhm": np.interp(right, points, spectrum.x)
            - np.interp(left, points, spectrum.x),
            "height": height,
            "prominence": props["prominences"],
        },
        columns=PEAK_COLUMNS,
    )
    return table.sort_values("center", ignore_index=True)


def detect_peaks_derivative(
    spectrum: Spectrum,
    window: int = 11,
    polyorder: int = 4,
    prominence: float | None = None,
    snr: float = 12.0,
) -> pd.DataFrame:
    """Find band positions as minima of the second derivative.

    The second derivative of a band has a sharp negative minimum at the band
    center, narrower than the band itself. A shoulder or a partly hidden
    band that makes no maximum in the spectrum still makes its own minimum
    in the second derivative, so this finds bands that `detect_peaks`
    misses. It is the usual way to locate overlapping bands in IR spectra
    before fitting them [1]_, [2]_.

    Parameters
    ----------
    spectrum : Spectrum
        Spectrum in absorbance, *not* smoothed: the derivative filter
        smooths, and the noise is estimated from the unsmoothed points.
        Points must be evenly spaced in `x`.
    window : int, default 11
        Savitzky–Golay window length in points (odd). A small window keeps
        close bands apart; a larger one copes with more noise but blurs
        them together and can add small ripples next to strong peaks.
    polyorder : int, default 4
        Degree of the Savitzky–Golay polynomial; at least 2. A higher order
        keeps the derivative minima narrower [3]_.
    prominence : float, optional
        Minimum prominence of a minimum of the second derivative
        (absorbance per cm⁻²). Defaults to `snr` times the noise in the
        second derivative; see Notes.
    snr : float, default 12.0
        Signal-to-noise ratio used for the default `prominence`.

    Returns
    -------
    pd.DataFrame
        One row per band, sorted by center, with the columns of
        `detect_peaks`: ``center`` (cm⁻¹), ``fwhm`` (NaN, see Notes),
        ``height`` (absorbance of the smoothed spectrum at ``center``) and
        ``prominence`` (of the second-derivative minimum, absorbance per
        cm⁻²).

    Raises
    ------
    ValueError
        If the points are not evenly spaced in `x`.

    Notes
    -----
    The derivative is computed with a Savitzky–Golay filter, which fits a
    polynomial in each window and differentiates it. That is much less noisy
    than differences of neighbouring points. It is still noisier than the
    spectrum, so the threshold is set from the noise *after* the filter:
    for white noise of standard deviation σ, a linear filter with
    coefficients hₖ gives noise of standard deviation σ·√(Σ hₖ²).
    Prominence is measured from a bump's top down to the valleys on either
    side, so a noise bump can be several standard deviations prominent. The
    default `snr` was set on pure synthetic noise: 8 still let through the
    odd false band and 12 none.

    The method has known limits:

    - The depth of a band's second-derivative minimum scales as
      height / FWHM², so broad bands (e.g. O–H, FWHM ~300 cm⁻¹) almost
      vanish and are usually missed.
    - It needs low noise. At a noise level that `detect_peaks` handles after
      smoothing, the threshold the derivative needs can hide real bands.
    - It gives positions only. A band's width can't be read reliably off
      the derivative of overlapping bands, so ``fwhm`` is NaN; widths and
      areas come from fitting (step 5).

    Constant and linear baselines have a zero second derivative, so the
    method is not affected by them.

    References
    ----------
    .. [1] Susi and Byler, "Resolution-enhanced Fourier transform
       infrared spectroscopy of enzymes," Methods Enzymol. 130, 290–311
       (1986).
    .. [2] A. Savitzky and M. J. E. Golay, "Smoothing and differentiation of
       data by simplified least squares procedures," Anal. Chem. 36,
       1627–1639 (1964).
    .. [3] M. A. Czarnecki, "Resolution enhancement in second-derivative
       spectra," Appl. Spectrosc. 69, 67–74 (2015).
    """
    spacing = _even_spacing(spectrum.x)
    coeffs = signal.savgol_coeffs(window, polyorder, deriv=2, delta=spacing)
    # Negated, so band centers are maxima and find_peaks can be used.
    curvature = -np.asarray(
        signal.savgol_filter(spectrum.y, window, polyorder, deriv=2, delta=spacing)
    )
    if prominence is None:
        prominence = snr * estimate_noise(spectrum) * np.linalg.norm(coeffs)
    prominence = max(prominence, 1e-12)

    # height=0: a band center has negative curvature; maxima of the negated
    # derivative below zero are dips between side lobes, not bands.
    index, props = signal.find_peaks(curvature, prominence=prominence, height=0)
    center, _ = _refine_top(spectrum.x, curvature, index)
    smoothed = np.asarray(signal.savgol_filter(spectrum.y, window, polyorder))
    table = pd.DataFrame(
        {
            "center": center,
            "fwhm": np.nan,
            "height": np.interp(center, spectrum.x, smoothed),
            "prominence": props["prominences"],
        },
        columns=PEAK_COLUMNS,
    )
    return table.sort_values("center", ignore_index=True)


def match_peaks(
    found: pd.DataFrame, true: pd.DataFrame, tolerance: float = 10.0
) -> pd.DataFrame:
    """Pair detected peaks with true (or reference) peaks by center.

    The closest pairs are matched first, and each peak is used at most once,
    so two detections can't both claim the same true peak.

    Parameters
    ----------
    found : pd.DataFrame
        Detected peaks, with a ``center`` column (cm⁻¹), e.g. from
        `detect_peaks`.
    true : pd.DataFrame
        True peaks, with a ``center`` column (cm⁻¹), e.g. from
        `spectro.synthetic.make_spectrum`.
    tolerance : float, default 10.0
        Largest center difference (cm⁻¹) that still counts as a match.

    Returns
    -------
    pd.DataFrame
        One row per matched pair, missed true peak or false detection, with
        the columns of `true` suffixed ``_true`` and those of `found`
        suffixed ``_found``. A missed true peak has NaN in the ``_found``
        columns; a false detection has NaN in the ``_true`` columns.

    Examples
    --------
    >>> matched = match_peaks(detect_peaks(spectrum), true_peaks)
    >>> recall = matched["center_found"].notna().sum() / len(true_peaks)
    """
    distance = np.abs(
        true["center"].to_numpy()[:, None] - found["center"].to_numpy()[None, :]
    )
    pairs: list[tuple[int, int]] = []
    used_true: set[int] = set()
    used_found: set[int] = set()
    for flat in np.argsort(distance, axis=None):
        i, j = np.unravel_index(flat, distance.shape)
        if distance[i, j] > tolerance:
            break
        if i not in used_true and j not in used_found:
            pairs.append((int(i), int(j)))
            used_true.add(int(i))
            used_found.add(int(j))

    missed = [(i, None) for i in range(len(true)) if i not in used_true]
    false = [(None, j) for j in range(len(found)) if j not in used_found]
    rows = [
        {**_row(true, i, "_true"), **_row(found, j, "_found")}
        for i, j in pairs + missed + false
    ]
    columns = [f"{c}_true" for c in true.columns] + [
        f"{c}_found" for c in found.columns
    ]
    table = pd.DataFrame(rows, columns=columns)
    # Sort by the true center, or the found one for false detections.
    order = table["center_true"].fillna(table["center_found"]).argsort()
    return table.iloc[order].reset_index(drop=True)


def _refine_top(
    x: np.ndarray, y: np.ndarray, index: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return the vertex of a parabola through each peak's top three points."""
    before, top, after = y[index - 1], y[index], y[index + 1]
    curvature = before - 2 * top + after
    # A flat top (zero curvature) has no unique vertex; keep the data point.
    safe = np.where(curvature == 0, 1.0, curvature)
    offset = np.where(curvature == 0, 0.0, 0.5 * (before - after) / safe)
    center = np.interp(index + offset, np.arange(len(x)), x)
    height = top - 0.25 * (before - after) * offset
    return center, height


def _row(table: pd.DataFrame, i: int | None, suffix: str) -> dict:
    """Return row `i` of `table` with suffixed keys, or NaNs if `i` is None."""
    if i is None:
        return {f"{c}{suffix}": np.nan for c in table.columns}
    return {f"{c}{suffix}": v for c, v in table.iloc[i].items()}


def _even_spacing(x: np.ndarray) -> float:
    """Return the point spacing of `x`, raising ValueError if it isn't even."""
    steps = np.diff(x)
    spacing = float(np.median(steps))
    if not np.allclose(steps, spacing, rtol=1e-3):
        raise ValueError("points must be evenly spaced in x")
    return spacing
