# Reproduction: TS-DFM (arXiv:2511.17229)

Paper: "Generating transition states of chemical reactions via
distance-geometry-based flow matching" by Yufei Luo, Xiang Gu, Jian Sun.

This is a reproducibility scaffold, not the authors' original code. The arXiv
source does not include code. The implementation here captures the paper's core
algorithmic path:

1. Convert reactant/product/TS coordinates to pairwise distance matrices.
2. Use `D_TS,0 = (D_R + D_P) / 2` as the flow source.
3. Train a velocity network with OT-CFM target `D_TS,1 - D_TS,0`.
4. Integrate the learned velocity field from `t=0` to `t=1`.
5. Reconstruct Cartesian coordinates from the predicted distance matrix using
   MDS initialization plus weighted distance-geometry optimization.
6. Evaluate RMSD and DMAE.

## Paper Facts Extracted

- Dataset: Transition1X, public at `https://doi.org/10.6084/m9.figshare.19614657.v4`.
- Generalization dataset: RGD1, public at `https://doi.org/10.6084/m9.figshare.21066901.v6`.
- TS-DFM training: 6 update blocks, atom/pair hidden dimension 128, cutoff 20A,
  batch size 32, Adam learning rate `5e-4`, decay `0.8` after 40 stagnant epochs,
  noise scale `sigma=0.1`.
- Coordinate reconstruction: weighted distance loss with `w_ij = 1 / d_ij^2`,
  MDS initialization, LBFGS optimization.
- Main structural metrics: Kabsch-aligned RMSD and DMAE.
- Full energetic replication additionally needs MLIP/DFT/CI-NEB tooling.

## Install

```bash
pip install -e ".[ts-dfm,dev]"
```

## Smoke Test With Synthetic Data

```bash
reproduce-tsdfm make-synthetic --output reproductions/ts_dfm_2511_17229/data/synthetic.jsonl
reproduce-tsdfm train --config reproductions/ts_dfm_2511_17229/configs/smoke.yaml
reproduce-tsdfm eval --config reproductions/ts_dfm_2511_17229/configs/smoke.yaml
```

The smoke configuration is intended to verify the pipeline, not reproduce the
reported benchmark numbers.

Verified locally on 2026-06-01 with Python 3.14:

- `pip install -e ".[ts-dfm,dev]"`
- `reproduce-tsdfm make-synthetic ...`
- `reproduce-tsdfm train --config .../smoke.yaml`
- `reproduce-tsdfm eval --config .../smoke.yaml`
- `pytest`

## Early Experiment Plots

Run a small synthetic experiment matrix and generate SVG plots:

```bash
reproduce-tsdfm early-experiments \
  --output-dir reproductions/ts_dfm_2511_17229/outputs/early \
  --seeds 3,7,11
```

Outputs:

- `early_experiments_summary.json`
- `early_experiments.svg`

The current checked-in early plot is `figures/early_experiments.svg`.

## Data Download And Conversion

Transition1X is a large HDF5 dataset. The DOI resolves to Figshare, but some
networks block direct Figshare access. Try:

```bash
reproduce-tsdfm download transition1x --output reproductions/ts_dfm_2511_17229/data/Transition1x.h5
```

If Figshare returns 403 on your network, download `Transition1x.h5` manually from
`https://doi.org/10.6084/m9.figshare.19614657.v4` and place it at the same path.
In this workspace, direct Figshare download attempts returned `HTTP 403
Forbidden`, while the GitLab metadata repository remained reachable. The
converter and smoke pipeline were therefore tested with synthetic data and a
mock HDF5 file matching the official Transition1X group layout.

Then extract a small JSONL subset:

```bash
reproduce-tsdfm convert-transition1x \
  --input reproductions/ts_dfm_2511_17229/data/Transition1x.h5 \
  --output reproductions/ts_dfm_2511_17229/data/transition1x_sample.jsonl \
  --split train \
  --limit 128
```

## Full Reproduction Plan

1. Download Transition1X and extract reactant/product/TS triplets.
2. Train TS-DFM with the default config.
3. Evaluate RMSD/DMAE against held-out Transition1X reactions.
4. Add React-OT baseline or import baseline predictions if available.
5. Train or obtain the MLIP used for CI-NEB evaluation.
6. Run ASE CI-NEB and Sella/Hessian checks for energetic metrics.
7. Repeat on RGD1 splits: Test-id, Test-ood-size, Test-ood-type.

## Known Gaps

- TSDVNet here is a compact faithful approximation of the described two-branch
  pair/atom network, not an exact reimplementation of every equation.
- Full CI-NEB, Hessian, IRC, and DFT/MLIP experiments are provided as integration
  targets, not executed by the smoke test.
- Dataset converters must be adapted to the exact downloaded Transition1X/RGD1
  file layout if the upstream HDF5 schema changes.
