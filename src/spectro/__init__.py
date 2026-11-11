"""spectro: tools for analyzing IR spectra."""

from spectro.loaders import load_csv
from spectro.plotting import plot_spectrum
from spectro.preprocessing import estimate_baseline, normalize, remove_baseline, smooth
from spectro.spectrum import Spectrum
from spectro.synthetic import Peak, make_spectrum

__all__ = [
    "Peak",
    "Spectrum",
    "estimate_baseline",
    "load_csv",
    "make_spectrum",
    "normalize",
    "plot_spectrum",
    "remove_baseline",
    "smooth",
]
