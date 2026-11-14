import numpy as np
import pytest

from spectro.preprocessing import (
    NormMethod,
    estimate_baseline,
    normalize,
    remove_baseline,
    smooth,
)
from spectro.synthetic import Peak, make_spectrum

PEAKS = [
    Peak(3350, 300, 0.6, shape="gaussian"),
    Peak(2950, 40, 0.4),
    Peak(1715, 25, 0.9),
    Peak(1100, 50, 0.5, shape="lorentzian"),
]
BASELINE = (0.05, 0.1, -0.05)


def rms(a, b):
    return np.sqrt(np.mean((a - b) ** 2))


def test_remove_baseline_recovers_clean_spectrum():
    raw, _ = make_spectrum(PEAKS, baseline=BASELINE)
    clean, _ = make_spectrum(PEAKS)
    corrected = remove_baseline(raw)
    np.testing.assert_allclose(corrected.y, clean.y, atol=0.005)


def test_remove_baseline_works_with_noise():
    raw, _ = make_spectrum(PEAKS, noise=0.005, baseline=BASELINE, seed=0)
    noisy, _ = make_spectrum(PEAKS, noise=0.005, seed=0)
    corrected = remove_baseline(raw)
    # Within a few noise standard deviations everywhere.
    assert np.abs(corrected.y - noisy.y).max() < 0.02


def test_estimate_baseline_of_pure_background_is_the_background():
    background, _ = make_spectrum([], baseline=BASELINE)
    baseline = estimate_baseline(background)
    np.testing.assert_allclose(baseline.y, background.y, atol=1e-3)


def test_other_baseline_methods_and_options_are_passed_through():
    raw, _ = make_spectrum(PEAKS, baseline=BASELINE)
    stiff = estimate_baseline(raw, "asls", lam=1e8, p=0.001)
    poly = estimate_baseline(raw, "modpoly", poly_order=2)
    assert stiff.metadata["preprocessing"] == ["estimate_baseline(asls)"]
    assert len(poly) == len(raw)


def test_unknown_baseline_method_is_rejected():
    raw, _ = make_spectrum(PEAKS)
    with pytest.raises(ValueError):
        remove_baseline(raw, "nonsense")
    with pytest.raises(ValueError):
        remove_baseline(raw, "_setup_polynomial")


def test_smoothing_reduces_noise():
    noisy, _ = make_spectrum(PEAKS, noise=0.02, seed=1)
    clean, _ = make_spectrum(PEAKS)
    smoothed = smooth(noisy)
    assert rms(smoothed.y, clean.y) < 0.6 * rms(noisy.y, clean.y)


def test_narrow_window_keeps_peak_height():
    spectrum, _ = make_spectrum([Peak(1700, 40, 1.0)])
    assert smooth(spectrum, window=11).y.max() == pytest.approx(1.0, rel=0.01)


def test_window_wider_than_peak_flattens_it():
    # 51 points = 100 cm⁻¹, five times the FWHM.
    spectrum, _ = make_spectrum([Peak(1700, 20, 1.0)])
    assert smooth(spectrum, window=51).y.max() < 0.9


def test_invalid_smoothing_window_is_rejected():
    spectrum, _ = make_spectrum(PEAKS)
    with pytest.raises(ValueError):
        smooth(spectrum, window=10)
    with pytest.raises(ValueError):
        smooth(spectrum, window=3, polyorder=3)
    with pytest.raises(ValueError):
        smooth(spectrum, window=len(spectrum) + 2)


@pytest.mark.parametrize(
    ("method", "check"),
    [
        ("max", lambda s: s.y.max()),
        ("area", lambda s: np.trapezoid(s.y, s.x)),
        ("vector", lambda s: np.linalg.norm(s.y)),
        ("snv", lambda s: s.y.std()),
    ],
)
def test_normalization_sets_scale_to_one(method, check):
    spectrum, _ = make_spectrum(PEAKS)
    normalized = normalize(spectrum, method)
    assert check(normalized) == pytest.approx(1.0)
    assert normalized.y_unit == f"absorbance ({method}-normalized)"


def test_snv_has_zero_mean():
    spectrum, _ = make_spectrum(PEAKS)
    assert normalize(spectrum, "snv").y.mean() == pytest.approx(0.0, abs=1e-12)


def test_normalization_removes_overall_scale():
    thin, _ = make_spectrum(PEAKS)
    thick = thin.with_y(3 * thin.y)
    methods: list[NormMethod] = ["max", "area", "vector", "snv"]
    for method in methods:
        np.testing.assert_allclose(
            normalize(thin, method).y, normalize(thick, method).y
        )


def test_invalid_normalization_is_rejected():
    spectrum, _ = make_spectrum(PEAKS)
    with pytest.raises(ValueError):
        normalize(spectrum, "median")  # pyright: ignore[reportArgumentType]
    flat, _ = make_spectrum([])
    with pytest.raises(ValueError):
        normalize(flat, "max")


@pytest.mark.parametrize(
    "process",
    [remove_baseline, estimate_baseline, smooth, normalize],
)
def test_input_is_not_modified(process):
    spectrum, _ = make_spectrum(PEAKS, noise=0.01, baseline=BASELINE, seed=0)
    spectrum.metadata["preprocessing"] = ["earlier step"]
    y_before = spectrum.y.copy()
    process(spectrum)
    np.testing.assert_array_equal(spectrum.y, y_before)
    assert spectrum.metadata["preprocessing"] == ["earlier step"]


def test_history_records_steps_in_order():
    raw, _ = make_spectrum(PEAKS, noise=0.01, baseline=BASELINE, seed=0)
    processed = normalize(smooth(remove_baseline(raw)), "snv")
    assert processed.metadata["preprocessing"] == [
        "remove_baseline(arpls)",
        "smooth(11, 3)",
        "normalize(snv)",
    ]
    assert "preprocessing" not in raw.metadata
