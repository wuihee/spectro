"""Peak line shapes, each described by center, FWHM and height.

All three shapes reach exactly `height` at `center` and have full width at
half maximum `fwhm`, so they can be swapped without changing the look of a
peak's size.
"""

from __future__ import annotations

import numpy as np

# Ratio of area to height × FWHM for each shape.
GAUSSIAN_AREA_FACTOR = np.sqrt(np.pi / (4 * np.log(2)))  # ≈ 1.0645
LORENTZIAN_AREA_FACTOR = np.pi / 2  # ≈ 1.5708


def gaussian(x: np.ndarray, center: float, fwhm: float, height: float) -> np.ndarray:
    """Evaluate a Gaussian peak.

    Parameters
    ----------
    x : np.ndarray
        Wavenumbers (cm⁻¹) to evaluate at.
    center : float
        Peak position (cm⁻¹).
    fwhm : float
        Full width at half maximum (cm⁻¹).
    height : float
        Peak value at `center`.

    Returns
    -------
    np.ndarray
        Peak values at each `x`.

    Notes
    -----
    G(x) = h · exp(−4 ln2 · (x − c)² / w²), with area ≈ 1.0645 · h · w.
    """
    return height * np.exp(-4 * np.log(2) * ((x - center) / fwhm) ** 2)


def lorentzian(x: np.ndarray, center: float, fwhm: float, height: float) -> np.ndarray:
    """Evaluate a Lorentzian peak.

    Lorentzians have much longer tails than Gaussians of the same FWHM.

    Parameters
    ----------
    x : np.ndarray
        Wavenumbers (cm⁻¹) to evaluate at.
    center : float
        Peak position (cm⁻¹).
    fwhm : float
        Full width at half maximum (cm⁻¹).
    height : float
        Peak value at `center`.

    Returns
    -------
    np.ndarray
        Peak values at each `x`.

    Notes
    -----
    L(x) = h / (1 + 4 (x − c)² / w²), with area = π/2 · h · w.
    """
    return height / (1 + 4 * ((x - center) / fwhm) ** 2)


def pseudo_voigt(
    x: np.ndarray, center: float, fwhm: float, height: float, eta: float
) -> np.ndarray:
    """Evaluate a pseudo-Voigt peak, a weighted mix of Lorentzian and Gaussian.

    The usual approximation for real IR bands, which have both Lorentzian
    (natural) and Gaussian (disorder, instrument) broadening.

    Parameters
    ----------
    x : np.ndarray
        Wavenumbers (cm⁻¹) to evaluate at.
    center : float
        Peak position (cm⁻¹).
    fwhm : float
        Full width at half maximum (cm⁻¹), shared by both parts.
    height : float
        Peak value at `center`.
    eta : float
        Lorentzian fraction, from 0 (pure Gaussian) to 1 (pure Lorentzian).

    Returns
    -------
    np.ndarray
        Peak values at each `x`.

    Notes
    -----
    PV(x) = η · L(x) + (1 − η) · G(x). Because both parts share `height` and
    `fwhm`, so does the mix, and its area is the same mix of their areas.

    Here η is a free shape parameter, as in Gaussian–Lorentzian curve
    fitting. The pseudo-Voigt is also used to approximate a true Voigt
    profile; the Thompson–Cox–Hastings version [1]_ computes η and the FWHM
    from the Voigt's Gaussian and Lorentzian widths, and Ida et al. [2]_ give
    a more accurate extended form.

    References
    ----------
    .. [1] Thompson, Cox and Hastings, "Rietveld refinement of Debye–Scherrer
       synchrotron X-ray data from Al₂O₃," J. Appl. Cryst. 20, 79–83 (1987).
    .. [2] Ida, Ando and Toraya, "Extended pseudo-Voigt function for
       approximating the Voigt profile," J. Appl. Cryst. 33, 1311–1316
       (2000).
    """
    return eta * lorentzian(x, center, fwhm, height) + (1 - eta) * gaussian(
        x, center, fwhm, height
    )
