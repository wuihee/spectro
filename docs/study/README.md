# Study guide

A guide to understanding what has been built so far, why it was built that
way, and how to explain it. This page has the overview; each step has its
own file (see [Steps](#steps)) with:

- **The idea:** the mental model in a few sentences.
- **Read:** the files to look at, in order.
- **Try:** small experiments to run in a notebook.
- **Design choices:** what was decided and the one-line reason, which is
  what your professor is most likely to ask about.
- **Literature:** whether the method is standard, with a link to the
  sources in [LITERATURE.md](../LITERATURE.md).
- **Check yourself:** questions to answer out loud before moving on.
  Answers are folded underneath; try first.

Don't try to memorise the code. Aim to be able to explain *what each piece is
for* and *why it is shaped the way it is*.

---

## The big picture

The project goal: take IR spectra, find and measure their peaks (including
overlapping ones), and classify samples by type. Then find out how much data
that needs.

The whole project is a pipeline, where each step takes the output of the one
before:

```text
 file / synthetic ──► Spectrum ──► preprocess ──► detect peaks ──► fit peaks ──► features ──► classify
     (1, 2)            (1)            (3)             (4)           (5, 6)          (7)          (7, 8)
```

Two ideas hold it together:

1. **One data type.** Every step takes and returns a `Spectrum`. Nothing
   downstream needs to know where the data came from.
2. **Ground truth from synthetic data.** With real data we never know the
   "right" peaks, so we can't tell if a method works. With synthetic data we
   do, so every later step is tested by asking: *did it recover the peaks we
   put in?*

If you can draw this pipeline and explain those two ideas, you understand the
architecture.

---

## Background science (just enough)

| Term | What it means here |
| --- | --- |
| **Wavenumber (cm⁻¹)** | The x-axis of an IR spectrum: 1 / wavelength. Higher = more energetic vibration. IR plots run from ~4000 on the left to ~400 on the right, by convention. |
| **Transmittance (T, %T)** | Fraction of light that gets through the sample. Peaks point *down*. Often what the instrument exports. |
| **Absorbance (A)** | A = −log₁₀(T). Peaks point *up*. |
| **Beer–Lambert law** | A = ε · c · l: absorbance is proportional to concentration. This is why we analyse in absorbance, not transmittance. |
| **Band / peak** | A bump in the spectrum from one molecular vibration (e.g. C=O stretch near 1715 cm⁻¹). |
| **Center, height, FWHM, area** | Where the peak is, how tall, how wide at half its height, and the total area under it. Area tracks the *amount* of that bond. |
| **Line shape** | The mathematical curve of a single peak: Gaussian, Lorentzian, or a mix. |

---

## Steps

| Step | Study file | Notebook |
| --- | --- | --- |
| 1 | [The `Spectrum` object](01_spectrum.md) | `notebooks/01_spectrum_basics.ipynb` |
| 2 | [Synthetic spectra](02_synthetic_data.md) | `notebooks/02_synthetic_data.ipynb` |
| 3 | [Preprocessing](03_preprocessing.md) | `notebooks/03_preprocessing.ipynb` |
| 4 | [Peak detection](04_peak_detection.md) | `notebooks/04_peak_detection.ipynb` |

---

## Ready to move on when you can…

- [ ] Draw the pipeline from memory and say what each step takes in and
      gives out.
- [ ] Explain in two sentences why everything uses one `Spectrum` type.
- [ ] Explain why we analyse in absorbance.
- [ ] Explain why synthetic data comes first, and what "ground truth" buys us.
- [ ] Sketch a Gaussian and a Lorentzian with the same height and FWHM, and
      say which has more area.
- [ ] Build a spectrum with `make_spectrum` from your own peak list, without
      looking at the notebook.
- [ ] Explain what arPLS does in one sentence and what `lam` controls.
- [ ] Explain the smoothing trade-off and pick a window for a given FWHM.
- [ ] Say why the order is baseline → smooth → normalise.
- [ ] Explain prominence, and why the detection threshold is a multiple of
      the noise.
- [ ] Say why noise is estimated before smoothing and peaks detected after.
- [ ] Name two cases where detection gets a peak wrong (shoulder, close
      overlap) and what will fix them.
- [ ] Explain how the second derivative finds hidden bands, and its two
      main limits.
- [ ] For each step, say whether our method is standard in the literature,
      and name one place where we simplified or deviated, and why (see
      `docs/LITERATURE.md`).
- [ ] Answer every "Check yourself" question in the step files without
      opening the answers.

## Explaining it to your professor (≈ 1 minute)

> We're building an IR analysis pipeline: load or generate a spectrum,
> preprocess it, detect and fit peaks, then classify samples. Everything
> passes around one validated `Spectrum` object, so each stage is
> independent and swappable. Before writing any analysis, we built a
> synthetic generator: we describe a spectrum as a list of peaks with known
> center, width, height and shape (Gaussian, Lorentzian or pseudo-Voigt),
> plus noise and baseline. It returns the true peak table alongside the
> spectrum, so every later stage can be measured against ground truth. That
> also lets us control noise and peak overlap to find where methods break
> down, and later, how much data classification needs. Preprocessing is a
> set of small functions run in order: arPLS baseline removal, Savitzky–Golay
> smoothing and normalisation. Each is tested by checking it gives back the
> clean synthetic spectrum. Peak detection keeps a local maximum only if its
> prominence is more than five times the noise, which we estimate robustly
> from second differences before smoothing. It returns the same columns as
> the true peak table, and on noisy synthetic spectra it finds every peak
> with no false ones, centers within about a wavenumber. For low-noise
> spectra we also find bands as minima of the second derivative, the
> standard IR way to reveal shoulders and overlapping bands.

Be ready for follow-ups like: *Why pseudo-Voigt and not a true Voigt?* (A
standard, cheap approximation that is close enough for IR and is what we'll
fit with later.) *How do you know the generator is correct?* (Tests check
height at center, FWHM and area against the formulas for every shape.) *Why
arPLS and not AsLS or a polynomial?* (On our test spectra it got back the
true baseline best, and it doesn't need to know where the peaks are.) *How
did you choose the smoothing window?* (Below the narrowest peak's FWHM in
points; the tests show the peak flattening once the window is wider.)
*Why not just threshold on height?* (Height depends on the baseline and
doesn't reject noise wiggles on top of big peaks; prominence does both.)
*What happens with overlapping peaks?* (Equal peaks closer than about ¾
FWHM merge into one; the second derivative separates them down to about half
a FWHM on clean data, and deconvolution in step 6 goes further.) *Are these
standard methods?* (Yes, each step was checked against the literature, with
sources in `docs/LITERATURE.md`. The main deviations are a baseline stiffness
tuned higher than the library default, and a simplified, symmetric
pseudo-Voigt; both get checked on real spectra in step 9.)
