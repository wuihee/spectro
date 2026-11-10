import numpy as np
import pytest

from spectro import Spectrum, load_csv


def test_points_are_sorted_by_wavenumber():
    s = Spectrum(x=[4000, 2000, 400], y=[0.1, 0.5, 0.9])
    assert list(s.x) == [400, 2000, 4000]
    assert list(s.y) == [0.9, 0.5, 0.1]  # y moved with its x


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError, match="differ in length"):
        Spectrum(x=[1, 2, 3], y=[1, 2])


def test_nan_is_rejected():
    with pytest.raises(ValueError, match="NaN"):
        Spectrum(x=[1, 2, 3], y=[1, np.nan, 2])


def test_percent_transmittance_to_absorbance():
    s = Spectrum(x=[1, 2, 3], y=[100, 10, 1], y_unit="%transmittance")
    a = s.to_absorbance()
    np.testing.assert_allclose(a.y, [0, 1, 2])
    assert a.y_unit == "absorbance"
    assert s.y_unit == "%transmittance"  # original untouched


def test_load_csv_with_header(tmp_path):
    path = tmp_path / "with_header.csv"
    path.write_text("wavenumber,absorbance\n4000,0.1\n2000,0.5\n400,0.9\n")
    s = load_csv(path)
    assert len(s) == 3
    assert list(s.x) == [400, 2000, 4000]


def test_load_csv_without_header_keeps_first_row(tmp_path):
    path = tmp_path / "no_header.txt"
    path.write_text("4000\t0.1\n2000\t0.5\n400\t0.9\n")
    s = load_csv(path)
    assert len(s) == 3


def test_load_csv_by_column_name(tmp_path):
    path = tmp_path / "wide.csv"
    path.write_text("wn,sample_a,sample_b\n1000,0.1,0.7\n1100,0.2,0.8\n")
    s = load_csv(path, x_col="wn", y_col="sample_b")
    assert list(s.y) == [0.7, 0.8]
