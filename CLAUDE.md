# spectro

Python tool for analyzing IR spectra. The plan, decisions and progress live
in [docs/PLAN.md](docs/PLAN.md); update it at the end of every step.

## Workflow

- Build one step at a time, then stop for review. Don't start the next step
  until the user says so.
- Each step adds one module in `src/spectro/`, one test file in `tests/` and
  one numbered demo notebook in `notebooks/` (e.g. `02_synthetic_data.ipynb`).
  Visuals and demos go in notebooks, not scripts.
- At the end of each step, add a section for it to [docs/STUDY.md](docs/STUDY.md),
  following the same layout (idea, read, try, design choices, check yourself
  with folded answers) and update the "ready to move on" checklist and the
  professor summary. The user is learning the code and will explain the
  design choices to their professor.
- Add a dependency only when the step's code imports it (`uv add <pkg>`,
  or `uv add --dev <pkg>` for tooling).

## Commands

```bash
uv run pytest                 # tests
uv run ruff format            # format (src, tests and notebooks)
uv run ruff check --fix       # lint, including docstring rules
uv run pyright                # type check src and tests (same engine as Pylance)
uv run pymarkdown scan *.md docs/*.md   # lint markdown docs
uv run jupyter lab            # open notebooks
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/<nb>.ipynb
```

Before finishing a step, run all five checks: `ruff format`, `ruff check`,
`pyright`, `pymarkdown scan`, `pytest`. Then execute the new notebook to make sure it
runs top to bottom.

## Code style

- Ruff handles formatting and linting; its settings are in `pyproject.toml`
  (88-character lines, import sorting, pydocstyle with the NumPy convention).
- Use type hints on every function signature, and `from __future__ import
  annotations` at the top of each module. Pyright checks them; its settings
  are in `pyproject.toml`.
- Make type hints match the docstrings. Inputs documented as `array_like`
  are typed `ArrayLike` (from `numpy.typing`) and converted with
  `np.asarray`; values a function returns or stores are typed `np.ndarray`.
  Parameters limited to a few strings use a `Literal` alias (e.g.
  `NormMethod`).
- When a test passes a deliberately invalid value, silence pyright on that
  line only: `# pyright: ignore[reportArgumentType]`.
- Keep functions short and plainly named. Processing functions take a
  `Spectrum` and return a new one (via `Spectrum.with_y`); they never modify
  their input.

## Documentation standard

Docstrings follow the **NumPy docstring style**
(https://numpydoc.readthedocs.io/en/latest/format.html). `ruff check`
enforces the structure.

**Every module** starts with a one-line docstring saying what it is for,
optionally followed by a short paragraph of context.

**Public functions, classes and methods** (no leading underscore) have:

1. A one-line summary in the imperative mood ("Load a file", not "Loads a
   file"), ending with a period.
2. Optionally, a short paragraph on *why* or on the science, e.g. why
   absorbance rather than transmittance.
3. These sections, in this order, each included only when it applies:
   `Parameters`, `Returns`, `Raises`, `Notes`, `References`, `Examples`.

```python
def load_csv(path: str | Path, y_unit: str = "absorbance") -> Spectrum:
    """Load a delimited text file into a `Spectrum`.

    Parameters
    ----------
    path : str or Path
        File to read.
    y_unit : str, default "absorbance"
        Unit of the signal column.

    Returns
    -------
    Spectrum
        The loaded spectrum.
    """
```

Conventions inside docstrings:

- Parameter types are written in words as numpydoc does (`str or Path`,
  `array_like`, `np.ndarray`, `int, optional`, `float, default 0.5`).
- Give physical units wherever a value has one (cm⁻¹, absorbance units).
- Refer to other parameters and objects in single backticks (`x`, `Spectrum`).
  Use double backticks for literal code or values (``metadata["source"]``).
- Put formulas and line-shape definitions in `Notes`, and cite papers or
  method docs in `References`.
- **Dataclasses** document their fields under `Parameters` in the class
  docstring.

**Private helpers** (leading underscore) need only a one-line imperative
summary.

**Magic methods** such as `__len__` need no docstring.

**Tests** need no docstrings; the test name should say what it checks.

**Comments** explain *why*, never *what*. Use them mainly where the science
isn't obvious from the code.

**Notebooks** are documented with markdown cells and organised around the
notebook's goal, broken into small parts:

- The title cell is `# NN · Topic`. It states the goal in one sentence,
  gives a numbered list of the parts, and names the source files covered.
- A `## Setup` section holds all the imports.
- Each part gets its own `## N. <part>` header, matching the list. The header
  states what the part shows, e.g. "Points are kept in wavenumber order".
  A sentence or two explains why it matters, then come the code cells.
- Keep notebooks short and focused on **how to use** the code: the main
  calls and their visual results. Leave out edge cases, validation and
  error handling; the tests cover those.

**Markdown files** (`README.md`, `CLAUDE.md`, `docs/*.md`) must pass
`pymarkdown scan`; its settings are in `pyproject.toml`:

- Wrap prose at 88 characters, like the code. Table rows and code blocks are
  exempt.
- Give every fenced code block a language (`bash`, `python`, or `text` for
  diagrams).
- Write table separators with spaces: `| --- | --- |`.
- Inline HTML is limited to `<details>` and `<summary>` (the folded answers
  in `STUDY.md`).
