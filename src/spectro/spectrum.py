"""The `Spectrum` object, the one data type every other module works with."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np


@dataclass
class Spectrum:
    """A single 1-D spectrum.

    Points are always stored with `x` ascending, whatever order they were
    given in, so later code never has to check.

    Parameters
    ----------
    x : array_like
        Wavenumber, in cm⁻¹ for IR. Converted to a float array and sorted.
    y : array_like
        Signal at each `x`, usually absorbance or transmittance. Same length
        as `x`.
    x_unit : str, default "cm⁻¹"
        Unit of `x`.
    y_unit : str, default "absorbance"
        Unit of `y`: "absorbance", "transmittance" (0-1) or "%transmittance".
    metadata : dict, optional
        Free-form information such as the source file or sample label.

    Raises
    ------
    ValueError
        If `x` and `y` are not 1-D, differ in length, or contain NaN or inf.
    """

    x: np.ndarray
    y: np.ndarray
    x_unit: str = "cm⁻¹"
    y_unit: str = "absorbance"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        x = np.asarray(self.x, dtype=float)
        y = np.asarray(self.y, dtype=float)

        if x.ndim != 1 or y.ndim != 1:
            raise ValueError("x and y must be 1-D arrays")
        if x.shape != y.shape:
            raise ValueError(f"x and y differ in length: {x.size} vs {y.size}")
        if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
            raise ValueError("x and y must not contain NaN or inf")

        # IR instruments often export from high to low wavenumber.
        order = np.argsort(x)
        self.x = x[order]
        self.y = y[order]

    def __len__(self) -> int:
        return self.x.size

    def with_y(self, y: np.ndarray, y_unit: str | None = None) -> Spectrum:
        """Return a copy with new y values.

        Processing functions use this so they never modify their input.

        Parameters
        ----------
        y : np.ndarray
            New signal values, same length as `x`.
        y_unit : str, optional
            New unit for `y`. Defaults to the current unit.

        Returns
        -------
        Spectrum
            A new spectrum sharing `x` and a copy of `metadata`.
        """
        return replace(
            self, y=y, y_unit=y_unit or self.y_unit, metadata=dict(self.metadata)
        )

    def to_absorbance(self) -> Spectrum:
        """Convert a transmittance spectrum to absorbance.

        Uses A = -log10(T). Peak areas are only proportional to concentration
        (Beer–Lambert law) in absorbance, so fitting and classification should
        work in absorbance.

        Returns
        -------
        Spectrum
            A new spectrum with `y_unit` "absorbance". If the spectrum is
            already in absorbance, a copy is returned.

        Raises
        ------
        ValueError
            If `y_unit` is not a recognised transmittance or absorbance unit.
        """
        if self.y_unit == "absorbance":
            return self.with_y(self.y.copy())
        if self.y_unit == "%transmittance":
            transmittance = self.y / 100.0
        elif self.y_unit == "transmittance":
            transmittance = self.y
        else:
            raise ValueError(f"don't know how to convert {self.y_unit!r} to absorbance")

        # Clip so that T <= 0 (noise near full absorption) doesn't give inf.
        transmittance = np.clip(transmittance, 1e-6, None)
        return self.with_y(-np.log10(transmittance), y_unit="absorbance")
