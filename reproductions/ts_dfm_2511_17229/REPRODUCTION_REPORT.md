# TS-DFM Reproduction Report

Paper: arXiv:2511.17229, "Generating transition states of chemical reactions via distance-geometry-based flow matching".

Status: partial reproduction scaffold tested locally.

## What Is Reproduced

- Distance-matrix representation for reactant, product, and transition state.
- Flow-matching source construction: `D_TS,0 = (D_R + D_P) / 2`.
- OT-CFM training target: `D_TS,1 - D_TS,0`.
- Numerical integration from `t=0` to `t=1`.
- Cartesian reconstruction from predicted distances using MDS + weighted distance-geometry optimization.
- Kabsch RMSD and DMAE metrics.
- Compact TSDVNet-like velocity model with the same input/output contract as the paper.
- CLI smoke workflow and tests.

## Local Verification

Environment:

- Date: 2026-06-01
- Python: 3.14
- Installed extras: `.[ts-dfm,dev]`

Commands run:

```bash
reproduce-tsdfm make-synthetic \
  --output reproductions/ts_dfm_2511_17229/data/synthetic.jsonl \
  --count 8 \
  --atoms 4

reproduce-tsdfm train \
  --config reproductions/ts_dfm_2511_17229/configs/smoke.yaml

reproduce-tsdfm eval \
  --config reproductions/ts_dfm_2511_17229/configs/smoke.yaml

python -m pytest
```

Observed smoke metrics:

```json
{
  "mean_rmsd": 0.47108421115816074,
  "mean_dmae": 0.017846639900534395
}
```

Full test status after installing reproduction extras:

```text
26 passed
```

## Dataset Status

The official Transition1X metadata repository is reachable:

```text
https://gitlab.com/matschreiner/Transition1x.git
```

The official download script points to:

```text
https://figshare.com/ndownloader/files/36035789
```

In this workspace, direct Figshare download attempts returned:

```text
HTTP Error 403: Forbidden
```

Because of that network-side block, the full Transition1X benchmark was not downloaded here. The converter was tested against a mock HDF5 file matching the official group layout:

```text
<split>/<formula>/<reaction>/{reactant,product,transition_state}/{atomic_numbers,positions}
```

## How To Continue Full Reproduction

1. Download `Transition1x.h5` from the DOI page or another network:

```text
https://doi.org/10.6084/m9.figshare.19614657.v4
```

2. Place it at:

```text
reproductions/ts_dfm_2511_17229/data/Transition1x.h5
```

3. Convert a small subset:

```bash
reproduce-tsdfm convert-transition1x \
  --input reproductions/ts_dfm_2511_17229/data/Transition1x.h5 \
  --output reproductions/ts_dfm_2511_17229/data/transition1x_sample.jsonl \
  --split train \
  --limit 128
```

4. Point a config at the converted JSONL and train.

5. For paper-level numbers, train with `configs/transition1x.yaml`, add React-OT baseline comparison, and run MLIP/ASE CI-NEB/Sella workflows.

## Remaining Gaps

- The current model is a compact TSDVNet-like scaffold, not an exact implementation of every pair/triangular update equation.
- Energetic metrics are not reproduced without MLIP, DFT, CI-NEB, Hessian, and frequency tooling.
- RGD1 generalization splits are documented but not downloaded or converted here.
- React-OT baseline integration remains future work.

## One-Command Smoke

```bash
bash reproductions/ts_dfm_2511_17229/run_smoke.sh
```
