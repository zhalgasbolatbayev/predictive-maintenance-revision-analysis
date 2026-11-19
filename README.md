# Predictive Maintenance: Revision Analysis (Grouped Validation)

> **Status: draft for co-author review.** These results have not yet been approved for the manuscript.

This repository holds the additional machine-learning analysis made for the manuscript revision. The data come from the Festo MPS 500 Handling station. Everything here is **real collected data**; no synthetic data are used.

The original project (training notebooks, raw recordings, Node-RED flow) is in the main project repository. This repository only adds the revision analysis.

## What question does this analysis answer?

The original models were tested on a random 15% of the rows. Rows from the same recording run end up in both training and testing, and rows from one run are very similar to each other. That can make the accuracy look better than it really is.

So here the models are always tested on **whole recording runs that were not used for training**. This shows how well the model works on a new recording.

## Repository contents

| Path | What it is |
|---|---|
| `revision_analysis_real_data.ipynb` | The revision notebook, already executed on the real data. The first cell ("Execution record") lists exactly what was changed from the template. |
| `real_data/` | The four input files (`forward_AC`, `forward_CB`, `backward_CA`, `backward_BC`), columns `Pressure`, `Time`, `Mechanism`, `Block`. |
| `revision_results/REAL_DATA/` | All outputs written by the notebook (listed below). |
| `block_verification/` | The script that found the recording run for every row, its output, and the training files with the run added. |
| `requirements.txt` | Python packages. |

## The data

Each segment has **16 recording runs**: 4 pressure levels (3.5, 4, 5, 6 bar) × 4 fault conditions (no fault, fault in the first segment, fault in the second segment, both). For each segment, 8 runs are normal and 8 are faulty.

The `Block` column names the run, for example `A_B_3.5_N_Y` = forward direction, 3.5 bar, no fault in A→C, fault in C→B.

**How `Block` was obtained.** It was not guessed. `block_verification/verify_blocks.py` matched every row of the original training files, value by value and in order, to the raw per-condition recordings (the `A_B_*.xlsx` / `B_A_*.xlsx` files in the main repository's `data/dataset_for_ml/`).

| Segment | Rows in original file | Rows found in raw recordings | Rows used here |
|---|---|---|---|
| forward_AC | 424 | 424 | 424 |
| forward_CB | 424 | 422 | **422** |
| backward_CA | 421 | 421 | 421 |
| backward_BC | 421 | 421 | 421 |

- **forward_CB:** 2 rows (6 bar, faulty, 2277 ms and 2279 ms; file lines 371–372) are not in the raw recordings. They repeat lines 368–369. They were left out here, so that every row analysed comes from a real measurement.
- **backward_BC:** the raw recording has one extra pass (3.5 bar, faulty, 4670 ms) that is not in the training file. The training file was used as it is.
- There are no recording-day or session labels, so the grouping unit is the recording run.

To re-run the check (from this folder):

```
python block_verification/verify_blocks.py <folder with the A_B_*/B_A_* xlsx files> <folder with the original four CSVs> <output folder>
```

## Method

- **Validation:** grouped, repeated, nested cross-validation. Groups are recording runs. 3 outer folds × 3 repeats = 9 test folds per segment; 3 inner folds choose the hyperparameters. No run is ever in both training and testing (checked in all folds).
- **Why 3 outer folds, not 5:** with only 16 runs per segment, 4 or 5 folds leave some test folds without any faulty run, and the notebook correctly refuses to run.
- **Fault detection models:** Dummy (always predicts the same class), Logistic regression, Decision tree, Random Forest (RF), Gradient Boosting (GB), SVM, MLP.
- **Pressure estimation models:** the same families as regressors, using **Time only**.
- **Metrics:** accuracy, macro F1, fault recall (share of faults caught), false-alarm rate (share of normal passes flagged as faults); for pressure, MAE and RMSE in bar.
- **Also tested:** which inputs matter (Time only / Pressure only / both); pressure as 4 classes; leaving one pressure level out completely; random-row vs grouped testing.
- Random seed 407. Python 3.13.18, scikit-learn 1.9.1 (full list in `revision_results/REAL_DATA/run_manifest.json`).

## Main results

All values are means over 9 test folds. Full results with standard deviations: `revision_results/REAL_DATA/nested_cv_mean_sd.csv`.

**Fault detection (inputs: Time and Pressure)**

| Segment | RF accuracy | GB accuracy | SVM accuracy | Dummy accuracy | RF fault recall | RF false alarms |
|---|---|---|---|---|---|---|
| forward_AC | 90.9% | 90.6% | 91.6% | 33.0% | 89.0% | 5.3% |
| forward_CB | 62.5% | 60.3% | 50.1% | 44.1% | 84.6% | 40.0% |
| backward_CA | 86.4% | 85.1% | 89.8% | 33.0% | 89.4% | 11.1% |
| backward_BC | 89.2% | 84.2% | 86.4% | 36.1% | 87.7% | 6.8% |

**Random-row vs grouped testing (RF, accuracy)**

| Segment | Random rows | Grouped (new runs) |
|---|---|---|
| forward_AC | 94.2% | 90.9% |
| forward_CB | 89.2% | 62.1% |
| backward_CA | 93.8% | 87.1% |
| backward_BC | 93.4% | 89.7% |

The drop for forward_CB happens because its normal travel times change between recording runs at the same pressure. When a whole run is held out, the model has not seen that run's "normal" level.

**Which inputs matter (RF, macro F1)**

| Segment | Time only | Pressure only | Both |
|---|---|---|---|
| forward_AC | 0.88 | 0.31 | 0.87 |
| forward_CB | 0.57 | 0.45 | 0.62 |
| backward_CA | 0.84 | 0.31 | 0.82 |
| backward_BC | 0.79 | 0.38 | 0.87 |

Time carries almost all the information. Pressure helps clearly only for backward_BC.

**Pressure estimation from Time only (RMSE in bar)**

| Segment | Best model | Best RMSE | Dummy RMSE |
|---|---|---|---|
| forward_AC | Decision tree | 0.61 | 0.86 |
| forward_CB | GB | 0.51 | 0.86 |
| backward_CA | Linear (Ridge) | 0.62 | 0.87 |
| backward_BC | GB | 0.30 | 0.87 |

When a whole pressure level is left out of training, the error (RMSE) is about 0.4–0.7 bar when 4 bar is left out and about 1.1 bar when 5 bar is left out (`leave_pressure_level_out.csv`), so the model does not reliably estimate pressure levels it has not seen.

## What was not done

- **No untouched holdout set.** None exists, so the holdout files in `revision_results/REAL_DATA/` are empty.
- **No data augmentation.** There is no measured estimate of timing noise to base it on.
- **No new live-system tests** (latency, reliability). No new experiments were run.

## Warnings during the run

`warning_log.csv` records 303 warnings: 51 are MLP "did not converge" warnings, and 252 are scikit-learn deprecation notices for SVM. None stopped the run.

## Output files (`revision_results/REAL_DATA/`)

| File | Content |
|---|---|
| `data_audit.csv`, `class_pressure_counts.csv`, `available_group_pressure_class_counts.csv`, `class_distribution.png` | Row counts per segment, class and pressure |
| `input_snapshot.csv`, `locked_partition.csv` | The exact data analysed |
| `outer_split_manifest.csv` | Which run was in which fold |
| `nested_cv_fold_metrics.csv`, `nested_cv_mean_sd.csv`, `nested_cv_predictions.csv` | Results per fold, summary, every prediction (with chosen hyperparameters) |
| `ablation_fold_metrics.csv`, `ablation_paired_differences.csv` | Time / Pressure / Both comparison |
| `random_vs_grouped_diagnostic.csv` | Random-row vs grouped testing |
| `pressure_classifier_fold_metrics.csv`, `leave_pressure_level_out.csv` | Pressure as classes; unseen pressure levels |
| `warning_log.csv`, `run_manifest.json` | Warnings; software versions, settings and input file hashes |

## How to re-run

```
pip install -r requirements.txt
jupyter notebook revision_analysis_real_data.ipynb
```

Run all cells. The notebook reads `real_data/` and rewrites `revision_results/REAL_DATA/`. A full run takes some time because of the nested search.
