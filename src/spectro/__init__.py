"""spectro: tools for analyzing IR spectra."""

from spectro.deconvolution import (
    Region,
    compare_peak_counts,
    deconvolve,
    find_regions,
    fit_region,
    fit_table,
)
from spectro.fitting import fit_peak, fit_peaks, peak_model
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
    "Region",
    "Spectrum",
    "compare_peak_counts",
    "deconvolve",
    "detect_peaks",
    "detect_peaks_derivative",
    "estimate_baseline",
    "estimate_noise",
    "find_regions",
    "fit_peak",
    "fit_peaks",
    "fit_region",
    "fit_table",
    "load_csv",
    "make_spectrum",
    "match_peaks",
    "normalize",
    "peak_model",
    "plot_spectrum",
    "remove_baseline",
    "smooth",
]
