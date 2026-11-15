"""spectro: tools for analyzing IR spectra."""

from spectro.loaders import load_csv
from spectro.peaks import (
    detect_peaks,
    detect_peaks_derivative,
    estimate_noise,
    match_peaks,
)
from spectro.plotting import plot_spectrum
from spectro.preprocessing import estimate_baseline, normalize, remove_baseline, smooth
from spectro.spectrum import Spectrum
from spectro.synthetic import Peak, make_spectrum

__all__ = [
    "Peak",
    "Spectrum",
    "detect_peaks",
    "detect_peaks_derivative",
    "estimate_baseline",
    "estimate_noise",
    "load_csv",
    "make_spectrum",
    "match_peaks",
    "normalize",
    "plot_spectrum",
    "remove_baseline",
    "smooth",
]
