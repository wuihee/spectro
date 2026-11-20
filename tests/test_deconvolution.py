import numpy as np
import pandas as pd
import pytest

from spectro.deconvolution import (
    COMPARE_COLUMNS,
    compare_peak_counts,
    deconvolve,
    find_regions,
    fit_region,
    fit_table,
)
from spectro.fitting import FIT_COLUMNS, fit_peaks
from spectro.peaks import detect_peaks, estimate_noise, match_peaks
from spectro.preprocessing import smooth
from spectro.synthetic import Peak, make_spectrum

CH_PAIR = [Peak(2950, 40, 0.4), Peak(2870, 30, 0.3)]
CH_STARTS = pd.DataFrame(
    {"center": [2865.0, 2955.0], "fwhm": [25.0, 35.0], "height": [0.25, 0.35]}
)
CH_RANGE = (2780.0, 3040.0)


def _detect(spectrum):
    return detect_peaks(smooth(spectrum), prominence=5 * estimate_noise(spectrum))


def _table(centers, fwhms):
    return pd.DataFrame(
        {"center": centers, "fwhm": fwhms, "height": [1.0] * len(centers)}
    )


def test_find_regions_groups_overlapping_peaks():
    regions = find_regions(_table([1000, 1050, 1500], [30, 30, 30]))
    assert [len(r.peaks) for r in regions] == [2, 1]
    assert regions[0].x_range == (940, 1110)
    assert regions[1].x_range == (1440, 1560)


def test_find_regions_chains_neighbours():
    # 1000 and 1200 don't overlap each other, but both overlap 1100.
    regions = find_regions(_table([1200, 1000, 1100], [30, 30, 30]))
    assert len(regions) == 1
    assert regions[0].peaks["center"].tolist() == [1000, 1100, 1200]


def test_find_regions_rejects_missing_fwhm():
    with pytest.raises(ValueError):
        find_regions(_table([1000, 1100], [30, np.nan]))


def test_joint_fit_recovers_clean_overlapping_pair():
    spectrum, true = make_spectrum(CH_PAIR)
    fitted = fit_table(fit_region(spectrum, CH_STARTS, CH_RANGE), "pseudo_voigt")
    assert list(fitted.columns) == FIT_COLUMNS
    for name in ["center", "fwhm", "height", "area"]:
        np.testing.assert_allclose(fitted[name], true[name], rtol=1e-3)


def test_joint_fit_keeps_area_that_single_fits_lose():
    spectrum, true = make_spectrum(CH_PAIR, noise=0.01, seed=3)
    found = _detect(spectrum)
    single = match_peaks(fit_peaks(spectrum, found), true)
    joint = match_peaks(deconvolve(spectrum, found), true)
    single_error = np.abs(single["area_found"] / single["area_true"] - 1)
    joint_error = np.abs(joint["area_found"] / joint["area_true"] - 1)
    assert (single_error > 0.1).any()
    assert (joint_error < 0.05).all()


def test_joint_fit_errors_match_scatter_over_noise_realisations():
    hits = np.zeros(2)
    runs = 60
    for seed in range(runs):
        spectrum, true = make_spectrum(CH_PAIR, noise=0.01, seed=seed)
        fitted = fit_table(fit_region(spectrum, CH_STARTS, CH_RANGE), "pseudo_voigt")
        hits += np.abs(fitted["area"] - true["area"]) < fitted["area_err"]
    assert np.all((0.55 < hits / runs) & (hits / runs < 0.85))


def test_bic_keeps_a_single_peak_single():
    for seed in range(5):
        spectrum, _ = make_spectrum([Peak(1715, 25, 0.9)], noise=0.01, seed=seed)
        region = find_regions(_detect(spectrum))[0]
        scores, results = compare_peak_counts(spectrum, region, max_extra=2)
        assert list(scores.columns) == COMPARE_COLUMNS
        assert len(results) == 3
        assert scores.loc[scores["bic"].idxmin(), "n_peaks"] == 1


def test_deconvolve_separates_peaks_detection_merges():
    # 0.6 FWHM apart: one maximum, so detection finds one peak.
    pair = [Peak(1694, 20, 0.5), Peak(1706, 20, 0.5)]
    spectrum, true = make_spectrum(pair, noise=0.002, seed=0)
    found = _detect(spectrum)
    assert len(found) == 1
    fitted = deconvolve(spectrum, found)
    assert len(fitted) == 2
    np.testing.assert_allclose(fitted["center"], true["center"], atol=1)
    np.testing.assert_allclose(fitted["area"], true["area"], rtol=0.05)


def test_deconvolve_labels_regions():
    peaks = [Peak(1100, 50, 0.5), *CH_PAIR]
    spectrum, _ = make_spectrum(peaks, noise=0.005, seed=1)
    fitted = deconvolve(spectrum, _detect(spectrum))
    assert list(fitted.columns) == [*FIT_COLUMNS, "region"]
    assert fitted["region"].tolist() == [0, 1, 1]


def test_fit_region_rejects_no_peaks():
    spectrum, _ = make_spectrum(CH_PAIR)
    with pytest.raises(ValueError):
        fit_region(spectrum, CH_STARTS.iloc[:0], CH_RANGE)


def test_fit_region_rejects_too_few_points():
    spectrum, _ = make_spectrum(CH_PAIR)
    with pytest.raises(ValueError):
        fit_region(spectrum, CH_STARTS, (2860, 2870))
