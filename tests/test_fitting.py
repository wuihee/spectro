import numpy as np
import pytest

from spectro.fitting import FIT_COLUMNS, fit_peak, fit_peaks, peak_model
from spectro.peaks import detect_peaks, estimate_noise, match_peaks
from spectro.preprocessing import remove_baseline, smooth
from spectro.synthetic import Peak, make_spectrum

PEAKS = [
    Peak(3350, 300, 0.6, shape="gaussian"),
    Peak(2950, 40, 0.4),
    Peak(2870, 30, 0.3),
    Peak(1715, 25, 0.9),
    Peak(1100, 50, 0.5, shape="lorentzian"),
]
ISOLATED = [1100, 1715, 3350]


@pytest.mark.parametrize("shape", ["gaussian", "lorentzian", "pseudo_voigt"])
def test_fit_recovers_clean_peak_of_each_shape(shape):
    true = Peak(1715.3, 25, 0.9, shape=shape, eta=0.3)
    spectrum, _ = make_spectrum([true])
    # Deliberately poor starting values.
    result = fit_peak(spectrum, 1712, 20, 0.7, shape=shape)
    params = result.params
    assert params["center"].value == pytest.approx(true.center, abs=1e-3)
    assert params["fwhm"].value == pytest.approx(true.fwhm, rel=1e-3)
    assert params["height"].value == pytest.approx(true.height, rel=1e-3)
    assert params["area"].value == pytest.approx(true.area, rel=1e-3)
    if shape == "pseudo_voigt":
        assert params["eta"].value == pytest.approx(true.eta, abs=1e-3)


def test_pseudo_voigt_fit_identifies_shape():
    spectrum, _ = make_spectrum(
        [Peak(1100, 50, 0.5, shape="lorentzian"), Peak(1715, 25, 0.9, "gaussian")]
    )
    fitted = fit_peaks(spectrum, detect_peaks(spectrum))
    np.testing.assert_allclose(fitted["eta"], [1.0, 0.0], atol=1e-3)


def test_fit_ignores_linear_background():
    spectrum, _ = make_spectrum([Peak(1715, 25, 0.9)], baseline=(0.2, 0.3))
    result = fit_peak(spectrum, 1715, 25, 1.0)
    assert result.params["height"].value == pytest.approx(0.9, rel=1e-3)
    assert result.params["fwhm"].value == pytest.approx(25, rel=1e-3)


def test_errors_match_scatter_over_noise_realisations():
    true = Peak(1715.3, 25, 0.9)
    covered = {name: 0 for name in ["center", "fwhm", "height", "area"]}
    runs = 100
    for seed in range(runs):
        spectrum, _ = make_spectrum([true], noise=0.01, seed=seed)
        params = fit_peak(spectrum, 1714, 22, 0.85).params
        for name in covered:
            value, err = params[name].value, params[name].stderr
            covered[name] += abs(value - getattr(true, name)) < err
    # A correct standard error contains the truth about 68 % of the time.
    for name, hits in covered.items():
        assert 0.55 < hits / runs < 0.8, name


def test_smoothing_before_fitting_makes_errors_too_small():
    true = Peak(1715.3, 25, 0.9)
    covered = 0
    runs = 50
    for seed in range(runs):
        raw, _ = make_spectrum([true], noise=0.01, seed=seed)
        params = fit_peak(smooth(raw), 1714, 22, 0.85).params
        covered += abs(params["height"].value - true.height) < params["height"].stderr
    assert covered / runs < 0.3


def test_fit_peaks_on_noisy_spectrum_measures_isolated_peaks():
    raw, true = make_spectrum(PEAKS, noise=0.01, baseline=(0.05, 0.1, -0.05), seed=3)
    corrected = remove_baseline(raw)
    noise = estimate_noise(corrected)
    found = detect_peaks(smooth(corrected), prominence=5 * noise)
    fitted = fit_peaks(corrected, found)
    assert list(fitted.columns) == FIT_COLUMNS

    matched = match_peaks(fitted, true, tolerance=40)
    isolated = matched[matched["center_true"].isin(ISOLATED)]
    np.testing.assert_allclose(
        isolated["center_found"], isolated["center_true"], atol=1
    )
    np.testing.assert_allclose(isolated["area_found"], isolated["area_true"], rtol=0.05)
    # A good fit leaves only noise behind.
    np.testing.assert_allclose(fitted["rms_residual"], noise, rtol=0.2)


def test_overlapping_peaks_lose_area_when_fitted_alone():
    spectrum, true = make_spectrum(PEAKS[1:3])
    fitted = fit_peaks(spectrum, detect_peaks(spectrum))
    matched = match_peaks(fitted, true)
    assert (matched["area_found"] < 0.95 * matched["area_true"]).to_numpy().all()


def test_window_stops_halfway_to_neighbour():
    spectrum, _ = make_spectrum([Peak(1700, 20, 1.0), Peak(1800, 20, 1.0)])
    found = detect_peaks(spectrum)
    found.loc[:, "fwhm"] = 200.0  # a window this wide would reach the neighbour
    fitted = fit_peaks(spectrum, found)
    np.testing.assert_allclose(fitted["fwhm"], 20, rtol=1e-2)


def test_fit_rejects_window_with_too_few_points():
    spectrum, _ = make_spectrum([Peak(1715, 25, 0.9)])
    with pytest.raises(ValueError):
        fit_peak(spectrum, 1715, 25, 0.9, x_range=(1714, 1718))


def test_peak_model_rejects_unknown_shape():
    with pytest.raises(ValueError):
        peak_model("voigt")  # pyright: ignore[reportArgumentType]
