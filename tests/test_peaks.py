import numpy as np
import pandas as pd
import pytest

from spectro.peaks import (
    PEAK_COLUMNS,
    detect_peaks,
    detect_peaks_derivative,
    estimate_noise,
    match_peaks,
)
from spectro.preprocessing import remove_baseline, smooth
from spectro.spectrum import Spectrum
from spectro.synthetic import Peak, make_spectrum

PEAKS = [
    Peak(3350, 300, 0.6, shape="gaussian"),
    Peak(2950, 40, 0.4),
    Peak(2870, 30, 0.3),
    Peak(1715, 25, 0.9),
    Peak(1100, 50, 0.5, shape="lorentzian"),
]
ISOLATED = [1100, 1715, 3350]


def test_estimate_noise_recovers_noise_level():
    spectrum, _ = make_spectrum(PEAKS, noise=0.01, seed=0)
    assert estimate_noise(spectrum) == pytest.approx(0.01, rel=0.1)


def test_estimate_noise_is_near_zero_without_noise():
    spectrum, _ = make_spectrum(PEAKS)
    assert estimate_noise(spectrum) < 1e-4


def test_clean_spectrum_finds_every_peak():
    spectrum, true = make_spectrum(PEAKS)
    found = detect_peaks(spectrum)
    assert list(found.columns) == PEAK_COLUMNS
    np.testing.assert_allclose(found["center"], true["center"], atol=0.5)


def test_isolated_peaks_are_measured_accurately():
    spectrum, true = make_spectrum(PEAKS)
    matched = match_peaks(detect_peaks(spectrum), true)
    isolated = matched[matched["center_true"].isin(ISOLATED)]
    np.testing.assert_allclose(isolated["fwhm_found"], isolated["fwhm_true"], rtol=0.02)
    np.testing.assert_allclose(
        isolated["height_found"], isolated["height_true"], rtol=0.01
    )


def test_center_is_found_between_grid_points():
    spectrum, _ = make_spectrum([Peak(1715.7, 25, 0.9)])
    found = detect_peaks(spectrum)
    # Points are 2 cm⁻¹ apart; the parabola gets well below that.
    assert found["center"].iloc[0] == pytest.approx(1715.7, abs=0.1)


def test_noisy_spectrum_after_preprocessing_finds_true_peaks():
    raw, true = make_spectrum(PEAKS, noise=0.01, baseline=(0.05, 0.1, -0.05), seed=3)
    corrected = remove_baseline(raw)
    noise = estimate_noise(corrected)
    found = detect_peaks(smooth(corrected), prominence=5 * noise)
    # Wide tolerance for the broad O–H band, whose flat top noise can shift.
    matched = match_peaks(found, true, tolerance=40)
    assert matched["center_true"].notna().to_numpy().all()
    assert matched["center_found"].notna().to_numpy().all()


def test_pure_noise_gives_no_peaks_when_smoothed():
    raw, _ = make_spectrum([], noise=0.01, seed=0)
    noise = estimate_noise(raw)
    assert detect_peaks(smooth(raw), prominence=5 * noise).empty


def test_flat_spectrum_gives_empty_table():
    flat, _ = make_spectrum([])
    found = detect_peaks(flat)
    assert found.empty
    assert list(found.columns) == PEAK_COLUMNS


def test_higher_prominence_drops_small_peaks():
    spectrum, _ = make_spectrum(PEAKS)
    found = detect_peaks(spectrum, prominence=0.5)
    assert list(found["center"].round()) == [1715, 3350]


def test_close_peaks_merge_into_one():
    far, _ = make_spectrum([Peak(1700, 20, 1.0), Peak(1740, 20, 1.0)])
    close, _ = make_spectrum([Peak(1700, 20, 1.0), Peak(1710, 20, 1.0)])
    assert len(detect_peaks(far)) == 2
    assert len(detect_peaks(close)) == 1


def test_match_peaks_pairs_closest_and_reports_misses():
    true = pd.DataFrame({"center": [1000.0, 1500.0, 2000.0]})
    found = pd.DataFrame({"center": [1003.0, 1001.0, 2500.0]})
    matched = match_peaks(found, true, tolerance=10)

    pairs = matched.dropna()
    assert list(pairs["center_true"]) == [1000.0]
    assert list(pairs["center_found"]) == [1001.0]
    assert set(matched.loc[matched["center_true"].isna(), "center_found"]) == {
        1003.0,
        2500.0,
    }
    assert set(matched.loc[matched["center_found"].isna(), "center_true"]) == {
        1500.0,
        2000.0,
    }


def test_match_peaks_with_nothing_found():
    true = pd.DataFrame({"center": [1000.0, 1500.0]})
    found = pd.DataFrame({"center": []}, dtype=float)
    matched = match_peaks(found, true)
    assert len(matched) == 2
    assert matched["center_found"].isna().to_numpy().all()


def test_derivative_finds_every_peak_in_clean_spectrum():
    spectrum, true = make_spectrum(PEAKS)
    found = detect_peaks_derivative(spectrum)
    np.testing.assert_allclose(found["center"], true["center"], atol=0.5)
    assert found["fwhm"].isna().to_numpy().all()


def test_derivative_finds_shoulder_that_maxima_miss():
    spectrum, true = make_spectrum([Peak(1700, 30, 1.0), Peak(1725, 20, 0.4)])
    assert len(detect_peaks(spectrum)) == 1
    found = detect_peaks_derivative(spectrum)
    np.testing.assert_allclose(found["center"], true["center"], atol=1.5)


def test_derivative_separates_closer_peaks_than_maxima():
    pair, true = make_spectrum([Peak(1700, 20, 1.0), Peak(1712, 20, 1.0)])
    assert len(detect_peaks(pair)) == 1
    found = detect_peaks_derivative(pair)
    np.testing.assert_allclose(found["center"], true["center"], atol=1.0)


def test_derivative_ignores_linear_baseline():
    flat, _ = make_spectrum(PEAKS[1:])
    sloped, _ = make_spectrum(PEAKS[1:], baseline=(0.2, 0.3))
    np.testing.assert_allclose(
        detect_peaks_derivative(sloped)["center"],
        detect_peaks_derivative(flat)["center"],
    )


def test_derivative_gives_no_peaks_on_pure_noise():
    for seed in range(5):
        raw, _ = make_spectrum([], noise=0.01, seed=seed)
        assert detect_peaks_derivative(raw).empty


def test_derivative_finds_peaks_in_low_noise_spectrum():
    narrow = PEAKS[1:]  # the broad O–H band vanishes in the second derivative
    raw, true = make_spectrum(narrow, noise=0.002, seed=0)
    matched = match_peaks(detect_peaks_derivative(raw), true)
    assert matched["center_true"].notna().to_numpy().all()
    assert matched["center_found"].notna().to_numpy().all()


def test_derivative_rejects_uneven_spacing():
    spectrum = Spectrum(x=np.r_[np.arange(1000, 1100, 2.0), 1105.0], y=np.zeros(51))
    with pytest.raises(ValueError):
        detect_peaks_derivative(spectrum)
