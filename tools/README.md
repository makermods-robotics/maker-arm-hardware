# tools

`split_step.py` splits the assembly STEP into one STEP file per unique part and writes `parts.csv`, `guide-part-map.json` and the parts table in the top-level README.

## Setup

You need Python and the OpenCascade Python bindings (`cadquery-ocp`). Tested with Python 3.12 and cadquery-ocp 8.0.1. Put the virtual environment outside the repo, or in `.venv/` (it is git-ignored).

With [uv](https://docs.astral.sh/uv/):

```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python cadquery-ocp
```

Or with pip:

```
python3.12 -m venv .venv
.venv/bin/pip install cadquery-ocp
```

## Run

From the repo root:

```
.venv/bin/python tools/split_step.py
```

Options:

- `--check` re-checks the existing part files against the assembly and writes nothing.
- `--steps-js PATH` also checks that every key of `PARTS` in the assembly guide's `steps.js` has an entry in `guide-part-map.json`.
- A path as the first argument reads a different assembly file.

The script exits with status 1 if any check fails.

## After a new Fusion export

1. Export the assembly from Fusion as STEP (mm) and save it over `assembly/maker-arm-rs02-single-arm.step`.
2. Run the script.
3. If it stops with `no component named ...`, a component was renamed or removed in Fusion. Fix the `product` name in the `PARTS` table at the top of `split_step.py`.
4. If check (d) lists components in no part file, a component was added. Add a row for it to `PARTS`.
5. If a part changes shape, nothing else needs changing: its file is rewritten.
6. Review the git diff. Part files are only rewritten byte-for-byte differently when their geometry or the export time stamp changes.

## How the split works

The assembly is read with OpenCascade's XCAF reader, which keeps the Fusion component names and the assembly tree. Every leaf component is matched by name against the `PARTS` table. Each row of the table is one output file and says which solids of which component go in it:

| `select` | Meaning |
| --- | --- |
| `all` (default) | every solid of the component, one copy per instance |
| `largest` | only the largest solid |
| `others` | every solid except the largest, each one a copy |
| `each` | every solid is a copy, the file holds one |
| `half:+Z`, `half:-Z` | the component is two halves. The two largest solids are the halves, each smaller solid (lettering) joins the half it touches. `+Z` is the half at larger Z in the assembly |

Where the table names several components for one file (the same part under two Fusion names), or a component holds several copies of a part (the MF84ZZ bearings come as back-to-back pairs), the first copy is written and every other copy is checked against it.

Each file holds its part in the Fusion component's own coordinate system, in mm, with the file name as the STEP product name. Colours from the export are kept.

## Checks

After writing, the script reports:

- **(a)** Every part file is re-opened. For every place the part occurs in the assembly, the file is moved to that placement, and its bounding box (size and centre) and volume must match the assembly's solids within 0.1 mm.
- **(b)** Instance and body counts: the quantities in `parts.csv` must account for every solid body in the assembly, and every component instance must be in at least one file.
- **(c)** Every entry in `guide-part-map.json` points at a file that exists (and, with `--steps-js`, every guide key is mapped).
- **(d)** Any assembly component, or any body of one, that ended up in no part file.
