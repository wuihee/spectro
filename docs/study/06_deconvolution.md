# Step 6 · Deconvolving overlapping peaks

## The idea

When two bands overlap, fitting each one on its own (step 5) treats the
other as background, so both lose area. **Deconvolution** here means fitting
them *together*: the model is the sum of all the line shapes in a region,
and the least-squares fit decides how to share the envelope between them.

That raises a new question: **how many peaks are there?** Detection can
miss a band hidden under another, and more peaks always fit better, even
when they are only fitting noise. So we fit the region with 1, 2, 3, ...
peaks and score each fit with an **information criterion** (BIC), which
rewards a smaller residual but charges for every extra parameter. The
lowest score wins.

```text
 detect_peaks ──► find_regions ──► for each region:
                                     fit 1, 2, ..., n+1 peaks (compare_peak_counts)
                                     keep the lowest BIC
                                   ──► peak table (deconvolve)
```

"Deconvolution" is used loosely in IR: strictly it means undoing a
broadening (as in Fourier self-deconvolution); here it means splitting an
envelope into its component bands by curve fitting.

## Read

1. `src/spectro/deconvolution.py`: start with `deconvolve` and its `Notes`
   (why BIC, what it can't tell you). Then `fit_region` (the summed model
   and why overlapping parameters get large errors), `compare_peak_counts`
   (how candidate models are built, the AIC/BIC formulas) and
   `find_regions` (how peaks are grouped). `_add_peak` shows the two ways a
   new peak is started.
2. `tests/test_deconvolution.py`: note
   `test_joint_fit_keeps_area_that_single_fits_lose`,
   `test_bic_keeps_a_single_peak_single` (no overfitting) and
   `test_deconvolve_separates_peaks_detection_merges`.
3. `notebooks/06_deconvolution.ipynb`: run it. Part 4 takes about a minute.

## Key terms

- **Region:** a stretch of spectrum whose peaks overlap (their ±2 FWHM
  spans touch), fitted as one model.
- **AIC / BIC:** N ln(χ²/N) + penalty, where χ² is the sum of squared
  residuals over N points and the penalty is 2 per parameter (AIC) or ln N
  per parameter (BIC). Lower is better; only differences between models on
  the same data mean anything.
- **ΔBIC:** a model's BIC minus the lowest. Above about 6 is strong, above
  10 very strong evidence against it (Kass and Raftery).
- **Overfitting:** adding components that describe noise or artefacts
  rather than real bands. The fit improves; the answer gets worse.
- **Parameter correlation:** two overlapping peaks can trade width and
  height against each other with little change in their sum, so their
  values are uncertain together.

## Try

- In part 2, change `noise=0.002` to `0.01`. Does BIC still choose two
  peaks? What happens to ΔBIC of the one-peak model?
- In part 2, set `max_extra=4` and look at the BIC column. Where does it
  turn up, and why?
- Run `deconvolve(..., criterion="aic")` on the part 3 spectrum without a
  baseline (`no_baseline`). How many peaks does it give the O–H region?
- Make the pair in part 4 unequal (heights 0.5 and 0.15). Is the small
  band harder to resolve at the same separation?
- In part 3, use the true baseline instead of arPLS
  (`raw.with_y(raw.y - true_baseline)`). Does the spurious component go?

## Design choices

| Choice | Why |
| --- | --- |
| Fit overlapping peaks together | Each band gets its share of the envelope instead of seeing its neighbour as background. On the notebook's C–H pair the areas go from ~20 % low to within 3 %. |
| Regions from overlapping ±2 FWHM spans | The same window as step 5, so isolated peaks get the same fit as before; small regions keep each fit fast and stable. A chain of overlapping peaks becomes one region. |
| One straight-line background per region | As in step 5: absorbs a small leftover baseline. It can't follow a curved one, which is the main failure seen (part 3). |
| BIC by default, AIC available | BIC charges more per parameter, so it adds a peak only on strong evidence. On a noisy spectrum AIC added a peak that isn't there; BIC didn't. |
| Try fewer peaks than detected, and up to `max_extra` more | Detection can both split noise into a peak and miss a hidden band; the criterion judges either way. |
| New peaks start at the residual's largest bump *or* by splitting a peak in two; the best fit wins | Starting from the residual alone failed on merged pairs: the fit got stuck with one big peak and a sliver (area errors ~90 %). Splitting fixed it (errors ~5 %). |
| Same line shape for every peak in a region | Simple and matches step 5; mixed shapes could be added if real bands need them. |
| Fit the unsmoothed spectrum | Same reason as step 5: honest errors. The joint errors cover the truth 70–75 % of the time on the C–H pair. |

## Literature

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Fit the whole envelope as a sum of bands | The established way to separate overlapping IR bands, with known pitfalls: the number of bands, their shapes and the baseline all have to be specified (Maddams 1980; Vandeginste and De Galan 1975). | Standard. |
| Choose the number of peaks with BIC | AIC (Akaike 1974) and BIC (Schwarz 1978) are the standard criteria; BIC has been used to choose the number of peaks in spectral decomposition (Shinotsuka et al. 2020). | Standard. |
| Candidate peaks from detection, the residual or a split | The usual source of candidates is a second-derivative or FSD spectrum. | Simplification. |
| Trust the result only if the model is right | Curve fitting is maximum-likelihood only if the model is correct; baseline or shape errors bias the bands (Lórenz-Fonfría and Padrós 2004). Seen here as the spurious O–H component. | Standard caution. |

Full references:
[LITERATURE.md, step 6](../LITERATURE.md#step-6--deconvolving-overlapping-peaks).

## Check yourself

1. Why do overlapping peaks lose area when fitted one at a time?
2. What does `find_regions` decide, and what would go wrong if every peak
   were put in one region? Or each in its own?
3. Why can't you choose the number of peaks by picking the smallest χ²?
4. Write down AIC and BIC. Which one is stricter for a region of 100
   points, and by how much per parameter?
5. Detection found one peak, but `deconvolve` returned two. How did the
   second one get there?
6. Why does `_add_peak` also try splitting each peak?
7. Below what separation did two equal bands stop being resolved, and why
   does that depend on the noise?
8. In part 3, BIC chose a fourth component in the O–H region. Is BIC
   wrong? What is the component really fitting?
9. When are the joint fit's standard errors trustworthy, and when not?

<details>
<summary>Answers</summary>

1. Each fit sees the neighbour's tail as background (the straight line
   absorbs part of it, or the window cuts it off), and the window is cut
   halfway between the peaks, so each peak's own tail outside the window
   is lost.
2. Which peaks are fitted together. One region for everything means a huge
   fit with many parameters that is slow and easily stuck, and one straight
   line can't serve as background over the whole spectrum. One region per
   peak is just step 5, with the area loss.
3. Every extra peak lowers χ² a little, even if it only fits noise, so the
   smallest χ² would always be the model with the most peaks.
4. AIC = N ln(χ²/N) + 2k, BIC = N ln(χ²/N) + k ln N. With N = 100,
   ln N ≈ 4.6, so BIC charges 4.6 per parameter against 2: about 2.3 times
   stricter. A new pseudo-Voigt peak adds 4 parameters, so it must lower
   N ln(χ²/N) by more than ~18 under BIC, against 8 under AIC.
5. `compare_peak_counts` also tries one peak more than detected
   (`max_extra=1`), starting it at the residual's largest bump or by
   splitting the existing peak in two. BIC then preferred the two-peak fit
   by a large margin.
6. When two peaks merge, the one-peak fit sits in the middle and the
   residual has no single clear bump, so a new peak started from it ends
   up as a sliver. Splitting starts the two peaks roughly where they are.
7. About 0.6 FWHM at signal-to-noise 50, 0.4 FWHM at 250. Closer peaks
   differ from one wider peak by less, and the difference has to stand out
   from the noise for the criterion to pay for four more parameters.
8. Not wrong about the data: arPLS left a curved dip under the O–H band
   that a straight line can't follow, so another component really does
   lower χ² by a lot. It is wrong to read that component as a band. The
   criterion can't tell an artefact from a band; you have to check.
9. When the model is right (right number of peaks and shapes, baseline
   handled): then they cover the truth ~70 % of the time. When peaks are
   very close they are large (honestly so). When the model is wrong,
   e.g. a spurious component or a bad baseline, the values are biased and
   the errors don't show it.

</details>

---

[← Step 5](05_peak_fitting.md) · [← Study guide](README.md)
