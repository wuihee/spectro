import numpy as np
import pytest

from spectro.synthetic import Peak, make_spectrum

SHAPES = ["gaussian", "lorentzian", "pseudo_voigt"]


def measured_fwhm(x, y):
    above = x[y >= y.max() / 2]
    return above[-1] - above[0]


@pytest.mark.parametrize("shape", SHAPES)
def test_peak_has_given_height_at_center(shape):
    peak = Peak(center=1700, fwhm=20, height=0.8, shape=shape)
    assert peak.evaluate(np.array([1700.0]))[0] == pytest.approx(0.8)


@pytest.mark.parametrize("shape", SHAPES)
def test_peak_has_given_fwhm(shape):
    x = np.linspace(1500, 1900, 400_001)  # 0.001 cm⁻¹ spacing
    peak = Peak(center=1700, fwhm=20, height=0.8, shape=shape)
    assert measured_fwhm(x, peak.evaluate(x)) == pytest.approx(20, abs=0.01)


@pytest.mark.parametrize("shape", SHAPES)
def test_area_formula_matches_numerical_integral(shape):
    # Wide range so the Lorentzian's long tails are (almost) all included.
    x = np.linspace(1700 - 20_000, 1700 + 20_000, 2_000_001)
    peak = Peak(center=1700, fwhm=20, height=0.8, shape=shape)
    assert np.trapezoid(peak.evaluate(x), x) == pytest.approx(peak.area, rel=1e-3)


def test_invalid_peak_is_rejected():
    with pytest.raises(ValueError):
        Peak(center=1700, fwhm=-5, height=1)
    with pytest.raises(ValueError):
        Peak(center=1700, fwhm=5, height=1, eta=1.5)
    with pytest.raises(ValueError):
        Peak(center=1700, fwhm=5, height=1, shape="triangle")


def test_clean_spectrum_is_sum_of_peaks():
    peaks = [Peak(1000, 10, 0.5), Peak(1700, 20, 0.9, shape="gaussian")]
    spectrum, _ = make_spectrum(peaks)
    expected = peaks[0].evaluate(spectrum.x) + peaks[1].evaluate(spectrum.x)
    np.testing.assert_allclose(spectrum.y, expected)


def test_baseline_coefficients_are_in_absorbance_units():
    spectrum, _ = make_spectrum([], baseline=(0.1, 0.2))
    assert spectrum.y[0] == pytest.approx(0.1)  # t = 0 at the low end
    assert spectrum.y[-1] == pytest.approx(0.3)  # t = 1 at the high end


def test_noise_level_and_seed():
    a, _ = make_spectrum([], noise=0.01, seed=1)
    b, _ = make_spectrum([], noise=0.01, seed=1)
    np.testing.assert_array_equal(a.y, b.y)
    assert a.y.std() == pytest.approx(0.01, rel=0.1)


def test_true_peak_table_matches_input():
    peaks = [Peak(1700, 20, 0.9), Peak(1000, 10, 0.5, shape="lorentzian")]
    _, table = make_spectrum(peaks)
    assert list(table.columns) == ["shape", "center", "fwhm", "height", "area"]
    assert list(table["center"]) == [1000, 1700]  # sorted by center
    assert table["area"].iloc[1] == pytest.approx(peaks[0].area)
