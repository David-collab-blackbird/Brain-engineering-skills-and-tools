# BrainBench v0.2 — batch 2 generated tables

All rates: mean over distinct required sets (cluster-aware), Wilson 95% over n = distinct sets, 3 seeds pooled unless stated. Paired tests: exact sign test over distinct sets; Δ with 95% cluster-bootstrap CI.

## v0.2 world and tasks

| seed | items | entities | keyed facts | tasks (8 classes) | stale probes |
|---|---|---|---|---|---|
| 1 | 10,869 | 216 | 468 | 2,207 | 330 |
| 2 | 10,840 | 214 | 468 | 2,164 | 324 |
| 3 | 10,829 | 215 | 468 | 2,145 | 319 |

| class | distinct sets per seed (s1/s2/s3) | tasks per seed | required-set sizes (pooled; 8 = 8+) |
|---|---|---|---|
| decision_support | 162/162/162 | 218/208/202 | 3:15, 4:237, 5:283, 6:35, 7:58 |
| option_analysis | 129/129/129 | 163/170/166 | 3:187, 4:303, 5:3, 6:3, 8:3 |
| current_state | 554/554/554 | 642/623/626 | 1:1633, 2:156, 3:102 |
| temporal_change | 424/410/402 | 503/480/473 | 2:861, 3:98, 4:233, 5:25, 6:239 |
| goal_tracking | 144/144/146 | 180/185/175 | 2:71, 3:281, 4:165, 6:13, 8:10 |
| preference_recommendation | 140/140/140 | 175/173/178 | 1:12, 2:313, 3:183, 4:4, 5:4, 6:6, 7:4 |
| cross_domain | 138/138/138 | 180/180/175 | 3:14, 4:313, 5:200, 6:4, 7:4 |
| multimodal | 129/129/129 | 146/145/150 | 1:296, 2:125, 3:20 |

## E8a — first-stage retrievers, exact search (all tasks, 3 seeds)

Weighted fusion alpha (on min-max BM25) tuned on seed 1 only: {'bge-small': 0.2, 'qwen3-emb': 0.3}. Grid (seed 1, score = mean rec@10 + mean CR@10): {"alpha_grid_bge-small": {"0.1": 0.985, "0.2": 0.996, "0.3": 0.973, "0.4": 0.938, "0.5": 0.911, "0.6": 0.877, "0.7": 0.829, "0.8": 0.775, "0.9": 0.739}, "alpha_grid_qwen3-emb": {"0.1": 0.904, "0.2": 0.938, "0.3": 0.94, "0.4": 0.921, "0.5": 0.901, "0.6": 0.859, "0.7": 0.809, "0.8": 0.781, "0.9": 0.741}}. Best first stage chosen on seed 1: **wsum(BM25+bge-small)**.

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| BM25 | 0.0 [0–1] | 1.8 [1–4] | 45.1 [43–48] | 47.2 [44–50] | 11.5 [9–15] | 4.3 [3–7] | 1.7 [1–3] | 73.6 [69–78] | 31.4 [30–33] |
| LSA-256 (batch-1 proxy) | 0.7 [0–2] | 1.4 [1–3] | 43.0 [41–45] | 31.0 [28–34] | 7.9 [6–11] | 2.5 [1–4] | 0.0 [0–1] | 57.1 [52–62] | 25.3 [24–27] |
| RRF(BM25+LSA) (batch-1 default) | 0.2 [0–1] | 0.4 [0–2] | 45.2 [43–48] | 38.2 [36–41] | 6.8 [5–10] | 2.0 [1–4] | 0.8 [0–2] | 65.2 [60–70] | 28.1 [27–29] |
| bge-small | 0.4 [0–1] | 2.5 [1–5] | 68.6 [66–71] | 61.4 [59–64] | 9.2 [7–12] | 3.3 [2–6] | 0.0 [0–1] | 81.4 [77–85] | 42.1 [41–43] |
| Qwen3-Emb-0.6B | 0.2 [0–1] | 4.8 [3–7] | 64.1 [62–66] | 55.0 [52–58] | 11.1 [8–14] | 3.1 [2–5] | 1.7 [1–3] | 69.9 [65–74] | 38.8 [37–40] |
| Qwen3-Emb-0.6B, task instruction | 0.2 [0–1] | 5.4 [4–8] | 65.3 [63–68] | 57.1 [54–60] | 12.2 [9–16] | 3.1 [2–5] | 1.9 [1–4] | 71.2 [66–75] | 39.9 [39–41] |
| rrf(BM25+bge-small) | 0.4 [0–1] | 2.3 [1–4] | 65.3 [63–68] | 59.7 [57–62] | 13.5 [11–17] | 3.8 [2–6] | 1.1 [0–3] | 80.7 [77–84] | 41.1 [40–42] |
| rrf(BM25+qwen3-emb) | 0.2 [0–1] | 3.4 [2–6] | 62.6 [60–65] | 58.2 [55–61] | 13.9 [11–18] | 3.8 [2–6] | 2.2 [1–4] | 75.2 [71–79] | 39.6 [38–41] |
| wsum(BM25+bge-small) | 0.2 [0–1] | 2.5 [1–5] | 72.4 [70–74] | 65.3 [63–68] | 11.6 [9–15] | 3.6 [2–6] | 0.8 [0–2] | 85.1 [81–88] | 44.6 [43–46] |
| wsum(BM25+qwen3-emb) | 0.2 [0–1] | 4.5 [3–7] | 66.5 [64–69] | 62.1 [59–65] | 12.2 [9–16] | 3.3 [2–6] | 2.3 [1–4] | 77.3 [73–81] | 41.8 [40–43] |
| *n sets (tasks)* | 486 (628) | 387 (499) | 1662 (1891) | 1236 (1456) | 434 (540) | 420 (526) | 414 (535) | 387 (441) | 5411 (6516) |

### Item recall@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| BM25 | 23.2 | 29.1 | 47.6 | 51.8 | 45.0 | 14.2 | 26.6 | 73.1 | 41.9 |
| LSA-256 (batch-1 proxy) | 20.5 | 27.4 | 46.5 | 39.2 | 40.0 | 16.3 | 13.3 | 59.9 | 36.1 |
| RRF(BM25+LSA) (batch-1 default) | 20.1 | 27.0 | 48.4 | 46.0 | 42.8 | 13.9 | 16.4 | 67.1 | 38.9 |
| bge-small | 25.8 | 35.4 | 71.8 | 70.6 | 45.3 | 15.5 | 19.3 | 84.3 | 54.1 |
| Qwen3-Emb-0.6B | 23.8 | 39.3 | 67.9 | 66.1 | 43.8 | 16.1 | 26.8 | 69.8 | 51.6 |
| Qwen3-Emb-0.6B, task instruction | 24.4 | 40.3 | 69.2 | 68.1 | 46.7 | 16.5 | 26.2 | 72.1 | 53.0 |
| rrf(BM25+bge-small) | 31.8 | 40.8 | 68.2 | 69.0 | 53.1 | 17.8 | 25.9 | 83.6 | 55.0 |
| rrf(BM25+qwen3-emb) | 26.4 | 38.8 | 65.9 | 67.2 | 53.0 | 17.1 | 30.5 | 76.8 | 53.1 |
| wsum(BM25+bge-small) | 30.9 | 41.0 | 75.1 | 74.1 | 50.4 | 17.5 | 24.6 | 87.5 | 58.0 |
| wsum(BM25+qwen3-emb) | 26.2 | 39.8 | 69.9 | 71.6 | 51.6 | 18.3 | 32.0 | 77.8 | 55.5 |

### Held-out seeds only (2 and 3), CR@10 % — the tuned fusion cannot have overfitted these

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| BM25 | 0.0 [0–1] | 1.6 [1–4] | 46.1 [43–49] | 48.5 [45–52] | 11.7 [9–16] | 3.9 [2–7] | 1.6 [1–4] | 75.2 [70–80] | 32.0 [30–34] |
| LSA-256 (batch-1 proxy) | 0.3 [0–2] | 1.4 [0–4] | 42.6 [40–46] | 31.9 [29–35] | 8.1 [5–12] | 2.9 [1–6] | 0.0 [0–1] | 57.0 [51–63] | 25.4 [24–27] |
| RRF(BM25+LSA) (batch-1 default) | 0.0 [0–1] | 0.2 [0–2] | 45.3 [42–48] | 39.2 [36–43] | 7.6 [5–11] | 2.5 [1–5] | 0.7 [0–3] | 67.1 [61–73] | 28.5 [27–30] |
| bge-small | 0.6 [0–2] | 2.5 [1–5] | 69.3 [67–72] | 61.8 [58–65] | 8.4 [6–12] | 3.2 [2–6] | 0.0 [0–1] | 81.0 [76–85] | 42.3 [41–44] |
| Qwen3-Emb-0.6B | 0.2 [0–1] | 5.4 [3–9] | 66.2 [63–69] | 55.4 [52–59] | 11.0 [8–15] | 3.2 [2–6] | 1.6 [1–4] | 70.9 [65–76] | 39.6 [38–41] |
| Qwen3-Emb-0.6B, task instruction | 0.3 [0–2] | 6.2 [4–10] | 66.9 [64–70] | 58.2 [55–62] | 12.6 [9–17] | 3.2 [2–6] | 1.8 [1–4] | 71.7 [66–77] | 40.7 [39–42] |
| rrf(BM25+bge-small) | 0.6 [0–2] | 2.3 [1–5] | 66.7 [64–69] | 60.2 [57–64] | 13.3 [10–18] | 4.3 [2–7] | 1.1 [0–3] | 81.2 [76–85] | 41.6 [40–43] |
| rrf(BM25+qwen3-emb) | 0.3 [0–2] | 3.9 [2–7] | 64.2 [61–67] | 58.9 [56–62] | 14.3 [11–19] | 3.9 [2–7] | 2.5 [1–5] | 75.8 [70–81] | 40.4 [39–42] |
| wsum(BM25+bge-small) | 0.3 [0–2] | 2.1 [1–5] | 73.3 [71–76] | 65.8 [62–69] | 11.2 [8–15] | 3.9 [2–7] | 0.7 [0–3] | 85.1 [80–89] | 44.9 [43–47] |
| wsum(BM25+qwen3-emb) | 0.3 [0–2] | 5.2 [3–9] | 67.9 [65–71] | 61.9 [59–65] | 11.9 [9–16] | 3.2 [2–6] | 2.7 [1–5] | 77.3 [72–82] | 42.2 [41–44] |
| *n sets (tasks)* | 324 (410) | 258 (336) | 1108 (1249) | 812 (953) | 290 (360) | 280 (351) | 276 (355) | 258 (295) | 3596 (4309) |

### Per-seed ALL CR@10 (s1 / s2 / s3)

| arm | per seed |
|---|---|
| BM25 | 30.1 / 31.4 / 32.6 |
| LSA-256 (batch-1 proxy) | 25.3 / 24.3 / 26.5 |
| RRF(BM25+LSA) (batch-1 default) | 27.3 / 27.9 / 29.1 |
| bge-small | 41.8 / 40.8 / 43.8 |
| Qwen3-Emb-0.6B | 37.2 / 38.8 / 40.4 |
| Qwen3-Emb-0.6B, task instruction | 38.2 / 40.1 / 41.3 |
| rrf(BM25+bge-small) | 40.0 / 41.0 / 42.2 |
| rrf(BM25+qwen3-emb) | 38.2 / 39.5 / 41.2 |
| wsum(BM25+bge-small) | 44.1 / 44.1 / 45.8 |
| wsum(BM25+qwen3-emb) | 41.0 / 41.6 / 42.7 |

### Depth diagnostic: item recall / CR at depth d (pooled)

| arm | class | d=10 | d=20 | d=50 | d=100 | d=200 |
|---|---|---|---|---|---|---|
| BM25 | decision | 23 / 0 | 37 / 1 | 51 / 8 | 59 / 12 | 68 / 18 |
| BM25 | option | 29 / 2 | 50 / 4 | 64 / 13 | 72 / 23 | 79 / 35 |
| BM25 | current | 48 / 45 | 60 / 57 | 71 / 70 | 79 / 79 | 82 / 82 |
| BM25 | temporal | 52 / 47 | 64 / 59 | 81 / 78 | 88 / 84 | 93 / 90 |
| BM25 | goal | 45 / 12 | 54 / 18 | 58 / 23 | 60 / 25 | 63 / 29 |
| BM25 | pref | 14 / 4 | 17 / 5 | 20 / 6 | 23 / 8 | 34 / 15 |
| BM25 | cross | 27 / 2 | 33 / 2 | 41 / 2 | 49 / 4 | 57 / 5 |
| BM25 | multimodal | 73 / 74 | 79 / 77 | 90 / 88 | 95 / 93 | 99 / 98 |
| RRF(BM25+LSA) (batch-1 default) | decision | 20 / 0 | 31 / 3 | 50 / 10 | 62 / 17 | 72 / 23 |
| RRF(BM25+LSA) (batch-1 default) | option | 27 / 0 | 43 / 5 | 64 / 19 | 76 / 33 | 85 / 48 |
| RRF(BM25+LSA) (batch-1 default) | current | 48 / 45 | 61 / 58 | 75 / 75 | 83 / 83 | 93 / 93 |
| RRF(BM25+LSA) (batch-1 default) | temporal | 46 / 38 | 59 / 52 | 74 / 69 | 85 / 81 | 93 / 90 |
| RRF(BM25+LSA) (batch-1 default) | goal | 43 / 7 | 51 / 13 | 66 / 26 | 73 / 36 | 85 / 62 |
| RRF(BM25+LSA) (batch-1 default) | pref | 14 / 2 | 22 / 7 | 34 / 12 | 43 / 19 | 61 / 49 |
| RRF(BM25+LSA) (batch-1 default) | cross | 16 / 1 | 23 / 1 | 35 / 1 | 45 / 3 | 60 / 6 |
| RRF(BM25+LSA) (batch-1 default) | multimodal | 67 / 65 | 79 / 76 | 92 / 90 | 95 / 93 | 99 / 99 |
| Qwen3-Emb-0.6B | decision | 24 / 0 | 34 / 1 | 54 / 11 | 64 / 18 | 68 / 22 |
| Qwen3-Emb-0.6B | option | 39 / 5 | 55 / 10 | 70 / 25 | 78 / 37 | 83 / 48 |
| Qwen3-Emb-0.6B | current | 68 / 64 | 80 / 78 | 90 / 89 | 93 / 93 | 98 / 98 |
| Qwen3-Emb-0.6B | temporal | 66 / 55 | 85 / 78 | 91 / 87 | 93 / 90 | 95 / 92 |
| Qwen3-Emb-0.6B | goal | 44 / 11 | 53 / 15 | 63 / 24 | 76 / 37 | 88 / 66 |
| Qwen3-Emb-0.6B | pref | 16 / 3 | 20 / 5 | 30 / 8 | 42 / 21 | 56 / 39 |
| Qwen3-Emb-0.6B | cross | 27 / 2 | 33 / 3 | 46 / 5 | 55 / 6 | 60 / 8 |
| Qwen3-Emb-0.6B | multimodal | 70 / 70 | 80 / 78 | 88 / 86 | 94 / 93 | 98 / 97 |
| wsum(BM25+bge-small) | decision | 31 / 0 | 42 / 2 | 56 / 11 | 64 / 18 | 70 / 23 |
| wsum(BM25+bge-small) | option | 41 / 2 | 58 / 10 | 72 / 28 | 79 / 39 | 83 / 49 |
| wsum(BM25+bge-small) | current | 75 / 72 | 83 / 82 | 89 / 88 | 93 / 93 | 97 / 97 |
| wsum(BM25+bge-small) | temporal | 74 / 65 | 87 / 81 | 92 / 88 | 94 / 91 | 95 / 92 |
| wsum(BM25+bge-small) | goal | 50 / 12 | 61 / 17 | 72 / 30 | 82 / 51 | 89 / 68 |
| wsum(BM25+bge-small) | pref | 17 / 4 | 25 / 7 | 34 / 14 | 44 / 25 | 55 / 42 |
| wsum(BM25+bge-small) | cross | 25 / 1 | 34 / 1 | 47 / 3 | 58 / 6 | 64 / 12 |
| wsum(BM25+bge-small) | multimodal | 88 / 85 | 90 / 89 | 96 / 94 | 99 / 98 | 100 / 99 |

### Paired tests vs BM25

| arm vs BM25 | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| LSA-256 (batch-1 proxy) | ALL | +295 / −619 | -6.0 [-7.0, -5.0] | 3.5e-27 |
| RRF(BM25+LSA) (batch-1 default) | ALL | +206 / −383 | -3.3 [-4.1, -2.5] | 2.7e-13 |
| bge-small | ALL | +935 / −305 | +10.8 [+9.6, +11.9] | 1.1e-74 |
| Qwen3-Emb-0.6B | ALL | +822 / −378 | +7.4 [+6.3, +8.6] | 2.7e-38 |
| Qwen3-Emb-0.6B, task instruction | ALL | +873 / −367 | +8.5 [+7.3, +9.7] | 5.7e-48 |
| rrf(BM25+bge-small) | ALL | +668 / −86 | +9.7 [+8.8, +10.6] | 1.8e-112 |
| rrf(BM25+qwen3-emb) | ALL | +609 / −110 | +8.3 [+7.4, +9.2] | 1.5e-84 |
| wsum(BM25+bge-small) | ALL | +899 / −118 | +13.3 [+12.2, +14.3] | 2.2e-149 |
| wsum(BM25+qwen3-emb) | ALL | +747 / −127 | +10.4 [+9.4, +11.4] | 1.6e-107 |

### Qwen3 vs bge-small (paired, per class)

| arm vs bge-small | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| Qwen3-Emb-0.6B | ALL | +379 / −561 | -3.3 [-4.4, -2.4] | 3.2e-09 |
| Qwen3-Emb-0.6B | decision | +2 / −2 | -0.2 [-0.9, +0.4] | 1 |
| Qwen3-Emb-0.6B | option | +21 / −12 | +2.3 [-0.1, +4.9] | 0.16 |
| Qwen3-Emb-0.6B | current | +184 / −257 | -4.4 [-6.6, -2.0] | 0.00059 |
| Qwen3-Emb-0.6B | temporal | +135 / −217 | -6.4 [-9.2, -3.5] | 1.5e-05 |
| Qwen3-Emb-0.6B | goal | +23 / −16 | +1.8 [-0.7, +4.4] | 0.34 |
| Qwen3-Emb-0.6B | pref | +2 / −3 | -0.2 [-1.2, +0.7] | 1 |
| Qwen3-Emb-0.6B | cross | +9 / −0 | +1.7 [+0.6, +2.9] | 0.0039 |
| Qwen3-Emb-0.6B | multimodal | +6 / −54 | -11.5 [-15.0, -8.0] | 9.7e-11 |
| Qwen3-Emb-0.6B, task instruction | ALL | +411 / −537 | -2.3 [-3.3, -1.2] | 4.8e-05 |
| Qwen3-Emb-0.6B, task instruction | decision | +1 / −2 | -0.2 [-1.0, +0.4] | 1 |
| Qwen3-Emb-0.6B, task instruction | option | +23 / −12 | +3.0 [+0.3, +5.7] | 0.09 |
| Qwen3-Emb-0.6B, task instruction | current | +194 / −245 | -3.3 [-5.5, -0.9] | 0.017 |
| Qwen3-Emb-0.6B, task instruction | temporal | +150 / −209 | -4.3 [-7.2, -1.3] | 0.0022 |
| Qwen3-Emb-0.6B, task instruction | goal | +30 / −17 | +3.0 [+0.2, +5.9] | 0.079 |
| Qwen3-Emb-0.6B, task instruction | pref | +2 / −3 | -0.2 [-1.2, +0.7] | 1 |
| Qwen3-Emb-0.6B, task instruction | cross | +9 / −0 | +1.9 [+0.7, +3.4] | 0.0039 |
| Qwen3-Emb-0.6B, task instruction | multimodal | +7 / −49 | -10.2 [-13.6, -6.8] | 7.5e-09 |

### Hybrid vs dense-only (Qwen3), paired

| arm vs Qwen3-Emb-0.6B | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| rrf(BM25+qwen3-emb) | ALL | +386 / −347 | +0.9 [-0.0, +1.8] | 0.16 |
| rrf(BM25+qwen3-emb) | decision | +1 / −2 | +0.0 [-0.4, +0.5] | 1 |
| rrf(BM25+qwen3-emb) | option | +5 / −12 | -1.4 [-3.2, +0.3] | 0.14 |
| rrf(BM25+qwen3-emb) | current | +154 / −185 | -1.5 [-3.4, +0.5] | 0.1 |
| rrf(BM25+qwen3-emb) | temporal | +155 / −118 | +3.2 [+0.6, +5.6] | 0.029 |
| rrf(BM25+qwen3-emb) | goal | +27 / −14 | +2.9 [+0.1, +5.8] | 0.06 |
| rrf(BM25+qwen3-emb) | pref | +3 / −0 | +0.7 [+0.0, +1.7] | 0.25 |
| rrf(BM25+qwen3-emb) | cross | +7 / −5 | +0.5 [-0.7, +1.8] | 0.77 |
| rrf(BM25+qwen3-emb) | multimodal | +34 / −11 | +5.3 [+2.1, +8.4] | 0.00082 |
| wsum(BM25+qwen3-emb) | ALL | +338 / −168 | +3.0 [+2.3, +3.8] | 3.3e-14 |
| wsum(BM25+qwen3-emb) | decision | +1 / −2 | +0.0 [-0.4, +0.5] | 1 |
| wsum(BM25+qwen3-emb) | option | +4 / −6 | -0.3 [-1.4, +0.9] | 0.75 |
| wsum(BM25+qwen3-emb) | current | +127 / −87 | +2.4 [+0.8, +4.0] | 0.0075 |
| wsum(BM25+qwen3-emb) | temporal | +149 / −55 | +7.1 [+5.0, +9.2] | 3.3e-11 |
| wsum(BM25+qwen3-emb) | goal | +14 / −8 | +1.2 [-0.7, +3.0] | 0.29 |
| wsum(BM25+qwen3-emb) | pref | +1 / −0 | +0.2 [+0.0, +0.7] | 1 |
| wsum(BM25+qwen3-emb) | cross | +7 / −5 | +0.6 [-0.7, +2.1] | 0.77 |
| wsum(BM25+qwen3-emb) | multimodal | +35 / −5 | +7.4 [+4.8, +10.2] | 1.4e-06 |

### Tuned weighted fusion vs RRF, held-out seeds 2–3

| arm vs rrf(BM25+qwen3-emb) | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| wsum(BM25+qwen3-emb) | ALL | +154 / −81 | +1.8 [+1.0, +2.6] | 2.2e-06 |

### Query-time cost per task (exact search over ~11k items, includes BM25 + dense matmul; embeddings cached)

| arm | ms/task |
|---|---|
| BM25 | 2.3 |
| LSA-256 (batch-1 proxy) | 2.0 |
| RRF(BM25+LSA) (batch-1 default) | 2.2 |
| bge-small | 0.6 |
| Qwen3-Emb-0.6B | 1.1 |
| Qwen3-Emb-0.6B, task instruction | 1.1 |
| rrf(BM25+bge-small) | 0.8 |
| rrf(BM25+qwen3-emb) | 1.3 |
| wsum(BM25+bge-small) | 0.7 |
| wsum(BM25+qwen3-emb) | 1.2 |

## E8b — rerankers on the top-50 of wsum(BM25+bge-small) (stratified distinct sets: {1: 40, 2: 15, 3: 10} per class per seed)

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| none | 0.0 [0–6] | 1.5 [0–8] | 72.3 [60–82] | 64.6 [52–75] | 12.3 [6–22] | 3.1 [1–11] | 0.0 [0–6] | 86.2 [76–93] | 30.1 [26–34] |
| bge-reranker-v2-m3 | 0.0 [0–6] | 3.1 [1–11] | 67.7 [56–78] | 61.5 [49–72] | 12.3 [6–22] | 6.2 [2–15] | 0.0 [0–6] | 87.7 [78–94] | 29.9 [26–34] |
| mxbai-rerank-base-v2 | 0.0 [0–6] | 1.5 [0–8] | 75.4 [64–84] | 72.3 [60–82] | 12.3 [6–22] | 6.2 [2–15] | 0.0 [0–6] | 86.2 [76–93] | 31.8 [28–36] |
| mxbai-rerank-base-v2 + scope-templated instruction | 2.5 [0–13] | 5.0 [1–17] | 42.5 [29–58] | 37.5 [24–53] | 2.5 [0–13] | 5.0 [1–17] | 0.0 [0–9] | 65.0 [50–78] | 20.1 [16–25] |
| qwen3-reranker | 0.0 [0–6] | 9.2 [4–19] | 76.9 [65–85] | 72.3 [60–82] | 15.4 [9–26] | 6.2 [2–15] | 0.0 [0–6] | 89.2 [79–95] | 33.7 [30–38] |
| qwen3-reranker + scope-templated instruction (H12) | 0.0 [0–9] | 7.5 [3–20] | 60.0 [45–74] | 65.0 [50–78] | 12.5 [5–26] | 7.5 [3–20] | 0.0 [0–9] | 80.0 [65–90] | 29.2 [24–34] |
| *n sets (tasks)* | 65 (65) | 65 (65) | 65 (65) | 65 (65) | 65 (65) | 65 (65) | 65 (65) | 65 (65) | 519 (520) |

### Item recall@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| none | 25.5 | 39.3 | 78.7 | 70.6 | 52.1 | 23.6 | 30.4 | 88.5 | 51.1 |
| bge-reranker-v2-m3 | 26.6 | 35.6 | 73.1 | 72.6 | 57.4 | 22.6 | 36.5 | 90.0 | 51.8 |
| mxbai-rerank-base-v2 | 24.5 | 40.4 | 80.0 | 81.7 | 53.2 | 27.4 | 32.2 | 87.7 | 53.4 |
| mxbai-rerank-base-v2 + scope-templated instruction | 22.5 | 34.6 | 47.9 | 45.2 | 40.8 | 27.1 | 28.1 | 67.5 | 39.2 |
| qwen3-reranker | 29.6 | 54.8 | 82.3 | 77.6 | 61.7 | 26.2 | 37.5 | 90.0 | 57.5 |
| qwen3-reranker + scope-templated instruction (H12) | 33.1 | 44.2 | 66.7 | 75.8 | 51.2 | 27.5 | 32.4 | 81.2 | 51.5 |

Ceiling: CR@50 of the candidate pool (no reranker can exceed it): decision 8, option 31, current 86, temporal 91, goal 29, pref 22, cross 3, multimodal 92

### Paired tests vs no reranker

| arm vs none | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| bge-reranker-v2-m3 | ALL | +13 / −14 | -0.2 [-2.1, +1.7] | 1 |
| bge-reranker-v2-m3 | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| bge-reranker-v2-m3 | option | +2 / −1 | +1.5 [-3.1, +7.7] | 1 |
| bge-reranker-v2-m3 | current | +2 / −5 | -4.6 [-12.3, +3.1] | 0.45 |
| bge-reranker-v2-m3 | temporal | +4 / −6 | -3.1 [-12.3, +6.2] | 0.75 |
| bge-reranker-v2-m3 | goal | +1 / −1 | +0.0 [-4.6, +4.6] | 1 |
| bge-reranker-v2-m3 | pref | +2 / −0 | +3.1 [+0.0, +7.7] | 0.5 |
| bge-reranker-v2-m3 | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| bge-reranker-v2-m3 | multimodal | +2 / −1 | +1.5 [-3.1, +7.7] | 1 |
| mxbai-rerank-base-v2 | ALL | +18 / −9 | +1.7 [-0.4, +3.7] | 0.12 |
| mxbai-rerank-base-v2 | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| mxbai-rerank-base-v2 | option | +1 / −1 | +0.0 [-4.6, +4.6] | 1 |
| mxbai-rerank-base-v2 | current | +5 / −3 | +3.1 [-6.2, +12.3] | 0.73 |
| mxbai-rerank-base-v2 | temporal | +8 / −3 | +7.7 [-3.1, +18.5] | 0.23 |
| mxbai-rerank-base-v2 | goal | +1 / −1 | +0.0 [-4.6, +4.6] | 1 |
| mxbai-rerank-base-v2 | pref | +2 / −0 | +3.1 [+0.0, +7.7] | 0.5 |
| mxbai-rerank-base-v2 | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| mxbai-rerank-base-v2 | multimodal | +1 / −1 | +0.0 [-4.6, +4.6] | 1 |
| mxbai-rerank-base-v2 + scope-templated instruction | ALL | +6 / −36 | -9.4 [-13.5, -5.6] | 2.8e-06 |
| mxbai-rerank-base-v2 + scope-templated instruction | decision | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| mxbai-rerank-base-v2 + scope-templated instruction | option | +2 / −1 | +2.5 [-5.0, +10.0] | 1 |
| mxbai-rerank-base-v2 + scope-templated instruction | current | +1 / −12 | -27.5 [-45.0, -12.5] | 0.0034 |
| mxbai-rerank-base-v2 + scope-templated instruction | temporal | +0 / −12 | -30.0 [-45.0, -17.5] | 0.00049 |
| mxbai-rerank-base-v2 + scope-templated instruction | goal | +0 / −3 | -7.5 [-17.5, +0.0] | 0.25 |
| mxbai-rerank-base-v2 + scope-templated instruction | pref | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| mxbai-rerank-base-v2 + scope-templated instruction | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| mxbai-rerank-base-v2 + scope-templated instruction | multimodal | +1 / −8 | -17.5 [-30.0, -5.0] | 0.039 |
| qwen3-reranker | ALL | +27 / −8 | +3.7 [+1.5, +5.8] | 0.0019 |
| qwen3-reranker | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| qwen3-reranker | option | +6 / −1 | +7.7 [+0.0, +15.4] | 0.12 |
| qwen3-reranker | current | +5 / −2 | +4.6 [-3.1, +12.3] | 0.45 |
| qwen3-reranker | temporal | +7 / −2 | +7.7 [+0.0, +16.9] | 0.18 |
| qwen3-reranker | goal | +3 / −1 | +3.1 [-3.1, +9.2] | 0.62 |
| qwen3-reranker | pref | +3 / −1 | +3.1 [-3.1, +9.2] | 0.62 |
| qwen3-reranker | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| qwen3-reranker | multimodal | +3 / −1 | +3.1 [-3.1, +9.2] | 0.62 |
| qwen3-reranker + scope-templated instruction (H12) | ALL | +13 / −14 | -0.3 [-3.4, +2.8] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | option | +3 / −1 | +5.0 [-5.0, +15.0] | 0.62 |
| qwen3-reranker + scope-templated instruction (H12) | current | +3 / −7 | -10.0 [-25.1, +5.0] | 0.34 |
| qwen3-reranker + scope-templated instruction (H12) | temporal | +3 / −4 | -2.5 [-15.0, +10.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | goal | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | pref | +2 / −0 | +5.0 [+0.0, +12.5] | 0.5 |
| qwen3-reranker + scope-templated instruction (H12) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | multimodal | +1 / −2 | -2.5 [-12.5, +5.0] | 1 |

### H12: scope-templated vs generic instruction (Qwen3-Reranker)

| arm vs qwen3-reranker | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| qwen3-reranker + scope-templated instruction (H12) | ALL | +6 / −21 | -4.7 [-7.8, -1.6] | 0.0059 |
| qwen3-reranker + scope-templated instruction (H12) | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | option | +1 / −2 | -2.5 [-10.0, +5.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | current | +0 / −7 | -17.5 [-30.0, -7.5] | 0.016 |
| qwen3-reranker + scope-templated instruction (H12) | temporal | +1 / −5 | -10.0 [-22.5, +0.0] | 0.22 |
| qwen3-reranker + scope-templated instruction (H12) | goal | +2 / −3 | -2.5 [-12.5, +7.5] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | pref | +2 / −2 | +0.0 [-10.0, +10.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| qwen3-reranker + scope-templated instruction (H12) | multimodal | +0 / −2 | -5.0 [-12.5, +0.0] | 0.5 |

### Instruction check on mxbai (seed 1 only)

| arm vs mxbai-rerank-base-v2 | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| mxbai-rerank-base-v2 + scope-templated instruction | ALL | +4 / −41 | -11.6 [-15.4, -7.5] | 9.3e-09 |

Reranker throughput (uncached pairs only) is in the component table at the end; wall-clock per variant including first-stage and cache hits: bge-reranker-v2-m3 543 s; mxbai-rerank-base-v2 1384 s; mxbai-rerank-base-v2 + scope-templated instruction 203 s; qwen3-reranker 3684 s; qwen3-reranker + scope-templated instruction (H12) 2031 s

## E8c — batch-1 arms re-run with the best real first stage (wsum/bge-small/alpha=0.2), equal k=10, all tasks, 3 seeds

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only | 0.2 [0–1] | 2.5 [1–5] | 72.4 [70–74] | 65.3 [63–68] | 11.6 [9–15] | 3.6 [2–6] | 0.8 [0–2] | 85.1 [81–88] | 44.6 [43–46] |
| query + mention forwarding | 0.5 [0–2] | 7.4 [5–10] | 78.5 [76–80] | 63.4 [61–66] | 16.0 [13–20] | 5.8 [4–9] | 1.1 [0–3] | 80.9 [77–84] | 46.7 [45–48] |
| packet(5) + query | 0.0 [0–1] | 1.0 [0–3] | 57.9 [56–60] | 34.7 [32–37] | 7.7 [6–11] | 3.6 [2–6] | 0.5 [0–2] | 75.2 [71–79] | 32.1 [31–33] |
| ORACLE packet(5) + query | 1.1 [1–3] | 4.0 [2–6] | 58.0 [56–60] | 35.0 [32–38] | 15.4 [12–19] | 13.2 [10–17] | 1.3 [1–3] | 75.2 [71–79] | 33.9 [33–35] |
| hand slots + query | 5.1 [4–7] | 11.8 [9–15] | 91.1 [90–92] | 45.5 [43–48] | 38.7 [34–43] | 3.6 [2–6] | 5.2 [3–8] | 75.5 [71–79] | 48.8 [48–50] |
| generic slots + query | 6.6 [5–9] | 8.7 [6–12] | 94.6 [93–96] | 46.5 [44–49] | 37.2 [33–42] | 3.8 [2–6] | 0.2 [0–1] | 75.5 [71–79] | 49.6 [48–51] |
| cards(<=3) + query | 8.2 [6–11] | 16.9 [14–21] | 97.4 [96–98] | 64.6 [62–67] | 43.5 [39–48] | 10.0 [7–13] | 1.2 [1–3] | 83.9 [80–87] | 56.9 [56–58] |
| cards(<=3) + static slots + query | 15.5 [13–19] | 16.1 [13–20] | 97.8 [97–98] | 42.9 [40–46] | 42.2 [38–47] | 9.8 [7–13] | 4.6 [3–7] | 74.9 [70–79] | 52.2 [51–54] |
| declared scope: hard filter | 0.2 [0–1] | 3.5 [2–6] | 74.0 [72–76] | 65.7 [63–68] | 13.4 [10–17] | 3.8 [2–6] | 0.0 [0–1] | 86.0 [82–89] | 45.5 [44–47] |
| declared scope: boost w=1 | 0.2 [0–1] | 3.2 [2–6] | 73.9 [72–76] | 65.5 [63–68] | 13.4 [10–17] | 3.8 [2–6] | 0.0 [0–1] | 86.0 [82–89] | 45.4 [44–47] |
| query-inferred scope: hard | 0.2 [0–1] | 2.7 [2–5] | 64.0 [62–66] | 60.4 [58–63] | 10.4 [8–14] | 3.3 [2–6] | 0.7 [0–2] | 79.3 [75–83] | 40.4 [39–42] |
| query-inferred scope: boost | 0.2 [0–1] | 2.5 [1–5] | 71.6 [69–74] | 64.6 [62–67] | 10.6 [8–14] | 3.3 [2–6] | 0.7 [0–2] | 79.8 [76–84] | 43.8 [42–45] |
| *n sets (tasks)* | 486 (628) | 387 (499) | 1662 (1891) | 1236 (1456) | 434 (540) | 420 (526) | 414 (535) | 387 (441) | 5411 (6516) |

### Item recall@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only | 30.9 | 41.0 | 75.1 | 74.1 | 50.4 | 17.5 | 24.6 | 87.5 | 58.0 |
| query + mention forwarding | 41.7 | 53.1 | 81.0 | 77.2 | 58.9 | 21.7 | 34.3 | 82.8 | 63.9 |
| packet(5) + query | 34.5 | 27.6 | 62.1 | 51.9 | 47.6 | 15.7 | 32.7 | 77.4 | 48.2 |
| ORACLE packet(5) + query | 43.8 | 32.4 | 62.3 | 52.2 | 51.1 | 41.0 | 43.9 | 77.4 | 52.8 |
| hand slots + query | 59.7 | 64.3 | 92.4 | 70.4 | 77.2 | 20.0 | 42.6 | 77.8 | 70.0 |
| generic slots + query | 55.2 | 63.6 | 95.4 | 70.8 | 76.5 | 20.1 | 35.9 | 77.8 | 69.9 |
| cards(<=3) + query | 58.4 | 69.1 | 97.2 | 81.7 | 78.2 | 26.4 | 38.9 | 85.9 | 75.0 |
| cards(<=3) + static slots + query | 74.0 | 69.9 | 97.6 | 70.0 | 79.3 | 25.6 | 50.0 | 77.0 | 74.4 |
| declared scope: hard filter | 31.6 | 42.2 | 76.6 | 74.6 | 52.4 | 17.9 | 19.7 | 88.5 | 58.6 |
| declared scope: boost w=1 | 31.7 | 42.1 | 76.5 | 74.6 | 52.4 | 17.9 | 20.6 | 88.5 | 58.6 |
| query-inferred scope: hard | 29.9 | 36.9 | 66.5 | 67.8 | 45.7 | 17.0 | 21.9 | 81.5 | 52.6 |
| query-inferred scope: boost | 30.2 | 40.4 | 74.3 | 73.7 | 49.3 | 17.2 | 22.1 | 82.2 | 56.9 |

### Paired tests vs query-only

| arm vs query-only | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| query + mention forwarding | ALL | +216 / −97 | +2.1 [+1.5, +2.6] | 1.5e-11 |
| query + mention forwarding | decision | +2 / −0 | +0.3 [+0.0, +0.8] | 0.5 |
| query + mention forwarding | option | +23 / −0 | +4.9 [+3.0, +7.1] | 2.4e-07 |
| query + mention forwarding | current | +143 / −36 | +6.1 [+4.7, +7.6] | 2.7e-16 |
| query + mention forwarding | temporal | +15 / −40 | -1.9 [-3.0, -0.9] | 0.001 |
| query + mention forwarding | goal | +21 / −1 | +4.4 [+2.4, +6.5] | 1.1e-05 |
| query + mention forwarding | pref | +10 / −0 | +2.3 [+1.0, +3.8] | 0.002 |
| query + mention forwarding | cross | +2 / −0 | +0.2 [+0.0, +0.6] | 0.5 |
| query + mention forwarding | multimodal | +0 / −20 | -4.3 [-6.2, -2.6] | 1.9e-06 |
| packet(5) + query | ALL | +60 / −796 | -12.5 [-13.5, -11.6] | 5.8e-165 |
| packet(5) + query | decision | +0 / −1 | -0.2 [-0.6, +0.0] | 1 |
| packet(5) + query | option | +2 / −10 | -1.4 [-3.0, +0.0] | 0.039 |
| packet(5) + query | current | +57 / −311 | -14.4 [-16.4, -12.3] | 1.8e-43 |
| packet(5) + query | temporal | +0 / −407 | -30.5 [-33.1, -28.2] | 6.1e-123 |
| packet(5) + query | goal | +0 / −20 | -3.9 [-5.8, -2.3] | 1.9e-06 |
| packet(5) + query | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| packet(5) + query | cross | +1 / −3 | -0.4 [-1.3, +0.5] | 0.62 |
| packet(5) + query | multimodal | +0 / −45 | -9.9 [-12.7, -7.2] | 5.7e-14 |
| ORACLE packet(5) + query | ALL | +169 / −790 | -10.7 [-11.8, -9.7] | 1.5e-96 |
| ORACLE packet(5) + query | decision | +6 / −1 | +0.9 [+0.0, +2.1] | 0.12 |
| ORACLE packet(5) + query | option | +15 / −9 | +1.6 [-0.6, +3.9] | 0.31 |
| ORACLE packet(5) + query | current | +61 / −311 | -14.4 [-16.4, -12.3] | 1.8e-41 |
| ORACLE packet(5) + query | temporal | +0 / −402 | -30.3 [-32.8, -27.9] | 1.9e-121 |
| ORACLE packet(5) + query | goal | +38 / −19 | +3.8 [+0.8, +6.9] | 0.016 |
| ORACLE packet(5) + query | pref | +44 / −1 | +9.6 [+6.8, +12.5] | 2.6e-12 |
| ORACLE packet(5) + query | cross | +5 / −3 | +0.5 [-0.7, +1.7] | 0.73 |
| ORACLE packet(5) + query | multimodal | +0 / −45 | -9.9 [-12.7, -7.2] | 5.7e-14 |
| hand slots + query | ALL | +637 / −402 | +4.2 [+3.1, +5.3] | 3.1e-13 |
| hand slots + query | decision | +27 / −0 | +4.9 [+3.2, +6.8] | 1.5e-08 |
| hand slots + query | option | +47 / −6 | +9.3 [+5.9, +12.5] | 5.8e-09 |
| hand slots + query | current | +394 / −61 | +18.7 [+16.5, +20.9] | 1e-60 |
| hand slots + query | temporal | +13 / −276 | -19.8 [-22.1, -17.7] | 2.5e-65 |
| hand slots + query | goal | +131 / −11 | +27.1 [+22.5, +31.7] | 3.1e-27 |
| hand slots + query | pref | +2 / −2 | +0.0 [-1.0, +1.0] | 1 |
| hand slots + query | cross | +23 / −3 | +4.3 [+2.3, +6.5] | 8.8e-05 |
| hand slots + query | multimodal | +0 / −44 | -9.7 [-12.4, -7.0] | 1.1e-13 |
| generic slots + query | ALL | +628 / −352 | +4.9 [+3.9, +6.0] | 9.3e-19 |
| generic slots + query | decision | +34 / −0 | +6.4 [+4.3, +8.6] | 1.2e-10 |
| generic slots + query | option | +35 / −9 | +6.2 [+3.2, +9.2] | 0.00011 |
| generic slots + query | current | +423 / −25 | +22.2 [+20.1, +24.3] | 1.8e-94 |
| generic slots + query | temporal | +14 / −263 | -18.8 [-21.0, -16.5] | 1.1e-60 |
| generic slots + query | goal | +120 / −8 | +25.6 [+21.1, +30.0] | 9e-27 |
| generic slots + query | pref | +2 / −1 | +0.2 [-0.5, +1.0] | 1 |
| generic slots + query | cross | +0 / −3 | -0.6 [-1.4, +0.0] | 0.25 |
| generic slots + query | multimodal | +0 / −44 | -9.7 [-12.4, -7.0] | 1.1e-13 |
| cards(<=3) + query | ALL | +749 / −41 | +12.3 [+11.4, +13.2] | 2.1e-169 |
| cards(<=3) + query | decision | +42 / −0 | +8.0 [+5.8, +10.5] | 4.5e-13 |
| cards(<=3) + query | option | +60 / −0 | +14.5 [+11.2, +18.0] | 1.7e-18 |
| cards(<=3) + query | current | +448 / −0 | +25.0 [+23.0, +27.1] | 2.8e-135 |
| cards(<=3) + query | temporal | +26 / −34 | -0.6 [-1.7, +0.4] | 0.37 |
| cards(<=3) + query | goal | +142 / −0 | +31.9 [+27.5, +36.3] | 3.6e-43 |
| cards(<=3) + query | pref | +28 / −0 | +6.4 [+4.3, +8.8] | 7.5e-09 |
| cards(<=3) + query | cross | +3 / −0 | +0.4 [+0.0, +0.8] | 0.25 |
| cards(<=3) + query | multimodal | +0 / −7 | -1.3 [-2.5, -0.4] | 0.016 |
| cards(<=3) + static slots + query | ALL | +824 / −389 | +7.6 [+6.5, +8.7] | 2.1e-36 |
| cards(<=3) + static slots + query | decision | +82 / −1 | +15.3 [+12.1, +18.4] | 1.7e-23 |
| cards(<=3) + static slots + query | option | +66 / −6 | +13.7 [+9.9, +17.6] | 7.3e-14 |
| cards(<=3) + static slots + query | current | +461 / −5 | +25.5 [+23.4, +27.6] | 1.9e-129 |
| cards(<=3) + static slots + query | temporal | +17 / −316 | -22.4 [-24.8, -20.1] | 1.7e-72 |
| cards(<=3) + static slots + query | goal | +149 / −12 | +30.5 [+25.6, +35.1] | 3.1e-31 |
| cards(<=3) + static slots + query | pref | +28 / −1 | +6.2 [+4.0, +8.7] | 1.1e-07 |
| cards(<=3) + static slots + query | cross | +21 / −3 | +3.7 [+1.8, +5.9] | 0.00028 |
| cards(<=3) + static slots + query | multimodal | +0 / −46 | -10.2 [-13.0, -7.5] | 2.8e-14 |
| declared scope: hard filter | ALL | +62 / −13 | +0.9 [+0.6, +1.2] | 8.4e-09 |
| declared scope: hard filter | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| declared scope: hard filter | option | +7 / −3 | +1.0 [-0.5, +2.8] | 0.34 |
| declared scope: hard filter | current | +31 / −2 | +1.6 [+1.0, +2.3] | 1.3e-07 |
| declared scope: hard filter | temporal | +8 / −2 | +0.4 [-0.1, +0.8] | 0.11 |
| declared scope: hard filter | goal | +8 / −0 | +1.7 [+0.7, +3.0] | 0.0078 |
| declared scope: hard filter | pref | +1 / −0 | +0.2 [+0.0, +0.7] | 1 |
| declared scope: hard filter | cross | +0 / −5 | -0.8 [-1.7, -0.2] | 0.062 |
| declared scope: hard filter | multimodal | +7 / −2 | +0.9 [-0.4, +2.3] | 0.18 |
| declared scope: boost w=1 | ALL | +56 / −12 | +0.8 [+0.5, +1.1] | 6.2e-08 |
| declared scope: boost w=1 | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| declared scope: boost w=1 | option | +6 / −3 | +0.8 [-0.8, +2.3] | 0.51 |
| declared scope: boost w=1 | current | +29 / −1 | +1.6 [+1.0, +2.2] | 5.8e-08 |
| declared scope: boost w=1 | temporal | +5 / −2 | +0.2 [-0.2, +0.5] | 0.45 |
| declared scope: boost w=1 | goal | +8 / −0 | +1.7 [+0.7, +3.0] | 0.0078 |
| declared scope: boost w=1 | pref | +1 / −0 | +0.2 [+0.0, +0.7] | 1 |
| declared scope: boost w=1 | cross | +0 / −5 | -0.8 [-1.7, -0.2] | 0.062 |
| declared scope: boost w=1 | multimodal | +7 / −2 | +0.9 [-0.4, +2.3] | 0.18 |
| query-inferred scope: hard | ALL | +23 / −292 | -4.2 [-4.8, -3.6] | 1.6e-60 |
| query-inferred scope: hard | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| query-inferred scope: hard | option | +1 / −0 | +0.3 [+0.0, +0.8] | 1 |
| query-inferred scope: hard | current | +14 / −177 | -8.4 [-9.8, -7.0] | 4.2e-37 |
| query-inferred scope: hard | temporal | +5 / −78 | -4.9 [-6.1, -3.8] | 6.4e-18 |
| query-inferred scope: hard | goal | +1 / −8 | -1.3 [-2.5, -0.2] | 0.039 |
| query-inferred scope: hard | pref | +0 / −1 | -0.2 [-0.7, +0.0] | 1 |
| query-inferred scope: hard | cross | +0 / −1 | -0.1 [-0.4, +0.0] | 1 |
| query-inferred scope: hard | multimodal | +2 / −27 | -5.8 [-8.3, -3.5] | 1.6e-06 |
| query-inferred scope: boost | ALL | +18 / −72 | -0.9 [-1.2, -0.6] | 8.1e-09 |
| query-inferred scope: boost | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| query-inferred scope: boost | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| query-inferred scope: boost | current | +13 / −29 | -0.8 [-1.4, -0.1] | 0.02 |
| query-inferred scope: boost | temporal | +2 / −10 | -0.7 [-1.2, -0.2] | 0.039 |
| query-inferred scope: boost | goal | +1 / −6 | -1.0 [-2.3, +0.0] | 0.12 |
| query-inferred scope: boost | pref | +0 / −1 | -0.2 [-0.7, +0.0] | 1 |
| query-inferred scope: boost | cross | +0 / −1 | -0.1 [-0.4, +0.0] | 1 |
| query-inferred scope: boost | multimodal | +2 / −25 | -5.3 [-7.9, -3.0] | 5.6e-06 |

### Mean share of required items covered by the pinned prefix alone

| arm | decision | option | current | temporal | goal | pref | cross | multimodal |
|---|---|---|---|---|---|---|---|---|
| packet(5) + query | 14 | 4 | 9 | 2 | 18 | 0 | 16 | 0 |
| ORACLE packet(5) + query | 23 | 9 | 8 | 3 | 12 | 32 | 28 | 0 |
| hand slots + query | 49 | 50 | 84 | 35 | 66 | 10 | 26 | 0 |
| generic slots + query | 44 | 50 | 93 | 37 | 68 | 10 | 19 | 0 |
| cards(<=3) + query | 45 | 52 | 93 | 37 | 66 | 10 | 19 | 0 |
| cards(<=3) + static slots + query | 64 | 56 | 96 | 38 | 70 | 10 | 33 | 0 |

### Same arms with the batch-1 retriever (RRF BM25+LSA) on v0.2, CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only | 0.2 | 0.4 | 45.2 | 38.2 | 6.8 | 2.0 | 0.8 | 65.2 | 28.1 |
| query + mention forwarding | 0.2 | 1.2 | 55.6 | 37.0 | 8.6 | 3.2 | 0.8 | 64.2 | 31.2 |
| packet(5) + query | 0.2 | 0.5 | 42.1 | 23.3 | 6.1 | 1.7 | 0.6 | 58.7 | 23.2 |
| ORACLE packet(5) + query | 0.7 | 0.8 | 41.5 | 23.3 | 10.3 | 7.4 | 0.6 | 58.0 | 23.8 |
| hand slots + query | 0.8 | 3.0 | 87.1 | 28.3 | 30.1 | 3.5 | 2.4 | 59.0 | 40.5 |
| generic slots + query | 2.5 | 2.8 | 89.6 | 29.4 | 29.4 | 3.5 | 0.6 | 59.8 | 41.6 |
| cards(<=3) + query | 6.5 | 9.8 | 95.7 | 40.9 | 32.1 | 7.3 | 0.8 | 64.5 | 47.8 |
| cards(<=3) + static slots + query | 6.0 | 7.9 | 97.1 | 29.2 | 32.0 | 7.0 | 0.6 | 57.2 | 44.8 |
| declared scope: hard filter | 0.2 | 0.4 | 47.7 | 39.6 | 9.7 | 4.6 | 0.0 | 68.0 | 29.7 |
| declared scope: boost w=1 | 0.2 | 0.6 | 48.1 | 39.7 | 9.9 | 4.8 | 0.6 | 67.6 | 29.9 |
| query-inferred scope: hard | 0.2 | 0.4 | 38.6 | 36.0 | 6.8 | 2.0 | 0.8 | 60.9 | 25.2 |
| query-inferred scope: boost | 0.2 | 0.4 | 46.3 | 38.1 | 7.0 | 2.1 | 0.8 | 61.9 | 28.2 |
| *n sets (tasks)* | 486 (628) | 387 (499) | 1662 (1891) | 1236 (1456) | 434 (540) | 420 (526) | 414 (535) | 387 (441) | 5411 (6516) |

### Real embedder vs LSA, per arm (ALL, paired over sets)

| arm | LSA retriever | real retriever | Δ pp [CI] | p |
|---|---|---|---|---|
| query-only | 28.1 | 44.6 | +16.6 [+15.5, +17.6] | 1.1e-199 |
| query + mention forwarding | 31.2 | 46.7 | +15.5 [+14.4, +16.6] | 3.6e-174 |
| packet(5) + query | 23.2 | 32.1 | +8.9 [+8.0, +9.9] | 1.7e-73 |
| ORACLE packet(5) + query | 23.8 | 33.9 | +10.2 [+9.1, +11.2] | 6.6e-88 |
| hand slots + query | 40.5 | 48.8 | +8.3 [+7.4, +9.2] | 6.2e-71 |
| generic slots + query | 41.6 | 49.6 | +8.0 [+7.2, +8.9] | 1.9e-69 |
| cards(<=3) + query | 47.8 | 56.9 | +9.2 [+8.3, +10.1] | 7.1e-88 |
| cards(<=3) + static slots + query | 44.8 | 52.2 | +7.4 [+6.6, +8.2] | 2.9e-65 |
| declared scope: hard filter | 29.7 | 45.5 | +15.8 [+14.7, +16.8] | 3.1e-186 |
| declared scope: boost w=1 | 29.9 | 45.4 | +15.5 [+14.5, +16.5] | 9.2e-181 |
| query-inferred scope: hard | 25.2 | 40.4 | +15.2 [+14.1, +16.2] | 5.5e-191 |
| query-inferred scope: boost | 28.2 | 43.8 | +15.6 [+14.6, +16.6] | 6e-183 |

### H9 / k sweep: CR@k (query-only vs cards + static slots)

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only | 0.2 [0–1] | 2.5 [1–5] | 72.4 [70–74] | 65.3 [63–68] | 11.6 [9–15] | 3.6 [2–6] | 0.8 [0–2] | 85.1 [81–88] | 44.6 [43–46] |
| query-only@20 | 2.1 [1–4] | 10.1 [7–13] | 81.6 [80–83] | 81.3 [79–83] | 17.2 [14–21] | 7.4 [5–10] | 1.1 [0–3] | 88.6 [85–91] | 52.8 [52–54] |
| query-only@30 | 6.4 [5–9] | 19.0 [15–23] | 84.7 [83–86] | 84.9 [83–87] | 20.2 [17–24] | 10.5 [8–14] | 1.7 [1–3] | 91.0 [88–93] | 56.3 [55–58] |
| cards(<=3) + static slots + query | 15.5 [13–19] | 16.1 [13–20] | 97.8 [97–98] | 42.9 [40–46] | 42.2 [38–47] | 9.8 [7–13] | 4.6 [3–7] | 74.9 [70–79] | 52.2 [51–54] |
| cards+slots@20 | 21.1 [18–25] | 25.3 [21–30] | 98.4 [98–99] | 78.7 [76–81] | 47.8 [43–53] | 16.7 [13–21] | 10.7 [8–14] | 87.5 [84–90] | 64.1 [63–65] |
| cards+slots@30 | 25.8 [22–30] | 29.1 [25–34] | 98.5 [98–99] | 84.6 [83–87] | 51.4 [47–56] | 19.5 [16–24] | 14.4 [11–18] | 89.9 [87–93] | 67.1 [66–68] |

### CR@10 by required-set size (cards + static slots + query; pooled)

| size | n sets | CR@10 | item recall | p^m prediction |
|---|---|---|---|---|
| 1 | 1692 | 96.5 [96–97] | 96 | 74 |
| 2 | 1286 | 49.1 [46–52] | 64 | 55 |
| 3 | 743 | 47.3 [44–51] | 73 | 41 |
| 4 | 986 | 14.6 [13–17] | 64 | 31 |
| 5 | 401 | 9.0 [7–12] | 66 | 23 |
| 6 | 243 | 12.1 [9–17] | 52 | 17 |
| 7 | 51 | 1.0 [0–9] | 73 | 13 |
| 8+ | 9 | 0.0 [0–30] | 33 | 7 |

### I8 — origin context for media (multimodal, all tasks, 3 seeds), CR@10 %

| index | retriever | all | caption sufficient | needs origin-only item |
|---|---|---|---|---|
| base | bm25 | 73.6 [69–78] (n=387) | 84.9 [78–90] (n=126) | 68.2 [62–74] (n=261) |
| base | dense | 81.4 [77–85] (n=387) | 93.7 [88–97] (n=126) | 75.5 [70–80] (n=261) |
| base | rrf | 80.7 [77–84] (n=387) | 91.7 [86–95] (n=126) | 75.5 [70–80] (n=261) |
| base | wsum | 85.1 [81–88] (n=387) | 94.4 [89–97] (n=126) | 80.7 [75–85] (n=261) |
| noorig | bm25 | 52.5 [47–57] (n=387) | 79.4 [71–86] (n=126) | 39.5 [34–46] (n=261) |
| noorig | dense | 52.3 [47–57] (n=387) | 88.1 [81–93] (n=126) | 35.1 [30–41] (n=261) |
| noorig | rrf | 55.7 [51–61] (n=387) | 88.9 [82–93] (n=126) | 39.7 [34–46] (n=261) |
| noorig | wsum | 55.3 [50–60] (n=387) | 92.5 [86–96] (n=126) | 37.4 [32–43] (n=261) |

Paired (bm25): with origin +90 / −2 sets, Δ +21.2 pp [+17.2, +25.3], p=1.7e-24.

Paired (dense): with origin +118 / −0 sets, Δ +29.1 pp [+24.7, +33.5], p=6e-36.

Paired (rrf): with origin +107 / −5 sets, Δ +25.1 pp [+20.7, +29.3], p=5.4e-26.

Paired (wsum): with origin +125 / −4 sets, Δ +29.8 pp [+25.2, +34.2], p=3.3e-32.

## M1 — measured CR@k vs independence prediction E[p^m]

`p_item` = class item recall; `pred(class p)` = mean over tasks of p_item^m; `pred(size p)` uses the item recall of tasks with the same class and size; `rho` = intra-task correlation of item successes implied by the variance of the found count (beta-binomial; 0 = independent, >0 = items succeed/fail together).


**query-only**

| class | n tasks | p_item | measured CR | pred (class p) | pred (size p) | measured − pred | rho |
|---|---|---|---|---|---|---|---|
| decision | 628 | 30.9 | 0.2 | 0.6 | 0.7 | -0.4 | -0.03 |
| option | 499 | 41.0 | 2.6 | 4.3 | 4.3 | -1.7 | -0.03 |
| current | 1891 | 75.1 | 72.9 | 71.8 | 71.3 | +1.2 | 0.41 |
| temporal | 1456 | 74.1 | 65.7 | 43.1 | 44.9 | +22.5 | 0.66 |
| goal | 540 | 50.4 | 12.4 | 12.0 | 15.5 | +0.4 | -0.01 |
| pref | 526 | 17.5 | 2.9 | 2.4 | 3.4 | +0.4 | -0.01 |
| cross | 535 | 24.6 | 0.9 | 0.3 | 0.5 | +0.6 | 0.05 |
| multimodal | 441 | 87.5 | 82.5 | 83.5 | 80.9 | -1.0 | 0.25 |
| ALL | 6516 | 58.0 | 43.0 | 30.8 | 34.5 | +12.2 | 0.36 |

**cards + static slots**

| class | n tasks | p_item | measured CR | pred (class p) | pred (size p) | measured − pred | rho |
|---|---|---|---|---|---|---|---|
| decision | 628 | 74.0 | 15.0 | 24.3 | 24.9 | -9.3 | -0.06 |
| option | 499 | 69.9 | 18.0 | 27.5 | 28.0 | -9.4 | -0.09 |
| current | 1891 | 97.6 | 97.6 | 97.1 | 97.6 | +0.4 | -0.00 |
| temporal | 1456 | 70.0 | 43.8 | 37.3 | 41.4 | +6.4 | -0.05 |
| goal | 540 | 79.3 | 40.6 | 47.1 | 49.4 | -6.6 | -0.05 |
| pref | 526 | 25.6 | 8.0 | 5.1 | 7.0 | +2.9 | 0.01 |
| cross | 535 | 50.0 | 4.7 | 5.2 | 5.6 | -0.5 | -0.06 |
| multimodal | 441 | 77.0 | 71.2 | 70.5 | 70.3 | +0.7 | 0.14 |
| ALL | 6516 | 74.4 | 50.1 | 49.4 | 47.9 | +0.7 | 0.17 |

**query-only@30**

| class | n tasks | p_item | measured CR | pred (class p) | pred (size p) | measured − pred | rho |
|---|---|---|---|---|---|---|---|
| decision | 628 | 49.3 | 6.7 | 4.0 | 5.1 | +2.7 | 0.02 |
| option | 499 | 65.6 | 21.6 | 21.9 | 22.8 | -0.3 | 0.05 |
| current | 1891 | 86.0 | 85.0 | 83.8 | 84.2 | +1.2 | 0.42 |
| temporal | 1456 | 89.4 | 85.5 | 71.7 | 74.4 | +13.8 | 0.64 |
| goal | 540 | 65.6 | 20.2 | 26.3 | 28.9 | -6.1 | -0.04 |
| pref | 526 | 28.0 | 9.1 | 6.1 | 7.1 | +3.1 | 0.09 |
| cross | 535 | 38.3 | 1.9 | 1.7 | 2.2 | +0.2 | 0.10 |
| multimodal | 441 | 92.4 | 89.8 | 89.8 | 87.5 | -0.0 | 0.46 |
| ALL | 6516 | 71.8 | 54.7 | 45.9 | 46.6 | +8.8 | 0.37 |

### M1 with item-specific p (product of each required item's leave-one-task-out hit rate in the same arm, class and seed)

| arm | class | measured CR@10 | pred: Π p_item(i) | pred: p_class^m | share of items with own estimate |
|---|---|---|---|---|---|
| query-only | decision | 0.2 | 0.2 | 0.6 | 75% |
| query-only | option | 2.6 | 3.3 | 4.3 | 48% |
| query-only | current | 72.9 | 71.0 | 71.8 | 70% |
| query-only | temporal | 65.7 | 51.7 | 43.1 | 53% |
| query-only | goal | 12.4 | 9.0 | 12.0 | 84% |
| query-only | pref | 2.9 | 1.1 | 2.4 | 87% |
| query-only | cross | 0.9 | 0.7 | 0.3 | 94% |
| query-only | multimodal | 82.5 | 75.7 | 83.5 | 77% |
| query-only | ALL | 43.0 | 38.5 | 30.8 | 70% |
| cards + static slots | decision | 15.0 | 22.1 | 24.3 | 75% |
| cards + static slots | option | 18.0 | 24.4 | 27.5 | 48% |
| cards + static slots | current | 97.6 | 98.0 | 97.1 | 70% |
| cards + static slots | temporal | 43.8 | 39.5 | 37.3 | 53% |
| cards + static slots | goal | 40.6 | 35.4 | 47.1 | 84% |
| cards + static slots | pref | 8.0 | 1.4 | 5.1 | 87% |
| cards + static slots | cross | 4.7 | 7.1 | 5.2 | 94% |
| cards + static slots | multimodal | 71.2 | 59.7 | 70.5 | 77% |
| cards + static slots | ALL | 50.1 | 48.9 | 49.4 | 70% |
| cards | decision | 8.1 | 9.1 | 8.4 | 75% |
| cards | option | 17.8 | 21.7 | 26.4 | 48% |
| cards | current | 97.2 | 98.0 | 96.7 | 70% |
| cards | temporal | 65.0 | 58.3 | 55.7 | 53% |
| cards | goal | 41.5 | 34.7 | 45.2 | 84% |
| cards | pref | 8.2 | 1.6 | 5.4 | 87% |
| cards | cross | 1.5 | 1.3 | 1.8 | 94% |
| cards | multimodal | 81.0 | 72.9 | 81.5 | 77% |
| cards | ALL | 54.6 | 52.0 | 50.3 | 70% |

## N5 — class-conditional prefix via a two-regex router (temporal regex from batch 1 + a media-word regex), CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only | 0.2 [0–1] | 2.5 [1–5] | 72.4 [70–74] | 65.3 [63–68] | 11.6 [9–15] | 3.6 [2–6] | 0.8 [0–2] | 85.1 [81–88] | 44.6 [43–46] |
| cards(<=3) + query | 8.2 [6–11] | 16.9 [14–21] | 97.4 [96–98] | 64.6 [62–67] | 43.5 [39–48] | 10.0 [7–13] | 1.2 [1–3] | 83.9 [80–87] | 56.9 [56–58] |
| cards(<=3) + static slots + query | 15.5 [13–19] | 16.1 [13–20] | 97.8 [97–98] | 42.9 [40–46] | 42.2 [38–47] | 9.8 [7–13] | 4.6 [3–7] | 74.9 [70–79] | 52.2 [51–54] |
| router: temporal/media -> query-only, else cards+slots | 15.5 [13–19] | 14.5 [11–18] | 97.8 [97–98] | 65.3 [63–68] | 42.2 [38–47] | 9.8 [7–13] | 4.6 [3–7] | 83.1 [79–86] | 57.8 [56–59] |
| router: temporal/media -> query-only, else cards | 8.2 [6–11] | 16.7 [13–21] | 97.4 [96–98] | 65.3 [63–68] | 43.5 [39–48] | 10.0 [7–13] | 1.2 [1–3] | 84.6 [81–88] | 57.1 [56–58] |
| router: temporal/media -> cards, else cards+slots | 15.5 [13–19] | 14.7 [12–19] | 97.8 [97–98] | 64.6 [62–67] | 42.2 [38–47] | 9.8 [7–13] | 4.6 [3–7] | 82.3 [78–86] | 57.6 [56–59] |
| *n sets (tasks)* | 486 (628) | 387 (499) | 1662 (1891) | 1236 (1456) | 434 (540) | 420 (526) | 414 (535) | 387 (441) | 5411 (6516) |

### Paired vs cards(<=3) + query (best fixed arm)

| arm vs cards(<=3) + query | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| query-only | ALL | +41 / −749 | -12.3 [-13.2, -11.4] | 2.1e-169 |
| query-only | decision | +0 / −42 | -8.0 [-10.5, -5.8] | 4.5e-13 |
| query-only | option | +0 / −60 | -14.5 [-18.0, -11.2] | 1.7e-18 |
| query-only | current | +0 / −448 | -25.0 [-27.1, -23.0] | 2.8e-135 |
| query-only | temporal | +34 / −26 | +0.6 [-0.4, +1.7] | 0.37 |
| query-only | goal | +0 / −142 | -31.9 [-36.3, -27.5] | 3.6e-43 |
| query-only | pref | +0 / −28 | -6.4 [-8.8, -4.3] | 7.5e-09 |
| query-only | cross | +0 / −3 | -0.4 [-0.8, +0.0] | 0.25 |
| query-only | multimodal | +7 / −0 | +1.3 [+0.4, +2.5] | 0.016 |
| cards(<=3) + static slots + query | ALL | +104 / −385 | -4.7 [-5.4, -4.0] | 6e-39 |
| cards(<=3) + static slots + query | decision | +45 / −6 | +7.3 [+4.7, +10.0] | 1.8e-08 |
| cards(<=3) + static slots + query | option | +16 / −21 | -0.8 [-3.4, +2.1] | 0.51 |
| cards(<=3) + static slots + query | current | +15 / −7 | +0.5 [-0.1, +1.0] | 0.13 |
| cards(<=3) + static slots + query | temporal | +0 / −292 | -21.8 [-24.0, -19.5] | 2.5e-88 |
| cards(<=3) + static slots + query | goal | +8 / −14 | -1.4 [-3.1, +0.2] | 0.29 |
| cards(<=3) + static slots + query | pref | +0 / −1 | -0.2 [-0.7, +0.0] | 1 |
| cards(<=3) + static slots + query | cross | +20 / −5 | +3.4 [+1.3, +5.4] | 0.0041 |
| cards(<=3) + static slots + query | multimodal | +0 / −40 | -8.9 [-11.6, -6.3] | 1.8e-12 |
| router: temporal/media -> query-only, else cards+slots | ALL | +139 / −88 | +0.9 [+0.4, +1.4] | 0.00087 |
| router: temporal/media -> query-only, else cards+slots | decision | +45 / −6 | +7.3 [+4.7, +10.0] | 1.8e-08 |
| router: temporal/media -> query-only, else cards+slots | option | +13 / −23 | -2.5 [-4.8, -0.1] | 0.13 |
| router: temporal/media -> query-only, else cards+slots | current | +15 / −7 | +0.5 [-0.1, +1.0] | 0.13 |
| router: temporal/media -> query-only, else cards+slots | temporal | +34 / −26 | +0.6 [-0.4, +1.7] | 0.37 |
| router: temporal/media -> query-only, else cards+slots | goal | +8 / −14 | -1.4 [-3.1, +0.2] | 0.29 |
| router: temporal/media -> query-only, else cards+slots | pref | +0 / −1 | -0.2 [-0.7, +0.0] | 1 |
| router: temporal/media -> query-only, else cards+slots | cross | +20 / −5 | +3.4 [+1.3, +5.4] | 0.0041 |
| router: temporal/media -> query-only, else cards+slots | multimodal | +4 / −7 | -0.8 [-2.1, +0.5] | 0.55 |
| router: temporal/media -> query-only, else cards | ALL | +39 / −28 | +0.2 [-0.1, +0.5] | 0.22 |
| router: temporal/media -> query-only, else cards | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| router: temporal/media -> query-only, else cards | option | +0 / −2 | -0.3 [-0.6, +0.0] | 0.5 |
| router: temporal/media -> query-only, else cards | current | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| router: temporal/media -> query-only, else cards | temporal | +34 / −26 | +0.6 [-0.4, +1.7] | 0.37 |
| router: temporal/media -> query-only, else cards | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| router: temporal/media -> query-only, else cards | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| router: temporal/media -> query-only, else cards | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| router: temporal/media -> query-only, else cards | multimodal | +5 / −0 | +0.8 [+0.1, +1.6] | 0.062 |
| router: temporal/media -> cards, else cards+slots | ALL | +101 / −61 | +0.7 [+0.3, +1.1] | 0.0021 |
| router: temporal/media -> cards, else cards+slots | decision | +45 / −6 | +7.3 [+4.7, +10.0] | 1.8e-08 |
| router: temporal/media -> cards, else cards+slots | option | +13 / −21 | -2.2 [-4.5, +0.1] | 0.23 |
| router: temporal/media -> cards, else cards+slots | current | +15 / −7 | +0.5 [-0.1, +1.0] | 0.13 |
| router: temporal/media -> cards, else cards+slots | temporal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| router: temporal/media -> cards, else cards+slots | goal | +8 / −14 | -1.4 [-3.1, +0.2] | 0.29 |
| router: temporal/media -> cards, else cards+slots | pref | +0 / −1 | -0.2 [-0.7, +0.0] | 1 |
| router: temporal/media -> cards, else cards+slots | cross | +20 / −5 | +3.4 [+1.3, +5.4] | 0.0041 |
| router: temporal/media -> cards, else cards+slots | multimodal | +0 / −8 | -1.6 [-2.8, -0.5] | 0.0078 |

Routing decisions (tasks, pooled): cross_domain|none: 12, cross_domain|prefix: 523, current_state|prefix: 1891, decision_support|none: 8, decision_support|prefix: 620, goal_tracking|none: 31, goal_tracking|prefix: 509, multimodal|none: 412, multimodal|prefix: 29, option_analysis|none: 63, option_analysis|prefix: 436, preference_recommendation|none: 3, preference_recommendation|prefix: 523, temporal_change|none: 1386, temporal_change|prefix: 70

## Structural ceilings (oracle analyses; no model calls)

Share of required items that are keyed-fact versions (reachable by slots/cards) vs media vs other free text:

| class | keyed facts | media | free text (notes, emails, chats, meetings, preferences) |
|---|---|---|---|
| decision | 70% | 0% | 30% |
| option | 59% | 0% | 41% |
| current | 100% | 0% | 0% |
| temporal | 100% | 0% | 0% |
| goal | 76% | 0% | 24% |
| pref | 30% | 0% | 70% |
| cross | 44% | 0% | 56% |
| multimodal | 0% | 100% | 0% |

### CR@10 % with oracle structure

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| cards(<=3) + query (lexical linker) | 8.2 [6–11] | 16.9 [14–21] | 97.4 [96–98] | 64.6 [62–67] | 43.5 [39–48] | 10.0 [7–13] | 1.2 [1–3] | 83.9 [80–87] | 56.9 [56–58] |
| cards(<=3) + static slots + query | 15.5 [13–19] | 16.1 [13–20] | 97.8 [97–98] | 42.9 [40–46] | 42.2 [38–47] | 9.8 [7–13] | 4.6 [3–7] | 74.9 [70–79] | 52.2 [51–54] |
| oracle linker: cards(<=3) + query | 20.8 [17–25] | 21.2 [17–26] | 100.0 [100–100] | 65.0 [62–68] | 48.4 [44–53] | 14.3 [11–18] | 15.5 [12–19] | 84.1 [80–87] | 61.1 [60–62] |
| oracle linker: cards(all required entities) + query | 20.8 [17–25] | 21.2 [17–26] | 100.0 [100–100] | 65.0 [62–68] | 48.4 [44–53] | 14.3 [11–18] | 16.2 [13–20] | 84.1 [80–87] | 61.2 [60–62] |
| oracle slots: every required keyed fact pinned + query | 19.8 [16–24] | 21.1 [17–25] | 100.0 [100–100] | 100.0 [100–100] | 48.4 [44–53] | 15.1 [12–19] | 16.3 [13–20] | 85.1 [81–88] | 69.2 [68–70] |
| *n sets (tasks)* | 486 (628) | 387 (499) | 1662 (1891) | 1236 (1456) | 434 (540) | 420 (526) | 414 (535) | 387 (441) | 5411 (6516) |

### Item recall@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| cards(<=3) + query (lexical linker) | 58.4 | 69.1 | 97.2 | 81.7 | 78.2 | 26.4 | 38.9 | 85.9 | 75.0 |
| cards(<=3) + static slots + query | 74.0 | 69.9 | 97.6 | 70.0 | 79.3 | 25.6 | 50.0 | 77.0 | 74.4 |
| oracle linker: cards(<=3) + query | 79.9 | 74.3 | 100.0 | 81.9 | 84.6 | 38.0 | 60.6 | 86.4 | 81.6 |
| oracle linker: cards(all required entities) + query | 79.9 | 74.3 | 100.0 | 81.9 | 84.6 | 38.0 | 61.0 | 86.4 | 81.6 |
| oracle slots: every required keyed fact pinned + query | 79.5 | 74.3 | 100.0 | 100.0 | 84.6 | 38.4 | 61.2 | 87.5 | 85.8 |

### Residual recall: share of required FREE-TEXT items in the top-10 (search's share of the job), and CR over tasks restricted to their free-text items

| arm | decision | option | goal | pref | cross |
|---|---|---|---|---|---|
| oracle slots: every required keyed fact pinned + query | 33% items / 19% tasks (n=625) | 35% items / 22% tasks (n=496) | 30% items / 31% tasks (n=414) | 14% items / 14% tasks (n=526) | 31% items / 15% tasks (n=531) |
| cards(<=3) + static slots + query | 30% items / 16% tasks (n=625) | 30% items / 18% tasks (n=496) | 27% items / 28% tasks (n=414) | 13% items / 13% tasks (n=526) | 27% items / 12% tasks (n=531) |

## E6a — model-free arms on complex classes (40 distinct sets per class per seed, 3 seeds)

### CR@10 %

| arm | decision | option | goal | cross | ALL |
|---|---|---|---|---|---|
| one-shot | 0.0 [0–3] | 2.5 [1–7] | 11.7 [7–19] | 1.7 [0–6] | 3.9 [2–6] |
| facet decomposition (deterministic) | 0.8 [0–5] | 2.5 [1–7] | 10.0 [6–17] | 1.7 [0–6] | 3.7 [2–6] |
| one-shot, LSA (batch-1 rrf) | 0.0 [0–3] | 0.0 [0–3] | 8.3 [5–15] | 0.8 [0–5] | 2.2 [1–4] |
| one-shot, BM25 only | 0.0 [0–3] | 1.7 [0–6] | 13.3 [8–21] | 2.5 [1–7] | 4.2 [3–6] |
| one-shot, bge-small dense | 0.8 [0–5] | 1.7 [0–6] | 9.2 [5–16] | 0.0 [0–3] | 2.9 [2–5] |
| one-shot, Qwen3-Emb dense | 0.0 [0–3] | 4.2 [2–9] | 14.2 [9–22] | 0.8 [0–5] | 4.6 [3–7] |
| one-shot, wsum BM25+Qwen3-Emb | 0.0 [0–3] | 4.2 [2–9] | 13.3 [8–21] | 1.7 [0–6] | 4.6 [3–7] |
| cards+slots + one-shot | 13.3 [8–21] | 20.0 [14–28] | 44.2 [36–53] | 5.8 [3–12] | 20.8 [17–25] |
| cards+slots + facets | 6.7 [3–13] | 12.5 [8–20] | 33.3 [26–42] | 2.5 [1–7] | 13.8 [11–17] |
| *n sets (tasks)* | 120 (120) | 120 (120) | 120 (120) | 120 (120) | 478 (480) |

### Item recall@10 %

| arm | decision | option | goal | cross | ALL |
|---|---|---|---|---|---|
| one-shot | 29.3 | 39.1 | 51.9 | 25.1 | 36.3 |
| facet decomposition (deterministic) | 37.9 | 48.8 | 55.3 | 25.5 | 41.9 |
| one-shot, LSA (batch-1 rrf) | 18.6 | 24.3 | 44.3 | 16.5 | 25.9 |
| one-shot, BM25 only | 22.7 | 29.2 | 47.1 | 26.2 | 31.3 |
| one-shot, bge-small dense | 24.7 | 33.9 | 45.8 | 19.7 | 31.0 |
| one-shot, Qwen3-Emb dense | 22.6 | 37.0 | 47.3 | 24.5 | 32.8 |
| one-shot, wsum BM25+Qwen3-Emb | 23.3 | 37.9 | 54.4 | 32.3 | 37.0 |
| cards+slots + one-shot | 72.0 | 71.9 | 79.9 | 51.6 | 68.8 |
| cards+slots + facets | 69.5 | 67.9 | 76.0 | 45.9 | 64.8 |

### CR@20 %

| arm | decision | option | goal | cross | ALL |
|---|---|---|---|---|---|
| one-shot | 0.8 | 9.2 | 18.3 | 1.7 | 7.4 |
| facet decomposition (deterministic) | 6.7 | 15.0 | 20.0 | 3.3 | 11.1 |
| one-shot, LSA (batch-1 rrf) | 0.8 | 3.3 | 13.3 | 1.7 | 4.7 |
| one-shot, BM25 only | 0.0 | 7.5 | 19.2 | 2.5 | 7.1 |
| one-shot, bge-small dense | 2.5 | 5.8 | 13.3 | 0.0 | 5.4 |
| one-shot, Qwen3-Emb dense | 0.8 | 8.3 | 15.8 | 1.7 | 6.5 |
| one-shot, wsum BM25+Qwen3-Emb | 0.0 | 9.2 | 20.0 | 2.5 | 7.7 |
| cards+slots + one-shot | 13.3 | 20.0 | 44.2 | 5.8 | 20.8 |
| cards+slots + facets | 6.7 | 12.5 | 33.3 | 2.5 | 13.8 |

### Paired vs one-shot (best hybrid)

| arm vs one-shot | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| facet decomposition (deterministic) | ALL | +3 / −4 | -0.2 [-1.3, +0.8] | 1 |
| facet decomposition (deterministic) | decision | +1 / −0 | +0.8 [+0.0, +2.5] | 1 |
| facet decomposition (deterministic) | option | +1 / −1 | +0.0 [-2.5, +2.5] | 1 |
| facet decomposition (deterministic) | goal | +1 / −3 | -1.7 [-5.0, +1.7] | 0.62 |
| facet decomposition (deterministic) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, LSA (batch-1 rrf) | ALL | +6 / −14 | -1.7 [-3.6, +0.2] | 0.12 |
| one-shot, LSA (batch-1 rrf) | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, LSA (batch-1 rrf) | option | +0 / −3 | -2.5 [-5.8, +0.0] | 0.25 |
| one-shot, LSA (batch-1 rrf) | goal | +6 / −10 | -3.3 [-10.0, +3.3] | 0.45 |
| one-shot, LSA (batch-1 rrf) | cross | +0 / −1 | -0.8 [-2.5, +0.0] | 1 |
| one-shot, BM25 only | ALL | +9 / −7 | +0.3 [-1.3, +1.9] | 0.8 |
| one-shot, BM25 only | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, BM25 only | option | +1 / −2 | -0.8 [-4.2, +1.7] | 1 |
| one-shot, BM25 only | goal | +7 / −5 | +1.7 [-4.2, +7.5] | 0.77 |
| one-shot, BM25 only | cross | +1 / −0 | +0.8 [+0.0, +2.5] | 1 |
| one-shot, bge-small dense | ALL | +1 / −6 | -0.9 [-2.1, +0.0] | 0.12 |
| one-shot, bge-small dense | decision | +1 / −0 | +0.8 [+0.0, +2.5] | 1 |
| one-shot, bge-small dense | option | +0 / −1 | -0.8 [-2.5, +0.0] | 1 |
| one-shot, bge-small dense | goal | +0 / −3 | -2.5 [-5.8, +0.0] | 0.25 |
| one-shot, bge-small dense | cross | +0 / −2 | -1.7 [-4.2, +0.0] | 0.5 |
| one-shot, Qwen3-Emb dense | ALL | +11 / −7 | +0.7 [-0.8, +2.4] | 0.48 |
| one-shot, Qwen3-Emb dense | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, Qwen3-Emb dense | option | +4 / −2 | +1.7 [-2.5, +5.8] | 0.69 |
| one-shot, Qwen3-Emb dense | goal | +7 / −4 | +2.5 [-3.3, +7.5] | 0.55 |
| one-shot, Qwen3-Emb dense | cross | +0 / −1 | -0.8 [-2.5, +0.0] | 1 |
| one-shot, wsum BM25+Qwen3-Emb | ALL | +9 / −5 | +0.7 [-0.8, +2.2] | 0.42 |
| one-shot, wsum BM25+Qwen3-Emb | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, wsum BM25+Qwen3-Emb | option | +3 / −1 | +1.7 [-1.7, +5.0] | 0.62 |
| one-shot, wsum BM25+Qwen3-Emb | goal | +6 / −4 | +1.7 [-3.3, +6.7] | 0.75 |
| one-shot, wsum BM25+Qwen3-Emb | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| cards+slots + one-shot | ALL | +85 / −4 | +16.9 [+13.4, +20.5] | 8.3e-21 |
| cards+slots + one-shot | decision | +16 / −0 | +13.3 [+7.5, +20.0] | 3.1e-05 |
| cards+slots + one-shot | option | +22 / −1 | +17.5 [+10.8, +25.0] | 5.7e-06 |
| cards+slots + one-shot | goal | +42 / −3 | +32.5 [+22.5, +41.7] | 8.7e-10 |
| cards+slots + one-shot | cross | +5 / −0 | +4.2 [+0.8, +8.3] | 0.062 |
| cards+slots + facets | ALL | +56 / −9 | +9.9 [+6.8, +13.2] | 2e-09 |
| cards+slots + facets | decision | +8 / −0 | +6.7 [+2.5, +11.7] | 0.0078 |
| cards+slots + facets | option | +13 / −1 | +10.0 [+5.0, +15.8] | 0.0018 |
| cards+slots + facets | goal | +33 / −7 | +21.7 [+11.7, +30.8] | 4.2e-05 |
| cards+slots + facets | cross | +2 / −1 | +0.8 [-1.7, +3.3] | 1 |

### With the structural prefix, paired vs cards+slots + one-shot

| arm vs cards+slots + one-shot | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| cards+slots + facets | ALL | +1 / −35 | -7.0 [-9.5, -4.8] | 1.1e-09 |
| cards+slots + facets | decision | +0 / −8 | -6.7 [-11.7, -2.5] | 0.0078 |
| cards+slots + facets | option | +0 / −9 | -7.5 [-12.5, -3.3] | 0.0039 |
| cards+slots + facets | goal | +1 / −14 | -10.8 [-16.7, -5.0] | 0.00098 |
| cards+slots + facets | cross | +0 / −4 | -3.3 [-6.7, -0.8] | 0.12 |

## E6b — LLM decomposition and gap-check (seeds [1]; 12 distinct sets per complex class; LLM = Qwen/Qwen3-1.7B, greedy, thinking off, few-shot prompts)

### CR@10 %

| arm | decision | option | goal | cross | ALL |
|---|---|---|---|---|---|
| one-shot | 0.0 [0–24] | 0.0 [0–24] | 41.7 [19–68] | 0.0 [0–24] | 10.4 [5–22] |
| decomposition (LLM, <=4, RRF union) | 0.0 [0–24] | 0.0 [0–24] | 41.7 [19–68] | 0.0 [0–24] | 10.4 [5–22] |
| facet decomposition (deterministic) | 0.0 [0–24] | 0.0 [0–24] | 41.7 [19–68] | 0.0 [0–24] | 10.4 [5–22] |
| gap-check (<=2 rounds) | 0.0 [0–24] | 0.0 [0–24] | 41.7 [19–68] | 0.0 [0–24] | 10.4 [5–22] |
| cards+slots + one-shot | 25.0 [9–53] | 25.0 [9–53] | 58.3 [32–81] | 0.0 [0–24] | 27.1 [17–41] |
| cards+slots + decomposition | 16.7 [5–45] | 16.7 [5–45] | 66.7 [39–86] | 0.0 [0–24] | 25.0 [15–39] |
| cards+slots + gap-check queries | 25.0 [9–53] | 33.3 [14–61] | 41.7 [19–68] | 0.0 [0–24] | 25.0 [15–39] |
| cards+slots + facets | 16.7 [5–45] | 16.7 [5–45] | 58.3 [32–81] | 0.0 [0–24] | 22.9 [13–37] |
| one-shot, bge-small dense | 0.0 [0–24] | 0.0 [0–24] | 33.3 [14–61] | 0.0 [0–24] | 8.3 [3–20] |
| one-shot, Qwen3-Emb dense | 0.0 [0–24] | 0.0 [0–24] | 33.3 [14–61] | 0.0 [0–24] | 8.3 [3–20] |
| one-shot, BM25 only | 0.0 [0–24] | 0.0 [0–24] | 16.7 [5–45] | 0.0 [0–24] | 4.2 [1–14] |
| one-shot, wsum BM25+Qwen3-Emb | 0.0 [0–24] | 0.0 [0–24] | 25.0 [9–53] | 0.0 [0–24] | 6.2 [2–17] |
| *n sets (tasks)* | 12 (12) | 12 (12) | 12 (12) | 12 (12) | 48 (48) |

### Item recall@10 %

| arm | decision | option | goal | cross | ALL |
|---|---|---|---|---|---|
| one-shot | 15.7 | 47.9 | 63.2 | 15.8 | 35.7 |
| decomposition (LLM, <=4, RRF union) | 23.6 | 45.8 | 63.2 | 16.2 | 37.2 |
| facet decomposition (deterministic) | 22.7 | 50.7 | 64.6 | 17.9 | 39.0 |
| gap-check (<=2 rounds) | 16.9 | 50.7 | 58.3 | 17.9 | 36.0 |
| cards+slots + one-shot | 66.7 | 68.1 | 83.3 | 41.2 | 64.8 |
| cards+slots + decomposition | 65.5 | 68.1 | 86.1 | 37.5 | 64.3 |
| cards+slots + gap-check queries | 65.1 | 70.8 | 76.4 | 45.4 | 64.4 |
| cards+slots + facets | 63.4 | 65.3 | 83.3 | 37.5 | 62.4 |
| one-shot, bge-small dense | 12.9 | 49.3 | 59.0 | 9.6 | 32.7 |
| one-shot, Qwen3-Emb dense | 14.9 | 33.3 | 52.8 | 18.3 | 29.8 |
| one-shot, BM25 only | 13.3 | 26.4 | 49.3 | 19.2 | 27.0 |
| one-shot, wsum BM25+Qwen3-Emb | 14.5 | 31.2 | 56.9 | 24.2 | 31.7 |

### CR@20 %

| arm | decision | option | goal | cross | ALL |
|---|---|---|---|---|---|
| one-shot | 0.0 | 0.0 | 41.7 | 0.0 | 10.4 |
| decomposition (LLM, <=4, RRF union) | 0.0 | 8.3 | 41.7 | 0.0 | 12.5 |
| facet decomposition (deterministic) | 8.3 | 16.7 | 41.7 | 0.0 | 16.7 |
| gap-check (<=2 rounds) | 0.0 | 8.3 | 50.0 | 0.0 | 14.6 |
| cards+slots + one-shot | 25.0 | 25.0 | 58.3 | 0.0 | 27.1 |
| cards+slots + decomposition | 16.7 | 16.7 | 66.7 | 0.0 | 25.0 |
| cards+slots + gap-check queries | 25.0 | 33.3 | 41.7 | 0.0 | 25.0 |
| cards+slots + facets | 16.7 | 16.7 | 58.3 | 0.0 | 22.9 |
| one-shot, bge-small dense | 0.0 | 16.7 | 33.3 | 0.0 | 12.5 |
| one-shot, Qwen3-Emb dense | 0.0 | 0.0 | 33.3 | 0.0 | 8.3 |
| one-shot, BM25 only | 0.0 | 0.0 | 16.7 | 0.0 | 4.2 |
| one-shot, wsum BM25+Qwen3-Emb | 0.0 | 0.0 | 33.3 | 8.3 | 10.4 |

### Paired vs one-shot

| arm vs one-shot | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| decomposition (LLM, <=4, RRF union) | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| decomposition (LLM, <=4, RRF union) | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| decomposition (LLM, <=4, RRF union) | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| decomposition (LLM, <=4, RRF union) | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| decomposition (LLM, <=4, RRF union) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| facet decomposition (deterministic) | ALL | +1 / −1 | +0.0 [-6.2, +6.2] | 1 |
| facet decomposition (deterministic) | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| facet decomposition (deterministic) | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| facet decomposition (deterministic) | goal | +1 / −1 | +0.0 [-25.0, +25.0] | 1 |
| facet decomposition (deterministic) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| gap-check (<=2 rounds) | ALL | +1 / −1 | +0.0 [-6.2, +6.2] | 1 |
| gap-check (<=2 rounds) | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| gap-check (<=2 rounds) | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| gap-check (<=2 rounds) | goal | +1 / −1 | +0.0 [-25.0, +25.0] | 1 |
| gap-check (<=2 rounds) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| cards+slots + one-shot | ALL | +9 / −1 | +16.7 [+6.2, +29.2] | 0.021 |
| cards+slots + one-shot | decision | +3 / −0 | +25.0 [+0.0, +50.0] | 0.25 |
| cards+slots + one-shot | option | +3 / −0 | +25.0 [+0.0, +50.0] | 0.25 |
| cards+slots + one-shot | goal | +3 / −1 | +16.7 [-16.7, +50.0] | 0.62 |
| cards+slots + one-shot | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| cards+slots + decomposition | ALL | +7 / −0 | +14.6 [+6.2, +25.0] | 0.016 |
| cards+slots + decomposition | decision | +2 / −0 | +16.7 [+0.0, +41.7] | 0.5 |
| cards+slots + decomposition | option | +2 / −0 | +16.7 [+0.0, +41.7] | 0.5 |
| cards+slots + decomposition | goal | +3 / −0 | +25.0 [+0.0, +50.0] | 0.25 |
| cards+slots + decomposition | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| cards+slots + gap-check queries | ALL | +8 / −1 | +14.6 [+4.2, +27.1] | 0.039 |
| cards+slots + gap-check queries | decision | +3 / −0 | +25.0 [+0.0, +50.0] | 0.25 |
| cards+slots + gap-check queries | option | +4 / −0 | +33.3 [+8.3, +58.3] | 0.12 |
| cards+slots + gap-check queries | goal | +1 / −1 | +0.0 [-25.0, +25.0] | 1 |
| cards+slots + gap-check queries | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| cards+slots + facets | ALL | +7 / −1 | +12.5 [+2.1, +25.0] | 0.07 |
| cards+slots + facets | decision | +2 / −0 | +16.7 [+0.0, +41.7] | 0.5 |
| cards+slots + facets | option | +2 / −0 | +16.7 [+0.0, +41.7] | 0.5 |
| cards+slots + facets | goal | +3 / −1 | +16.7 [-16.7, +50.0] | 0.62 |
| cards+slots + facets | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, bge-small dense | ALL | +0 / −1 | -2.1 [-6.2, +0.0] | 1 |
| one-shot, bge-small dense | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, bge-small dense | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, bge-small dense | goal | +0 / −1 | -8.3 [-25.0, +0.0] | 1 |
| one-shot, bge-small dense | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, Qwen3-Emb dense | ALL | +0 / −1 | -2.1 [-6.2, +0.0] | 1 |
| one-shot, Qwen3-Emb dense | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, Qwen3-Emb dense | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, Qwen3-Emb dense | goal | +0 / −1 | -8.3 [-25.0, +0.0] | 1 |
| one-shot, Qwen3-Emb dense | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, BM25 only | ALL | +0 / −3 | -6.2 [-12.5, +0.0] | 0.25 |
| one-shot, BM25 only | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, BM25 only | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, BM25 only | goal | +0 / −3 | -25.0 [-50.0, +0.0] | 0.25 |
| one-shot, BM25 only | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, wsum BM25+Qwen3-Emb | ALL | +0 / −2 | -4.2 [-10.4, +0.0] | 0.5 |
| one-shot, wsum BM25+Qwen3-Emb | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, wsum BM25+Qwen3-Emb | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| one-shot, wsum BM25+Qwen3-Emb | goal | +0 / −2 | -16.7 [-41.7, +0.0] | 0.5 |
| one-shot, wsum BM25+Qwen3-Emb | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |

### Paired vs one-shot, item recall@10

| arm vs one-shot | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| decomposition (LLM, <=4, RRF union) | ALL | +11 / −8 | +1.5 [-3.8, +6.9] | 0.65 |
| facet decomposition (deterministic) | ALL | +10 / −4 | +3.3 [-1.3, +8.2] | 0.18 |
| gap-check (<=2 rounds) | ALL | +11 / −8 | +0.3 [-5.7, +5.6] | 0.65 |
| cards+slots + one-shot | ALL | +35 / −3 | +29.2 [+21.1, +37.1] | 6.7e-08 |
| cards+slots + decomposition | ALL | +32 / −1 | +28.6 [+21.2, +36.3] | 7.9e-09 |
| cards+slots + gap-check queries | ALL | +33 / −3 | +28.8 [+20.0, +37.0] | 2.3e-07 |
| cards+slots + facets | ALL | +33 / −3 | +26.7 [+19.2, +34.5] | 2.3e-07 |
| one-shot, bge-small dense | ALL | +3 / −9 | -3.0 [-6.8, +0.6] | 0.15 |
| one-shot, Qwen3-Emb dense | ALL | +6 / −16 | -5.8 [-12.3, +0.3] | 0.052 |
| one-shot, BM25 only | ALL | +5 / −16 | -8.6 [-14.4, -3.2] | 0.027 |
| one-shot, wsum BM25+Qwen3-Emb | ALL | +8 / −12 | -4.0 [-10.6, +2.9] | 0.5 |

### With the structural prefix, paired vs cards+slots + one-shot

| arm vs cards+slots + one-shot | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| cards+slots + decomposition | ALL | +2 / −3 | -2.1 [-12.5, +6.3] | 1 |
| cards+slots + gap-check queries | ALL | +2 / −3 | -2.1 [-12.5, +6.2] | 1 |
| cards+slots + facets | ALL | +0 / −2 | -4.2 [-10.4, +0.0] | 0.5 |

### Calls and latency (LLM on this CPU)

| seed | decomposition calls | wall s | mean sub-queries | share at cap (4) | gap-check calls (all rounds) | gap wall s | gap calls/task | gap queries/task | round-2 continued |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 48 | 0 | 3.88 | 92% | 95 | 0 | 1.98 | 5.23 | 44 |

### Examples

- **decision_support** — "question: equity's up on the Bramley terrace, thinking about the next purchase — what do I need to weigh up? cheers"
  - decomposition: ['equity value of Bramley terrace property', 'property equity calculation', 'Bramley terrace investment assessment', 'Bramley terrace purchase budget']
  - gap-check: ['Purchase price or target price for Bramley terrace', 'Current buffer goal for the offset', 'Competitiveness of 5.89% and 6.19%', 'Purchase budget or financing options', 'Comparable property rentals', 'Offset buffer goal details']
  - facets: ['73 Whistler Avenue, Bramley current valuation loan balance interest rate', 'The Olive Press ', 'investment strategy maximum portfolio LVR rule offset balance', "question: equity's up on the Bramley terrace, thinking about the next purchase — what do I need to weigh up? cheers decision rule goal policy"]
- **decision_support** — "Hey, is it worth switching lenders on Juniper Cres?"
  - decomposition: ['Juniper Cres lender change policy', 'Juniper Cres loan servicing costs', 'Juniper Cres loan application deadline', 'Juniper Cres loan approval threshold']
  - gap-check: ['Current loan terms or agreement for Juniper Cres', 'Comparison of loan options or competitive rates', 'Any existing loan agreements or refinancing options', 'Current loan balance for Juniper Cres', 'Competitive interest rates for Juniper Cres loan', 'Details about the current lender and their terms']
  - facets: ['4 Juniper Crescent, Redcliff current valuation loan balance interest rate', 'investment strategy maximum portfolio LVR rule offset balance', 'Hey, is it worth switching lenders on Juniper Cres? decision rule goal policy']
- **decision_support** — "quick one — should we move Siobhan onto a different membership? asap"
  - decomposition: ["Siobhan's current membership type", "Siobhan's membership plan details", "Siobhan's membership status", "Siobhan's current membership type"]
  - gap-check: ['Siobhan Abara membership plan details', 'Why Siobhan should be moved to a different membership', 'Any specific criteria or reasons for moving Si', "Siobhan's current membership plan", "Siobhan's current membership plan details", "Siobhan's membership plan change date or"]
  - facets: ['Siobhan Abara membership plan training program assigned coach', 'active memberships membership target standard membership price', 'quick one — should we move Siobhan onto a different membership? asap decision rule goal policy']
- **option_analysis** — "hey, options for improving the return on the Whistler Avenue terrace?"
  - decomposition: ['return on investment for Whistler Avenue terrace', 'real estate appreciation rate for Whistler Avenue terrace', 'rental income projections for Whistler Avenue terrace', 'capital appreciation goals for Whistler Avenue terrace']
  - gap-check: ["Current tenant's name or contact information", 'Proposed renovation or development plans', 'Expected return on investment or ROI calculation', "Current tenant's name and contact details for Whistler Avenue terrace", 'Details about the Elsbury renovation', 'Proposed financing options for the Whistler']
  - facets: ['73 Whistler Avenue, Bramley current valuation loan balance interest rate', 'The Olive Press ', 'investment strategy maximum portfolio LVR rule offset balance', 'hey, options for improving the return on the Whistler Avenue terrace? decision rule goal policy']
- **option_analysis** — "Can you check: how could Corey lift client retention — options? asap"
  - decomposition: ['Check: client retention strategies', 'client retention strategies', 'client retention options', 'client retention plan']
  - gap-check: ['Client retention targets for other clients', 'Specific strategies or actions to improve client retention', 'Metrics or KPIs related to client retention', 'Specific retention targets for Corey', 'Current retention rate for Corey']
  - facets: ['Corey Lin 12-month client retention retention target', 'active memberships membership target standard membership price', 'Can you check: how could Corey lift client retention — options? asap decision rule goal policy']
- **option_analysis** — "Can you check: what are our options on the tenant issue at the Granite Falls house?"
  - decomposition: ['Check tenant agreement terms', 'Granite Falls house tenancy rules', 'tenant agreement details', 'tenant issue options at Granite Falls house']
  - gap-check: ['Tenant agreement or lease terms for the Granite Falls house', 'Tenant payment history or payment plan options', 'Tenant communication or dispute resolution process', 'Tenant agreement terms or conditions', 'Pet bond requirements or process', 'Rental income forecast or budget']
  - facets: ['69 Kurrajong Place, Granite Falls current valuation loan balance interest rate', 'Granite Insurance units held market value', 'investment strategy maximum portfolio LVR rule offset balance', 'Can you check: what are our options on the tenant issue at the Granite Falls house? decision rule goal policy']
- **goal_tracking** — "need to know: am I getting there with my goal?"
  - decomposition: ['goal', 'goal target', 'personal goal', 'goal statement']
  - gap-check: ['Kai Reyes · member goal: Kai Reyes | member goal | deadlift 150 kg by end of 2026 | from 2026-01-03', "Kai Reyes' current goal or progress tracking system", 'Specific date or timeline for achieving the deadlift goal', 'Any additional goals or challenges set for Kai Reyes']
  - facets: ['Kai Reyes membership plan training program assigned coach', 'active memberships membership target standard membership price', 'need to know: am I getting there with my goal? decision rule goal policy']
- **goal_tracking** — "Ok so how are we going on the safety goal at Stonefield"
  - decomposition: ['Stonefield Builders safety goal', 'stonefield builders safety target or goal']
  - gap-check: ['Safety goal details', 'Specific metrics or KPIs related to the safety goal', "Any documentation or records of the safety goal's implementation or review", 'Safety goal progress tracking system', 'Specific metrics or KPIs for the safety goal', 'Timeline or deadline for achieving the safety target']
  - facets: ['Stonefield Builders contracted pipeline value active projects concrete supplier', 'The Olive Press ', 'contracted pipeline value tender policy site supervisor', 'Ok so how are we going on the safety goal at Stonefield decision rule goal policy']

## N4 — entity linkers (20 distinct sets per class per seed)

### Linker recall of required fact entities (mean per task; share of tasks with ALL required entities linked)

| linker | decision | option | current | temporal | goal | pref | cross | multimodal | ALL | all-linked (ALL) | precision | mean entities linked | seeds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lexical | 43 | 85 | 92 | 92 | 98 | 36 | 55 | – | 74 | 65 | 57 | 1.5 | seeds [1, 2] |
| embedding@3 | 52 | 92 | 100 | 100 | 99 | 67 | 52 | – | 81 | 74 | 28 | 2.9 | seeds [1, 2] |
| embedding@5 | 53 | 95 | 100 | 100 | 99 | 71 | 55 | – | 83 | 75 | 20 | 4.7 | seeds [1, 2] |
| lexical+embedding@3 | 53 | 95 | 100 | 100 | 99 | 71 | 57 | – | 83 | 75 | 21 | 4.7 | seeds [1, 2] |
| lexical [LLM subsample] | 47 | 67 | 100 | 100 | 100 | 50 | 6 | – | 69 | 61 | 56 | 1.4 | seeds [1] |
| embedding@3 [LLM subsample] | 64 | 83 | 100 | 100 | 100 | 100 | 17 | – | 79 | 71 | 28 | 2.9 | seeds [1] |
| embedding@5 [LLM subsample] | 64 | 83 | 100 | 100 | 100 | 100 | 17 | – | 79 | 71 | 20 | 4.6 | seeds [1] |
| lexical+embedding@3 [LLM subsample] | 64 | 83 | 100 | 100 | 100 | 100 | 17 | – | 79 | 71 | 22 | 4.4 | seeds [1] |
| LLM-assisted (picks from lexical+embedding@15) | 64 | 83 | 50 | 100 | 83 | 75 | 6 | – | 65 | 58 | 29 | 2.6 | seeds [1] |
| lexical + LLM-assisted | 64 | 83 | 100 | 100 | 100 | 100 | 6 | – | 77 | 71 | 30 | 3.2 | seeds [1] |
| candidates@15 (ceiling of LLM linker) | 64 | 83 | 100 | 100 | 100 | 100 | 17 | – | 79 | 71 | 12 | 13.4 | seeds [1] |

### CR@10 with cards(<=3) + static slots + query, by linker

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| lexical | 12.5 [5–26] | 20.0 [10–35] | 97.5 [87–100] | 40.0 [26–55] | 55.0 [40–69] | 12.5 [5–26] | 7.5 [3–20] | 65.0 [50–78] | 38.8 [34–44] |
| embedding@3 | 10.0 [4–23] | 17.5 [9–32] | 100.0 [91–100] | 42.5 [29–58] | 55.0 [40–69] | 12.5 [5–26] | 2.5 [0–13] | 65.0 [50–78] | 38.1 [33–44] |
| embedding@5 | 10.0 [4–23] | 17.5 [9–32] | 100.0 [91–100] | 42.5 [29–58] | 55.0 [40–69] | 15.0 [7–29] | 2.5 [0–13] | 65.0 [50–78] | 38.4 [33–44] |
| lexical+embedding@3 | 10.0 [4–23] | 17.5 [9–32] | 100.0 [91–100] | 42.5 [29–58] | 55.0 [40–69] | 15.0 [7–29] | 5.0 [1–17] | 65.0 [50–78] | 38.8 [34–44] |
| lexical [LLM subsample] | 50.0 [19–81] | 33.3 [10–70] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 52.1 [38–66] |
| embedding@3 [LLM subsample] | 33.3 [10–70] | 16.7 [3–56] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 47.9 [34–62] |
| embedding@5 [LLM subsample] | 33.3 [10–70] | 16.7 [3–56] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 47.9 [34–62] |
| lexical+embedding@3 [LLM subsample] | 33.3 [10–70] | 16.7 [3–56] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 47.9 [34–62] |
| LLM-assisted (picks from lexical+embedding@15) | 33.3 [10–70] | 16.7 [3–56] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 47.9 [34–62] |
| lexical + LLM-assisted | 33.3 [10–70] | 16.7 [3–56] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 47.9 [34–62] |
| candidates@15 (ceiling of LLM linker) | 33.3 [10–70] | 16.7 [3–56] | 100.0 [61–100] | 50.0 [19–81] | 66.7 [30–90] | 16.7 [3–56] | 0.0 [0–39] | 100.0 [61–100] | 47.9 [34–62] |
| *n sets (tasks)* | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 320 (320) |

(paired tests use only the seeds both linkers ran on)

| arm vs lexical | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| embedding@3 | ALL | +3 / −5 | -0.6 [-2.5, +0.9] | 0.73 |
| embedding@3 | decision | +0 / −1 | -2.5 [-10.0, +0.0] | 1 |
| embedding@3 | option | +1 / −2 | -2.5 [-10.1, +5.0] | 1 |
| embedding@3 | current | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| embedding@3 | temporal | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| embedding@3 | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 | cross | +0 / −2 | -5.0 [-12.5, +0.0] | 0.5 |
| embedding@3 | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 | ALL | +4 / −5 | -0.3 [-2.2, +1.6] | 1 |
| embedding@5 | decision | +0 / −1 | -2.5 [-10.0, +0.0] | 1 |
| embedding@5 | option | +1 / −2 | -2.5 [-10.1, +5.0] | 1 |
| embedding@5 | current | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| embedding@5 | temporal | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| embedding@5 | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 | pref | +1 / −0 | +2.5 [+0.0, +10.0] | 1 |
| embedding@5 | cross | +0 / −2 | -5.0 [-12.5, +0.0] | 0.5 |
| embedding@5 | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 | ALL | +4 / −4 | +0.0 [-1.9, +1.6] | 1 |
| lexical+embedding@3 | decision | +0 / −1 | -2.5 [-10.0, +0.0] | 1 |
| lexical+embedding@3 | option | +1 / −2 | -2.5 [-10.1, +5.0] | 1 |
| lexical+embedding@3 | current | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| lexical+embedding@3 | temporal | +1 / −0 | +2.5 [+0.0, +7.5] | 1 |
| lexical+embedding@3 | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 | pref | +1 / −0 | +2.5 [+0.0, +10.0] | 1 |
| lexical+embedding@3 | cross | +0 / −1 | -2.5 [-7.5, +0.0] | 1 |
| lexical+embedding@3 | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | decision | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| lexical [LLM subsample] | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| lexical [LLM subsample] | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical [LLM subsample] | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | ALL | +0 / −1 | -7.7 [-23.1, +0.0] | 1 |
| embedding@3 [LLM subsample] | decision | +0 / −1 | -16.7 [-50.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| embedding@3 [LLM subsample] | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| embedding@3 [LLM subsample] | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | ALL | +0 / −1 | -7.7 [-23.1, +0.0] | 1 |
| embedding@5 [LLM subsample] | decision | +0 / −1 | -16.7 [-50.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| embedding@5 [LLM subsample] | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| embedding@5 [LLM subsample] | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | ALL | +0 / −1 | -7.7 [-23.1, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | decision | +0 / −1 | -16.7 [-50.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| lexical+embedding@3 [LLM subsample] | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| lexical+embedding@3 [LLM subsample] | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | ALL | +0 / −1 | -7.7 [-23.1, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | decision | +0 / −1 | -16.7 [-50.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical + LLM-assisted | ALL | +0 / −1 | -7.7 [-23.1, +0.0] | 1 |
| lexical + LLM-assisted | decision | +0 / −1 | -16.7 [-50.0, +0.0] | 1 |
| lexical + LLM-assisted | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical + LLM-assisted | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| lexical + LLM-assisted | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| lexical + LLM-assisted | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical + LLM-assisted | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical + LLM-assisted | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical + LLM-assisted | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | ALL | +0 / −1 | -7.7 [-23.1, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | decision | +0 / −1 | -16.7 [-50.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | option | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | current | +0 / −0 | +nan [+nan, +nan] | 1 |
| candidates@15 (ceiling of LLM linker) | temporal | +0 / −0 | +nan [+nan, +nan] | 1 |
| candidates@15 (ceiling of LLM linker) | goal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | pref | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | cross | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | multimodal | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |

### CR@10 with cards(<=5) + query (no static slots), by linker

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| lexical | 2.5 | 20.0 | 97.5 | 67.5 | 55.0 | 12.5 | 0.0 | 75.0 | 41.2 |
| embedding@3 | 2.5 | 20.0 | 100.0 | 55.0 | 55.0 | 12.5 | 0.0 | 72.5 | 39.7 |
| embedding@5 | 2.5 | 20.0 | 100.0 | 37.5 | 55.0 | 12.5 | 0.0 | 65.0 | 36.6 |
| lexical+embedding@3 | 2.5 | 20.0 | 100.0 | 42.5 | 55.0 | 15.0 | 0.0 | 65.0 | 37.5 |
| lexical [LLM subsample] | 0.0 | 16.7 | 100.0 | 66.7 | 66.7 | 16.7 | 0.0 | 100.0 | 45.8 |
| embedding@3 [LLM subsample] | 0.0 | 16.7 | 100.0 | 66.7 | 66.7 | 16.7 | 0.0 | 100.0 | 45.8 |
| embedding@5 [LLM subsample] | 0.0 | 16.7 | 100.0 | 50.0 | 66.7 | 16.7 | 0.0 | 100.0 | 43.8 |
| lexical+embedding@3 [LLM subsample] | 0.0 | 16.7 | 100.0 | 66.7 | 66.7 | 16.7 | 0.0 | 100.0 | 45.8 |
| LLM-assisted (picks from lexical+embedding@15) | 0.0 | 16.7 | 100.0 | 66.7 | 66.7 | 16.7 | 0.0 | 100.0 | 45.8 |
| lexical + LLM-assisted | 0.0 | 16.7 | 100.0 | 66.7 | 66.7 | 16.7 | 0.0 | 100.0 | 45.8 |
| candidates@15 (ceiling of LLM linker) | 0.0 | 16.7 | 100.0 | 50.0 | 66.7 | 16.7 | 0.0 | 100.0 | 43.8 |
| *n sets (tasks)* | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 40 (40) | 320 (320) |

| arm vs lexical | class | sets better / worse | Δ pp [95% cluster-bootstrap CI] | exact sign-test p |
|---|---|---|---|---|
| embedding@3 | ALL | +2 / −7 | -1.6 [-3.4, +0.0] | 0.18 |
| embedding@5 | ALL | +3 / −18 | -4.7 [-7.2, -2.2] | 0.0015 |
| lexical+embedding@3 | ALL | +4 / −16 | -3.8 [-6.2, -1.2] | 0.012 |
| lexical [LLM subsample] | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@3 [LLM subsample] | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| embedding@5 [LLM subsample] | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical+embedding@3 [LLM subsample] | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| LLM-assisted (picks from lexical+embedding@15) | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| lexical + LLM-assisted | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |
| candidates@15 (ceiling of LLM linker) | ALL | +0 / −0 | +0.0 [+0.0, +0.0] | 1 |

LLM linker cost: seed 1: 48 calls, 0 s

## H13-lite — index-time origin enrichment vs query-side LLM expansion (multimodal, seed 1, 16 distinct sets, best first stage)

| arm | CR@10 | item recall@10 | n sets |
|---|---|---|---|
| caption-only index + raw query | 50.0 [28–72] | 59.4 | 16 |
| caption-only index + LLM query expansion | 50.0 [28–72] | 62.5 | 16 |
| origin-enriched index + raw query | 81.2 [57–93] | 87.5 | 16 |
| origin-enriched index + LLM query expansion | 81.2 [57–93] | 87.5 | 16 |

caption-only index + LLM query expansion vs caption-only index + raw query: +0 / −0, Δ +0.0 pp [+0.0, +0.0], p=1.

origin-enriched index + raw query vs caption-only index + raw query: +5 / −0, Δ +31.2 pp [+12.5, +56.2], p=0.062.

origin-enriched index + LLM query expansion vs origin-enriched index + raw query: +1 / −1, Δ +0.0 pp [-18.8, +18.8], p=1.

origin-enriched index + raw query vs caption-only index + LLM query expansion: +5 / −0, Δ +31.2 pp [+12.5, +56.2], p=0.062.

Expansion cost: seed 1: 16 calls, 0 s

## H11-lite — SigLIP2 image vectors vs text twins on synthetic TEXT-BEARING images (whiteboards, menu boards, receipts, report pages rendered from their OCR text); within-media search; 124 tasks over 3 seeds, 247 rendered media items per seed

| arm | CR@10 | item recall@10 | n sets |
|---|---|---|---|
| text twin, hybrid (system first stage) | 97.5 [92–99] | 98.0 | 99 |
| text twin, dense (caption+OCR+origin) | 91.4 [84–95] | 93.1 | 99 |
| text twin without OCR, dense (caption+origin) | 98.5 [94–100] | 98.8 | 99 |
| SigLIP2 image only | 61.1 [51–70] | 62.9 | 99 |
| RRF(text twin without OCR, SigLIP2 image) | 78.8 [70–86] | 79.8 | 99 |
| RRF(text twin dense, SigLIP2 image) | 82.3 [74–89] | 81.9 | 99 |

RRF(text twin without OCR, SigLIP2 image) vs text twin without OCR, dense (caption+origin): +0 / −22, Δ -19.7 pp [-27.3, -12.6], p=4.8e-07.

RRF(text twin dense, SigLIP2 image) vs text twin, dense (caption+OCR+origin): +1 / −10, Δ -9.1 pp [-15.2, -3.5], p=0.012.

SigLIP2 image only vs text twin without OCR, dense (caption+origin): +0 / −40, Δ -37.4 pp [-47.0, -28.3], p=1.8e-12.

SigLIP2-base image encoding on this CPU (fp32): 1.6 img/s, 1.9 img/s, 2.0 img/s

## I2 kill test — LLM-written cards (from dated notes) vs code-compiled cards (from keyed heads)

Checks: keyed facts with >=2 versions where the notes given to the model quote BOTH the current and a superseded value. Code-compiled cards state only the current value by construction (0% stale).

| input order | key checks | states current only | states stale only | states both | states neither | stale value present |
|---|---|---|---|---|---|---|
| random | 15 | 6.7% | 6.7% | 80.0% | 6.7% | **86.7% [62.1–96.3]** |
| newest-first | 15 | 20.0% | 6.7% | 73.3% | 0.0% | **80.0% [54.8–93.0]** |

Example model-written cards (seed 1):

```
[h_cvl / random]
- Corvid Logistics marked at $160k.  
- Corvid Logistics position worth about 140 grand on today's close.  
- Corvid Logistics marked at about 144 grand.  
- Corvid Logistics marked at 160k.  
- Corvid Logistics shares: position is 2,950 units after the last trade.  
- Corvid Logistics portfolio check: Corvid Logistics at $165,600.  
- Corvid Logistics portfolio check: Corvid Logistics at $143,600.
```
```
[h_cvl / newest-first]
- Corvid Logistics marked at $160k on 2026-06-05  
- Corvid Logistics marked at $160k on 2026-06-01  
- Corvid Logistics position worth $140k on 2026-03-28  
- Corvid Logistics position worth about 140 grand on 2026-03-20  
- Corvid Logistics marked at about 144 grand on 2025-11-0
```

## Component throughput (pooled over both hosts: host A = Xeon 2.1 GHz with AMX/bf16; host B = Xeon 2.8 GHz without bf16, fp32 rerankers, emulated-bf16 LLM, shared CPU; see RESULTS_batch2.md for the per-host split)

| component | items | seconds | items/s | ms/item |
|---|---|---|---|---|
| embed-docs:bge-small | 29,431 | 166 | 177.2 | 6 |
| embed-docs:qwen3-emb | 31,946 | 1386 | 23.1 | 43 |
| embed-queries:bge-small | 6,270 | 179 | 35.1 | 28 |
| embed-queries:qwen3-emb | 6,221 | 609 | 10.2 | 98 |
| embed-queries:qwen3-emb-task | 6,313 | 281 | 22.4 | 45 |
| llm:Qwen3-1.7B | 158 | 23953 | 0.0 | 151599 |
| rerank:bge-reranker-v2-m3 | 18,246 | 1322 | 13.8 | 72 |
| rerank:mxbai-rerank-base-v2 | 8,133 | 1864 | 4.4 | 229 |
| rerank:qwen3-reranker | 26,631 | 5704 | 4.7 | 214 |
