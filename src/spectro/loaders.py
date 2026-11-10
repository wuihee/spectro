"""Read spectra from files.

There is no fixed file format yet, so this starts with plain delimited text
(CSV, TSV, whitespace). Vendor formats can be added here later as separate
functions that also return a `Spectrum`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from spectro.spectrum import Spectrum


def load_csv(
    path: str | Path,
    x_col: int | str = 0,
    y_col: int | str = 1,
    y_unit: str = "absorbance",
    sep: str | None = None,
) -> Spectrum:
    """Load a delimited text file into a `Spectrum`.

    A header row is detected automatically, and lines starting with ``#`` are
    ignored.

    Parameters
    ----------
    path : str or Path
        File to read.
    x_col, y_col : int or str, default 0 and 1
        Column holding wavenumber and signal, as a position or header name.
    y_unit : str, default "absorbance"
        Unit of the signal column; see `Spectrum`.
    sep : str, optional
        Column delimiter. If None, pandas guesses it (comma, tab, spaces...).

    Returns
    -------
    Spectrum
        The spectrum, with the file path stored in ``metadata["source"]``.
    """
    path = Path(path)
    header = 0 if _has_header(path, sep) else None
    table = pd.read_csv(path, sep=sep, header=header, engine="python", comment="#")

    x = _column(table, x_col)
    y = _column(table, y_col)
    return Spectrum(x=x, y=y, y_unit=y_unit, metadata={"source": str(path)})


def _has_header(path: Path, sep: str | None) -> bool:
    """Check whether the first row is text (column names) rather than numbers."""
    first_row = pd.read_csv(
        path, sep=sep, header=None, nrows=1, engine="python", comment="#"
    )
    numeric = pd.to_numeric(first_row.iloc[0], errors="coerce")
    return bool(numeric.isna().any())


def _column(table: pd.DataFrame, col: int | str) -> np.ndarray:
    """Select a column by position or by name."""
    if isinstance(col, int):
        return table.iloc[:, col].to_numpy()
    return table[col].to_numpy()
