"""spectro: tools for analyzing IR spectra."""

from spectro.loaders import load_csv
from spectro.plotting import plot_spectrum
from spectro.spectrum import Spectrum
from spectro.synthetic import Peak, make_spectrum

__all__ = ["Peak", "Spectrum", "load_csv", "make_spectrum", "plot_spectrum"]
