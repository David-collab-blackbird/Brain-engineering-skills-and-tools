## 4. Integration experiments: write gate, certified recall, router sets (`scripts/conformal.py`)

The pool is split by group: the first 2/3 fits the temperature or head, the last 1/3 calibrates thresholds. Test =
world s2. These are sandbox numbers on synthetic, templated text: they compare approaches and are not estimates for
the real brain.

### 4.1 J1 write gate (maker–checker): how much can be auto-accepted, with how many errors?
**Certification is label-hungry.** Learn-then-Test with a one-sided 95% Clopper–Pearson bound needs **≥ 59
accepted, audited records with zero errors** to certify ε = 5%, and **≥ 149** for ε = 2% (93 / 236 with one error).
With 334–397 calibration records (one third of the pool) at 50% error prevalence, nothing certifies at ε ≤ 5% and only one arm certifies
at 10% (bge + linear head: automation 0.50, realised error 9.0% at a 13% bound). This is the honest result: the seeded
set is too error-dense and too small for a strict certificate.

**At a realistic 10% error prevalence** (errors subsampled in calibration and test, 30 draws):
| Arm | ε | Certified (share of draws) | Automation | True records auto-accepted | Realised error among accepted | Catch: numeric / value swap / entity swap |
|---|---|---|---|---|---|---|
| Laya + temperature | 5% | 0.73 | 0.47 | 0.51 | **1.6%** | 0.97 / 0.94 / 0.94 |
| Laya + temperature, hybrid (deterministic value check first) | 5% | 0.73 | 0.44 | 0.49 | **1.1%** | 1.00 / 1.00 / 0.91 |
| Laya + linear head | 5% | 0.50 | 0.40 | 0.44 | 1.4% | 0.97 / 0.98 / 0.95 |
| NLI-xsmall + temperature | 5% | 0.30 | 0.13 | 0.14 | 1.8% | 1.00 / 0.99 / 0.97 |
| bge-reranker + temperature, hybrid | 5% | 0.53 | 0.48 | 0.52 | 2.2% | 1.00 / 1.00 / 0.86 |
| Julia-1 + linear head, hybrid | 5% | 0.23 | 0.11 | 0.12 | 1.0% | 1.00 / 1.00 / 0.98 |
| any arm | 2% | 0.00 | 0 | 0 | – | – |

(The attribute-swap catch rate is undefined at 10% prevalence in most draws; see the 50% table in `tables.md`.)

**Risk–coverage without certification** (test set, error among the top-q most confident "supported" calls):
| Arm | 50% error prevalence: top 10% / 25% / 50% | 10% error prevalence: top 10% / 25% / 50% |
|---|---|---|
| Laya + temperature (hybrid) | 0.000 / 0.040 / 0.105 | 0.000 / 0.000 / 0.005 |
| Laya + linear head (hybrid) | 0.000 / 0.020 / 0.085 | 0.000 / 0.002 / 0.003 |
| NLI-xsmall + linear head | 0.025 / 0.020 / 0.085 | 0.005 / 0.002 / 0.004 |
| bge-reranker + temperature (hybrid) | 0.000 / 0.040 / 0.080 | 0.000 / 0.001 / 0.005 |
| Julia-1 + temperature (hybrid) | 0.275 / 0.230 / 0.225 | 0.035 / 0.035 / 0.036 |

**Reading.** A local checker can route about half of the extracted records past review at under 1–2% residual error,
*if* the base has good ranking (Laya, or a probe on NLI). Certifying that at 95% confidence needs a few hundred
**audited** records per partition × record type, so certification is a per-partition milestone, not a day-0 feature.
The deterministic value-token check is free and removes the numeric and value-swap classes outright (§3.5).

### 4.2 J2 certified recall (I15 applied to the grader; DA2's two-budget design)
Per test task: keep every candidate with P(vital) ≥ λ, where λ is the conformal quantile of the **minimum** P(vital)
over each calibration task's vital items, so P(all vital candidates kept) ≥ 1 − α.
| Arm | α | Calibration tasks | Test tasks | Coverage [Wilson] | CP lower 95% | Kept share of candidates |
|---|---|---|---|---|---|---|
| NLI + linear head | 0.10 | 60 | 108 | 0.944 [0.88–0.97] | 0.893 | **0.664** |
| NLI + linear head | 0.05 | 60 | 108 | 0.991 [0.95–1.00] | 0.957 | 0.851 |
| Julia + linear head | 0.10 | 60 | 108 | 0.926 [0.86–0.96] | 0.870 | 0.760 |
| Laya + temperature | 0.10 | 38 | 71 | 0.944 [0.86–0.98] | 0.876 | 0.870 |
| NLI + temperature | 0.10 | 60 | 108 | 0.870 [0.79–0.92] | 0.805 | 0.886 |

**Reading.** Coverage of the *all-vital* event meets the target, but the candidate set shrinks only to 66–87% of
its size, because the grader is not discriminative enough on these hard negatives (same entity, superseded versions).
The structural point from r6 stands: conformal certifies the recall that the scorer and upstream structure already
provide. A relevance grader is useful as stage-1 pruning only once its AUROC is well above 0.9; here it is
0.74–0.89 after 1,000 labels. Calibration n here (60 tasks) is far below the 300+ distinct sets per class that r6
recommends for a stable certificate.

### 4.3 J3 router: conformal prediction sets
| Arm | Target | Request type: coverage / mean set size / singleton share (singleton accuracy) | Area: coverage / mean set size / singleton share (singleton accuracy) |
|---|---|---|---|
| NLI + linear head | 90% | 0.940 / **1.32** / 0.72 (0.93) | 0.835 / 1.16 / 0.84 (0.84) |
| NLI + linear head | 95% | 0.955 / 1.57 / 0.55 (0.95) | 0.910 / 1.95 / 0.41 (0.94) |
| Julia + linear head | 90% | 0.895 / 1.92 / 0.37 (0.88) | 0.905 / **1.48** / 0.63 (0.92) |
| Laya + temperature | 90% | 0.890 / 2.48 / 0.25 (0.92) | 0.895 / 1.79 / 0.51 (0.84) |
| zero-shot + temperature (any) | 90% | sets of 3.4–4.4 of 5 | sets of 1.8–4.6 of 7 |

**Reading.** With 200 fitting plus 100 calibration labels, the best router (NLI + linear head) produces singletons for
72% (type) and 84% (area) of requests at 84–93% singleton accuracy, and small sets otherwise; weaker bases give
singletons for only 25–63%. A set of size > 1 can route to all areas in the set, since retrieval across two
areas is cheap. Zero-shot routers produce near-uninformative sets, so routing *needs* the brain's own labels or a
strong prior (the dashboard section the user is in).
