# Handoff: modelling workstreams

Two parallel tracks start from here: **LightGBM** and **combined spatial + attribute donors**. Both use the same data, folds and scoring, so their results can go into one comparison table.

## Where things stand

| Piece | Where | Status |
| --- | --- | --- |
| Raw subset (all 1,903 gauges, unfiltered) | `data/processed/timeseries/`, `attributes.parquet` | committed |
| Quality filter, splits, static features, daily table | `notebooks/01_preprocessing.ipynb` | committed; run it once to build `data/features/` (git-ignored, ~2 min) |
| EDA | `notebooks/02_caravan_eda.ipynb` | committed |
| kNN donor baseline | `notebooks/03_knn_donors.ipynb`, `data/results/knn_donor_scores.csv` | committed |

**Data in scope:** 667 US and 541 AUS basins (GB excluded). Train on water years 1986-10 to 2003-09 and test on 2004-10 to 2014-09, with a one-year gap between them.

**Folds:** 5 spatially blocked folds. Blocks are up to 300 km across, plus a 100 km buffer: training basins that close to a test basin are dropped for that fold. `data/processed/splits/fold_roles.csv` gives each basin's role (`train`, `test` or `buffer`) in each fold.

**Loading helpers:** `load_fold`, `load_static` and `load_daily`, in section 9 of `01_preprocessing.ipynb`. Moving them to a `src/` module is a good first task for whoever needs them first.

## Ground rules (both tracks)

1. **Fit only on the fold's `train` basins.** That includes scalers, PCA, k-means, model fits and choosing donors. `buffer` basins are never used.
2. **Never tune on the test basins.** Choose k, α or hyperparameters inside each fold by leaving out one *block* of training basins at a time (the `block` column in `splits/basins.csv`), using training years only. Then score that single setting on the test basins.
3. **Score each test basin over the test years** with NSE, KGE (plus its parts r, α, β) and log-NSE. Report the median across basins, and compare methods basin by basin. The scoring functions are in Step 2 of `03_knn_donors.ipynb`; moving them to `src/metrics.py` would keep everyone consistent.
4. **Save per-basin scores** to `data/results/<method>_scores.csv`, using the same columns as `knn_donor_scores.csv`: `fold, gauge_id, region`, your setting columns, then `nse, log_nse, kge, r, alpha, beta`.

## Benchmarks to beat (kNN donors, median over test basins)

| Distance space | k | NSE | KGE | log-NSE |
| --- | --- | --- | --- | --- |
| spatial | 5 | 0.02 | 0.15 | 0.12 |
| spatial | 20 | 0.06 | 0.11 | 0.01 |
| attributes (PCA, 10 components) | 20 | 0.04 | 0.14 | 0.12 |
| attributes (13 curated) | 20 | −0.12 | −0.05 | −0.31 |

These rows are an ablation, not tuned results. Skill is higher in the US (NSE about 0.15–0.18 at k = 20) than in AUS (negative).

**Why so low:** with random basin folds, the same spatial donors score a median NSE of 0.44–0.54. Most of the apparent skill in a random-fold evaluation comes from having a gauge within about 30 km, which the blocked design deliberately removes (Step 7 of notebook 03).

## Track 1: LightGBM

**Goal:** predict daily `log_streamflow` from weather windows plus basin information, and test whether cluster ID helps (feasibility review, issue 1).

- **Inputs:** `data/features/daily_<subset>.parquet`, which has the forcings, 7/30/90/365-day windows and day of year, joined on `gauge_id` to `data/processed/features/static_attributes.parquet`. Feature groups are in `feature_groups.json`.
- **Arms to compare:**
  1. no basin information (weather only)
  2. k-means cluster ID (k swept over 3–4 values, clustering fit per fold)
  3. raw static attributes
- **Size:** about 870 training basins × 6,200 days is roughly 5.4 million rows. Joining all 189 static columns won't fit in memory comfortably. Subsample days (e.g. 20% at random), or use the curated or PCA static features.
- **Target:** `log_streamflow` = log(q + 0.01). Back-transform before computing NSE and KGE, and note that the back-transform biases the mean low (review, minor points).
- **Later:**
  - the training-basin-count experiment (25/50/100/all training basins, test basins fixed)
  - a neighbour-feature arm: the kNN donors' mean *training-period* flow as a feature, which gives the model neighbour information without seeing test-year flow
- **Known data issues:**
  - ERA5-Land PET is about 5× too high (it affects `aridity_train`'s absolute level, not how basins rank).
  - `cls_cl_smj`, `tec_cl_smj` and `fec_cl_smj` have dozens of classes and may act as near-identifiers for individual basins.

## Track 2: combined spatial + attribute donors

**Goal:** test whether mixing "nearby" with "looks similar" picks better donors than either alone (Oudin et al., 2008).

- **Start from** `03_knn_donors.ipynb`. Steps 3–5 already have the distance functions, donor weighting and scoring loop.
- **Combined distance:** d = α · d_attr + (1 − α) · d_space. Rescale both parts first so they're comparable, e.g. divide each by its median over the fold's train-to-train pairs, or convert to ranks. Sweep α from 0 to 1 in steps of 0.25, for k = 1–20.
- **Choosing α and k:** leave out one block at a time within the training basins, as in ground rule 2. This needs **training-period** flow; notebook 03 currently loads only the test period, so add a second wide table for training years.
- **Revisit the curated attribute list.** It currently does worse than PCA. In Step 4's example, a Maine river borrows from Michigan and Wisconsin basins. Ideas:
  - weight features (e.g. by LightGBM importance, which links the two tracks)
  - drop terrain features that don't track flow
  - log-transform skewed attributes before standardising
- **Nice to have:** k-means donors (all training basins in the test basin's cluster), which is the kNN vs k-means comparison the midway feedback asked for.

## Open decisions for the group

- **Concurrent donor flow.** Donor methods use donors' observed *test-year* flow, while LightGBM doesn't see it. Keep both, and state the difference plainly in the report.
- **Excluded attributes.** `ria_ha_usu`, `riv_tc_usu` and `dor_pc_pva` were excluded as derived from modelled discharge. That was a cautious call and could be reversed.
- **Report text.** `docs/md/methods.md` and `preliminary-results.md` still say 1,760 basins and a 1981–2014 missingness window.
