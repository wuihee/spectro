# Literature check

For each part of the pipeline, this file compares the methods we chose with what the
literature does, and gives the sources. Numbers in brackets, e.g. [3], point to the
[reference list](#references) at the end.

How it was checked: by web search in November 2026. Every citation below was confirmed
to exist, with its journal, volume and pages. Authors are given as the sources showed
them (surnames only where initials weren't confirmed). For most papers only the
abstract or index entry was read, not the full text; where a claim rests on a secondary
source (a review, a later paper, or software documentation), the row says so.

Verdicts:

- **Standard**: what the literature does.
- **Standard, tuned**: a standard method with a setting we chose by testing; the
  setting differs from common defaults.
- **Simplification**: a simpler version of the standard method, fine for now, with
  a stated limit.
- **Not a method choice**: a convention or implementation detail; no source needed.

---

## The `Spectrum` object

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Analyse in absorbance, converting with A = −log₁₀ T | IUPAC defines (decadic) absorbance as log₁₀(P₀/P), and the Beer–Lambert law as A = εcl: absorbance, not transmittance, is proportional to concentration [1], [2]. | Standard |
| Plain CSV loader now; JCAMP-DX planned | JCAMP-DX is the IUPAC standard format for exchanging IR spectra between instruments and software [3], [4]. | Standard plan |
| Wavenumber in cm⁻¹, plotted high to low | The usual convention for IR spectra. | Not a method choice |
| Sort points by wavenumber; clip T at 10⁻⁶ before the log | Implementation details. | Not a method choice |

Note for real spectra: IUPAC states that the Beer–Lambert law holds only when the
instrument's spectral bandwidth is narrow compared with the bands [2]. Very strong
(saturated) bands break it, so measured spectra need checking for them.

---

## Synthetic spectra

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Test methods on synthetic spectra with known peaks | Method papers do the same. The arPLS paper compares baseline methods on simulated as well as measured spectra [5]. An adaptive Savitzky–Golay study uses simulated signals with Gaussian, Lorentzian and Voigt profiles [6]. | Standard |
| Gaussian, Lorentzian and pseudo-Voigt line shapes | IR curve fitting uses Gaussian–Lorentzian mixtures, or the Voigt profile when the two widths are allowed to differ. Gaussian is usual for solids, Lorentzian for gases (instrument maker's application note, a secondary source [7]). | Standard |
| Pseudo-Voigt as η·L + (1 − η)·G with one shared FWHM | The pseudo-Voigt approximates the Voigt profile. The Thompson–Cox–Hastings version computes η and the FWHM from the Gaussian and Lorentzian widths of a true Voigt [8]. Ida et al. give a more accurate extended version [9]. Our η is a free shape parameter, as in Gaussian–Lorentzian curve fitting. | Simplification |
| Symmetric bands only | Condensed-phase bands can be asymmetric. Fitting them with a symmetric or naively skewed pseudo-Voigt can shift the fitted center away from the band maximum [10]. | Simplification; check on real spectra |
| White Gaussian noise and a polynomial baseline | Simple, common models. Real noise and baselines are more varied (water vapour, CO₂, scattering); still to be tested on measured spectra. | Simplification |
| Peaks described by center, FWHM and height; area computed | The usual band parameters. The area factors (√(π / 4 ln 2) for Gaussian, π/2 for Lorentzian) are exact integrals. | Standard |

---

## Preprocessing

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| arPLS baseline by default (pybaselines) | arPLS [5] gave a lower error than AsLS and airPLS on simulated and measured Raman spectra and was less sensitive to the choice of λ. Its weights adapt to an iteratively estimated noise level. AsLS [11] uses one fixed asymmetry and can sit too high or low when there is noise [5]. Both build on Eilers' penalised least-squares (Whittaker) smoother [12]. Our own comparison on synthetic spectra agreed. | Standard |
| arPLS `lam = 1e7` | pybaselines' default for arPLS is 1e5 [13]. Other implementations suggest searching by orders of magnitude, about 10⁵–10⁸ [14] or 10²–10⁹ [15], and tuning it to the data. We set 1e7 by testing on our 1801-point grid. | Standard, tuned; recheck on real data |
| AsLS `p = 0.01` | Suggested values are 0.001–0.1 [14], [15]; pybaselines' default is 0.01 [13]. | Standard |
| Savitzky–Golay smoothing | The standard polynomial smoothing filter [16], listed among the most common spectral pre-processing techniques [17]. Alternatives exist: the Whittaker smoother [12], and a recent paper arguing for replacing Savitzky–Golay filters [18]. | Standard |
| Window below the narrowest FWHM in points; default 11 points (20 cm⁻¹, 0.8 × a 25 cm⁻¹ band) with a cubic polynomial | Edwards and Willson recommend a cubic smoothing range of about 0.7 × the FWHM of the narrowest band, to keep resolution [19]. Our default sits just above that; our rule ("below the FWHM") is slightly looser. | Standard; docstring now cites 0.7 × FWHM |
| Normalisation: max, area, vector, SNV | SNV was introduced to remove multiplicative scatter effects, one spectrum at a time [20]. It is one of the two main families of pre-processing in the standard NIR review [17]. Max, area and vector normalisation are common simple options; we didn't check them against individual sources. | Standard |
| Order: baseline → smooth → normalise | Normalising last is the consensus. A Raman pre-processing guide lists "normalizing before baseline correction" as a common mistake [21]. Where smoothing goes varies: one FTIR pipeline uses baseline → denoise → normalise [22], and some studies smooth first. Both of these are software documentation, a weaker kind of source. The FTIR protocol of Baker et al. sets the overall chain: quality control → pre-processing → feature extraction → classification [23]. | Standard (normalise last); baseline/smooth order is a choice |

---

## Peak detection

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Smooth, find local maxima, keep those above a threshold | The basic textbook method for spectra and chromatograms. | Standard |
| Threshold as a multiple of the noise (5σ) | Detection limits are set the same way: IUPAC's detection limit is commonly the blank plus 3σ of the blank [24]. Our 5σ was set by testing (4σ already gave no false peaks). | Standard idea, tuned |
| Robust noise from the median absolute deviation of second differences | The MAD is a standard robust estimate of spread. Using second differences relies on peaks being smooth. | Standard |
| Center from a parabola through the top three points | Common sub-sample peak interpolation. | Standard |
| Minima of the Savitzky–Golay second derivative | The usual way to locate overlapping IR bands, e.g. the components of the protein amide I band [25]. The resolution gained depends on point spacing, window, polynomial order and band shape; a small window and high polynomial order maximise it, at a cost in noise [26]. Derivatives are one of the two main pre-processing families in the NIR review [17]. | Standard |
| Not used: continuous wavelet transform (CWT) | Matches the spectrum against peak-shaped wavelets at many widths [27]. Developed for mass spectrometry. | Could be compared later |
| Not used: Fourier self-deconvolution (FSD) | Narrows bands mathematically before finding peaks [28]. Classic in IR, but noise limits how far bands can be narrowed. | Peak fitting and deconvolution cover the same need |

---

## Peak fitting

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Nonlinear least-squares fit of a line shape to each band (Levenberg–Marquardt, via lmfit) | Band fitting by nonlinear least squares is the established method for measuring IR band positions, widths and intensities [30]. A recent IR band tool fits pseudo-Voigt components with Levenberg–Marquardt in lmfit, as we do [33]. | Standard |
| Gaussian, Lorentzian or pseudo-Voigt (free η) | The three standard profiles; the pseudo-Voigt with a mixing parameter η is the usual cheap stand-in for a Voigt [8], [33]. No true Voigt profile. | Standard; simplification (no Voigt) |
| Starting values from detection, center bounded to the window, height ≥ 0, 0 ≤ η ≤ 1 | Good starting values and physical bounds are standard practice; Maddams stresses that fits must stay physically plausible and be checked visually, not only by a statistic [30]. | Standard |
| Straight-line background in each window | The baseline form is one of the things a fit has to specify [30]. A local linear term absorbs leftover baseline and neighbours' tails. | Standard |
| One peak per window, window ±2 FWHM cut halfway to neighbours | A simplification: overlapping bands should be fitted together [30]. On synthetic data the overlapping C–H pair loses 7–30 % of its area. | Simplification; fixed by deconvolution |
| Fit the unsmoothed (baseline-corrected) spectrum | Smoothing makes neighbouring points share noise; fits to such data underestimate parameter uncertainties [31]. Our test agrees: errors cover the truth 72 % of the time on raw data (68 % expected) and 1 % on smoothed data, and smoothing biases the height about 2 % low. | Standard (and tested) |
| Standard errors from the covariance matrix scaled by reduced χ² | lmfit's default (`scale_covar=True`): with unknown noise, the scale is taken from the residuals [32]. The covariance estimate assumes independent noise and a correct model; it says nothing about systematic error. | Standard, with stated limits |
| Area from the fitted height, FWHM and η, with propagated error | lmfit computes errors of derived parameters from the covariance matrix [29]. | Standard |

---

## Deconvolving overlapping peaks

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Fit overlapping bands together, as a sum of line shapes on one background | Curve fitting of the whole envelope is the established way to separate overlapping IR bands; both classic reviews stress that the number, positions, shapes and widths of the components and the baseline form all have to be specified, and that the method has many pitfalls [30], [34]. | Standard |
| Group peaks into regions where their ±2 FWHM spans overlap | A practical choice so each fit stays small; the literature fits "the band envelope" without a fixed rule for its limits. | Not a method choice |
| Choose the number of peaks with an information criterion (BIC by default, AIC available) | AIC [35] and BIC [36] are the standard criteria for choosing a model's size. BIC has been used to choose the number of peaks in automatic spectral decomposition [38]; an ice-band study with JWST used AIC the same way [39]. lmfit computes both from χ² [32]. | Standard |
| BIC rather than AIC by default | BIC charges ln N per parameter instead of 2, so it adds components only on stronger evidence; ΔBIC above 6–10 is "strong" to "very strong" on Kass and Raftery's scale [37]. Our tests agree: on a noisy spectrum without baseline problems AIC added a fourth, non-existent peak where BIC kept the right three. | Standard (and tested) |
| Candidate models from detection, plus extra peaks at the largest residual bump or by splitting a peak | The literature proposes components from resolution-enhanced spectra (second derivative or FSD) before fitting [25], [38]. Our residual and split starts are a simple search over starting values; the criterion then judges them. `detect_peaks_derivative` can supply the starting table instead. | Simplification |
| Standard errors from the joint fit | As in peak fitting. Strongly overlapping peaks are correlated, and the errors grow to show it. The fit is maximum-likelihood only when the model is correct and the noise random; model error and systematic data error (e.g. leftover baseline) bias the bands in ways the errors don't show [40]. Our test: joint errors cover the truth 70–75 % of the time when the model is right; a curved baseline leftover made BIC add a spurious wide component. | Standard, with stated limits |
| Not used: Bayesian spectral deconvolution with marginal likelihood | Estimates the number of peaks and the noise together by sampling, avoiding both over- and under-fitting [41]. More robust, much slower. | Could be compared later |

---

## Deviations and follow-ups

1. **arPLS `lam` (preprocessing):** 1e7 against a library default of 1e5. It was
   tuned on synthetic data; check again on real spectra.
2. **Pseudo-Voigt (synthetic spectra, peak fitting):** a shared-FWHM mixture, not a
   TCH-style Voigt approximation, and symmetric. Fine for synthetic data and as a
   fitting model; check real bands for asymmetry.
3. **Smoothing window (preprocessing):** the literature optimum is ~0.7 × FWHM [19]; the
   docstring rule is now stated that way.
4. **Pre-processing order (preprocessing):** normalising last is well supported;
   whether to smooth before or after baseline removal is a choice. Revisit if real
   data show arPLS struggling with noise.
5. **Thresholds (peak detection):** 5σ and 12σ were set by testing on synthetic
   noise, not taken from the literature. Check false-positive rates on real spectra.
6. **One peak per fit (peak fitting):** overlapping bands lose area when fitted
   alone, and their reported errors don't show it. Deconvolution fits them together.
7. **No true Voigt (peak fitting):** only Gaussian, Lorentzian and pseudo-Voigt. Add
   lmfit's Voigt if real bands need it.
8. **Candidate peaks (deconvolution):** extra components are proposed from the
   residual or by splitting a peak, not from a resolution-enhanced spectrum as is
   usual. Compare with starting from `detect_peaks_derivative` on real low-noise data.
9. **Baseline leftover and model choice (deconvolution):** at noise σ = 0.01, arPLS
   leaves a curved dip of up to ~0.045 under the broad O–H band; the straight-line
   background can't follow it, and BIC adds a wide spurious component that takes
   9–22 % of the C–H areas. Revisit baseline removal on noisy spectra (arPLS
   settings) or allow a curved region background, and check on real spectra.

---

## References

1. IUPAC Compendium of Chemical Terminology (Gold Book), "absorbance, A".
   <https://goldbook.iupac.org/terms/view/A00028>
2. IUPAC Gold Book, "Beer–Lambert law (Beer–Lambert–Bouguer law)".
   <https://goldbook.iupac.org/terms/view/B00626>
3. McDonald and Wilks, "JCAMP-DX: A standard form for exchange of infrared
   spectra in computer readable form," *Appl. Spectrosc.* 42, 151–162 (1988).
   doi:10.1366/0003702884428734.
   [IUPAC copy](https://iupac.org/wp-content/uploads/2021/08/JCAMP-DX_IR_1988.pdf)
4. Grasselli, IUPAC recommendations on JCAMP-DX, *Pure Appl. Chem.* 63, 1781–1792
   (1991).
   [PDF](https://joomla.iupac.org/publications/pac/1991/pdf/6312x1781.pdf)
5. Baek et al., "Baseline correction using
   asymmetrically reweighted penalized least squares smoothing," *Analyst* 140, 250–257
   (2015). doi:10.1039/C4AN01061B.
   [RSC](https://pubs.rsc.org/en/content/articlehtml/2015/an/c4an01061b)
6. Li, Deng, Li and Yu, "Real-time infrared gas detection based on an
   adaptive Savitzky–Golay algorithm," *Appl. Phys. B* 120, 207–216 (2015).
   doi:10.1007/s00340-015-6123-z
7. Thermo Fisher Scientific, application note AN50733 on spectral curve fitting.
   [PDF](https://assets.thermofisher.com/TFS-Assets/CAD/Application-Notes/AN50733_E.pdf)
   (instrument maker's note, secondary source)
8. Thompson, Cox and Hastings, "Rietveld refinement of Debye–Scherrer
   synchrotron X-ray data from Al₂O₃," *J. Appl. Cryst.* 20, 79–83 (1987).
9. Ida, Ando and Toraya, "Extended pseudo-Voigt function for approximating the
   Voigt profile," *J. Appl. Cryst.* 33, 1311–1316 (2000).
10. "Asymmetric fitting function for condensed-phase Raman spectroscopy," arXiv:1804.06083.
    <https://arxiv.org/abs/1804.06083>
11. Eilers and Boelens, "Baseline correction with asymmetric least
    squares smoothing," Leiden University Medical Centre report (2005, unpublished).
12. P. H. C. Eilers, "A perfect smoother," *Anal. Chem.* 75, 3631–3636 (2003).
    doi:10.1021/ac034173t
13. pybaselines documentation, `Baseline.arpls` and `Baseline.asls`.
    <https://pybaselines.readthedocs.io/en/latest/generated/api/pybaselines.Baseline.arpls.html>
14. R package `ptw`, documentation of `asysm`.
    <https://rdrr.io/pkg/ptw/man/asysm.html>
15. WaveMetrics, "Asymmetric least squares smoothing" (Igor Pro code snippet).
    <https://www.wavemetrics.com/node/7936>
16. Savitzky and Golay, "Smoothing and differentiation of data by simplified
    least squares procedures," *Anal. Chem.* 36, 1627–1639 (1964).
17. Å. Rinnan, F. van den Berg and S. B. Engelsen, "Review of the most common
    pre-processing techniques for near-infrared spectra," *TrAC Trends Anal. Chem.* 28,
    1201–1222 (2009). doi:10.1016/j.trac.2009.07.007
18. "Why and how Savitzky–Golay filters should be replaced" (2022).
    <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9026279/>
19. T. H. Edwards and P. D. Willson, "Digital least squares smoothing of spectra,"
    *Appl. Spectrosc.* 28, 541–545 (1974). doi:10.1366/000370274774332065
20. Barnes, Dhanoa and Lister, "Standard normal variate transformation
    and de-trending of near-infrared diffuse reflectance spectra," *Appl. Spectrosc.* 43,
    772–777 (1989). doi:10.1366/0003702894202201
21. Raman Spectroscopy Analysis Application, "Preprocessing guide" (software
    documentation).
    <https://raman-spectroscopy-analysis-application.readthedocs.io/en/latest/user-guide/preprocessing.html>
22. xpectrass documentation (FTIR pre-processing pipeline; software documentation).
    <https://xpectrass.readthedocs.io/en/latest/api/utils.html>
23. M. J. Baker et al., "Using Fourier transform IR spectroscopy to analyze biological
    materials," *Nat. Protoc.* 9, 1771–1791 (2014). doi:10.1038/nprot.2014.110.
    [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4480339)
24. D. Harvey, *Analytical Chemistry 2.1*, section 4.7, "Detection limits" (LibreTexts).
    <https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Analytical_Chemistry_2.1_by_David_Harvey/Analytical_Chemistry_2.1_(Harvey)/04%3A_Evaluating_Analytical_Data/4.07%3A_Detection_Limits>
25. Susi and Byler, "Resolution-enhanced Fourier transform infrared
    spectroscopy of enzymes," *Methods Enzymol.* 130, 290–311 (1986).
26. M. A. Czarnecki, "Resolution enhancement in second-derivative spectra," *Appl.
    Spectrosc.* 69, 67–74 (2015). doi:10.1366/14-07568
27. P. Du, W. A. Kibbe and S. M. Lin, "Improved peak detection in mass spectrum by
    incorporating continuous wavelet transform-based pattern matching,"
    *Bioinformatics* 22, 2059–2065 (2006). doi:10.1093/bioinformatics/btl355
28. Kauppinen, Moffatt, Mantsch and Cameron, "Fourier
    self-deconvolution: a method for resolving intrinsically overlapped bands," *Appl.
    Spectrosc.* 35, 271–276 (1981). doi:10.1366/0003702814732634
29. M. Newville et al., "LMFIT: Non-Linear Least-Squares Minimization and Curve-Fitting
    for Python," version 1.3.4, Zenodo (2025). <https://zenodo.org/record/598352>;
    documentation <https://lmfit.github.io/lmfit-py/>
30. W. F. Maddams, "The scope and limitations of curve fitting," *Appl. Spectrosc.* 34,
    245–267 (1980). doi:10.1366/0003702804730312
31. "Probabilistic denoising for reliable signal extraction in spectroscopy,"
    arXiv:2605.07819 (2026). <https://arxiv.org/abs/2605.07819>
32. lmfit documentation, "Performing fits and analyzing outputs" (`scale_covar`,
    `stderr`, reduced chi-square). <https://lmfit.github.io/lmfit-py/fitting.html>
    (checked through a mirror of the docs)
33. "CosmicPAH-IRDB: A web application for including anharmonicity in simulated PAH
    spectra for astrophysics," arXiv:2609.01696 (2026).
    <https://arxiv.org/abs/2609.01696>
34. B. G. M. Vandeginste and L. De Galan, "Critical evaluation of curve fitting in
    infrared spectrometry," *Anal. Chem.* 47, 2124–2132 (1975). doi:10.1021/ac60363a029
    (index entry only; full text not read)
35. H. Akaike, "A new look at the statistical model identification," *IEEE Trans. Autom.
    Control* 19, 716–723 (1974). doi:10.1109/TAC.1974.1100705
36. G. Schwarz, "Estimating the dimension of a model," *Ann. Stat.* 6, 461–464 (1978).
    doi:10.1214/aos/1176344136
37. R. E. Kass and A. E. Raftery, "Bayes factors," *J. Am. Stat. Assoc.* 90, 773–795
    (1995). <https://sites.stat.washington.edu/courses/stat527/s13/readings/KassRaftery_jasa1995.pdf>
    (scale checked through secondary sources)
38. H. Shinotsuka, K. Nagata, H. Yoshikawa, Y. Mototake, H. Shouno and M. Okada,
    "Development of spectral decomposition based on Bayesian information criterion with
    estimation of confidence interval," *Sci. Technol. Adv. Mater.* 21, 402–419 (2020).
    doi:10.1080/14686996.2020.1773210 (XPS spectra)
39. "Ice inventory towards the protostar Ced 110 IRS4 observed with the James Webb Space
    Telescope," arXiv:2411.19651. <https://arxiv.org/abs/2411.19651> (checked through
    a search summary of the paper only)
40. V. A. Lórenz-Fonfría and E. Padrós, "Curve-fitting overlapped bands: quantification
    and improvement of curve-fitting robustness in the presence of errors in the model
    and in the data," *Analyst* 129, 1243–1250 (2004). doi:10.1039/B406581F
41. S. Tokuda, K. Nagata and M. Okada, "Simultaneous estimation of noise variance and
    number of peaks in Bayesian spectral deconvolution," arXiv:1607.07590.
    <https://arxiv.org/abs/1607.07590>
