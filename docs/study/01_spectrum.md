# The `Spectrum` object

## The idea

A spectrum is just two arrays (x and y) plus units. `Spectrum` wraps them in
one object that **guarantees they are valid**, so no other code has to check.
It's the "contract" every other module relies on.

## Read

1. `src/spectro/spectrum.py`: the dataclass. Focus on `__init__` (what is
   guaranteed) and `with_y` (how changes are made).
2. `src/spectro/plotting.py`: short; note the inverted x-axis.
3. `src/spectro/loaders.py`: skim. Just know it turns a text file into a
   `Spectrum`.
4. `notebooks/01_spectrum_basics.ipynb`: run it.

## Try

- Create a spectrum with `x` in *decreasing* order and print `s.x`. What
  happened?
- Create one with mismatched lengths and read the error.
- Make a copy with `s.with_y(s.y * 2)` and check that `s.y` didn't change.
- Make a `%transmittance` spectrum, call `.to_absorbance()`, and plot both.
  Which way do the peaks point in each?

## Design choices

| Choice | Why |
| --- | --- |
| One `Spectrum` dataclass used everywhere | Every function speaks the same language; functions can be swapped or chained freely. |
| Sort by x and validate on creation | Check once at the door, so later code (peak finding, integration) can assume clean, ascending data. Bad files fail immediately, with a clear message. |
| Hand-written `__init__` on a dataclass | Callers may pass lists or arrays (`ArrayLike`), but the stored fields are always float arrays (`np.ndarray`). The dataclass-generated `__init__` can't type the two differently, so the type checker would reject `Spectrum(x=[1, 2], ...)`. |
| Never modify in place; return a new spectrum (`with_y`) | You can always compare before and after a processing step, and a bug in one function can't silently corrupt data used elsewhere. |
| Convert to absorbance | Only absorbance is proportional to concentration (Beer–Lambert), so areas and classification features are meaningful. |
| Plain CSV loader for now | No file format is fixed yet. New formats can be added as new loader functions without touching anything else, because they all return a `Spectrum`. |

## Literature

Standard. IUPAC defines absorbance as log₁₀(P₀/P) and states the Beer–Lambert
law in absorbance, which is why we convert. JCAMP-DX, planned for loading real spectra, is
the IUPAC standard file format for IR spectra. Details and sources:
[LITERATURE.md, The `Spectrum` object](../LITERATURE.md#the-spectrum-object).

## Check yourself

1. Why does `Spectrum` sort points by wavenumber?
2. What could go wrong if processing functions modified the spectrum in
   place?
3. Why do we work in absorbance rather than transmittance?
4. If we get data in a new vendor format next month, what needs to change?

<details>
<summary>Answers</summary>

1. Instruments often export from high to low wavenumber. Sorting once means
   every function downstream can assume ascending x (needed for things like
   integration and peak widths) without checking.
2. You'd lose the original, so you can't compare before/after, and if two
   parts of the code share the same spectrum, one function could silently change
   the other's data.
3. Beer–Lambert: absorbance is proportional to concentration, so peak heights
   and areas reflect how much of something is there. Transmittance is not
   linear in concentration.
4. Only a new loader function that returns a `Spectrum`. Nothing downstream
   changes.

</details>

---

[← Study guide](README.md) · [Synthetic spectra →](02_synthetic_data.md)
