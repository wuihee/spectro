"""spectro: tools for analyzing IR spectra."""

from spectro.loaders import load_csv
from spectro.plotting import plot_spectrum
from spectro.spectrum import Spectrum

__all__ = ["Spectrum", "load_csv", "plot_spectrum"]
