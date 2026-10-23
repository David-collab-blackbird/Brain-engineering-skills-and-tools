## GBrain on BrainBench v0.2 seed 1

Rates: mean over distinct required sets, Wilson 95% (n = distinct sets). Batch-2 comparators re-read from results_v02 pickles, same seed and tasks.

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid <6s | 0.0 [0–10] | 2.9 [1–10] | 54.7 [43–65] | 83.3 [55–95] | 3.8 [1–10] | 6.2 [3–14] | 0.0 [0–23] | 74.4 [59–85] | 22.4 [19–27] |
| GB hybrid+cards <6s | 2.9 [1–15] | 13.0 [7–23] | 97.3 [91–99] | 83.3 [55–95] | 38.8 [29–50] | 21.2 [14–31] | 7.7 [1–33] | 79.5 [64–89] | 43.1 [38–48] |
| B2 BM25 | 0.0 [0–10] | 1.4 [0–8] | 48.0 [37–59] | 58.3 [32–81] | 8.8 [4–17] | 6.2 [3–14] | 7.7 [1–33] | 76.9 [62–87] | 21.5 [18–26] |
| B2 bge-small dense | 0.0 [0–10] | 4.3 [1–12] | 66.7 [55–76] | 75.0 [47–91] | 7.5 [3–15] | 6.2 [3–14] | 0.0 [0–23] | 87.2 [73–94] | 26.8 [23–31] |
| B2 rrf(BM25+bge-small) | 0.0 [0–10] | 2.9 [1–10] | 68.0 [57–77] | 75.0 [47–91] | 8.8 [4–17] | 5.0 [2–12] | 7.7 [1–33] | 82.1 [67–91] | 26.4 [22–31] |
| B2 wsum(BM25+bge-small) = query-only | 0.0 [0–10] | 4.3 [1–12] | 73.3 [62–82] | 83.3 [55–95] | 8.8 [4–17] | 5.0 [2–12] | 7.7 [1–33] | 89.7 [76–96] | 28.6 [24–33] |
| B2 cards(<=3)+query | 2.9 [1–15] | 15.9 [9–26] | 98.7 [93–100] | 83.3 [55–95] | 43.8 [33–55] | 11.2 [6–20] | 15.4 [4–42] | 87.2 [73–94] | 43.9 [39–49] |
| B2 cards+slots+query | 11.8 [5–27] | 14.5 [8–25] | 100.0 [95–100] | 33.3 [14–61] | 42.5 [32–53] | 11.2 [6–20] | 7.7 [1–33] | 79.5 [64–89] | 41.9 [37–47] |

### CR@20 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid <6s | 0.0 [0–10] | 8.7 [4–18] | 69.3 [58–79] | 83.3 [55–95] | 8.8 [4–17] | 8.8 [4–17] | 0.0 [0–23] | 87.2 [73–94] | 28.9 [25–34] |
| GB hybrid+cards <6s | 2.9 [1–15] | 20.3 [12–31] | 98.7 [93–100] | 83.3 [55–95] | 41.2 [31–52] | 22.5 [15–33] | 7.7 [1–33] | 89.7 [76–96] | 46.4 [42–51] |
| B2 BM25 | 0.0 [0–10] | 2.9 [1–10] | 61.3 [50–72] | 58.3 [32–81] | 17.5 [11–27] | 6.2 [3–14] | 7.7 [1–33] | 76.9 [62–87] | 26.0 [22–31] |
| B2 bge-small dense | 0.0 [0–10] | 10.1 [5–19] | 77.3 [67–85] | 75.0 [47–91] | 10.0 [5–19] | 7.5 [3–15] | 0.0 [0–23] | 89.7 [76–96] | 30.8 [26–35] |
| B2 rrf(BM25+bge-small) | 0.0 [0–10] | 10.1 [5–19] | 81.3 [71–89] | 91.7 [65–99] | 16.2 [10–26] | 10.0 [5–19] | 7.7 [1–33] | 92.3 [80–97] | 34.0 [30–39] |
| B2 wsum(BM25+bge-small) = query-only | 0.0 [0–10] | 10.1 [5–19] | 84.0 [74–91] | 83.3 [55–95] | 11.2 [6–20] | 8.8 [4–17] | 7.7 [1–33] | 92.3 [80–97] | 33.1 [29–38] |

### CR@50 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid <6s | 2.9 [1–15] | 14.5 [8–25] | 81.3 [71–89] | 83.3 [55–95] | 11.2 [6–20] | 16.2 [10–26] | 7.7 [1–33] | 92.3 [80–97] | 35.0 [30–40] |
| GB hybrid+cards <6s | 5.9 [2–19] | 24.6 [16–36] | 98.7 [93–100] | 83.3 [55–95] | 47.5 [37–58] | 32.5 [23–43] | 15.4 [4–42] | 92.3 [80–97] | 51.0 [46–56] |
| B2 BM25 | 2.9 [1–15] | 11.6 [6–21] | 74.7 [64–83] | 91.7 [65–99] | 21.2 [14–31] | 8.8 [4–17] | 7.7 [1–33] | 89.7 [76–96] | 33.8 [29–39] |
| B2 bge-small dense | 0.0 [0–10] | 17.4 [10–28] | 90.7 [82–95] | 91.7 [65–99] | 18.8 [12–29] | 17.5 [11–27] | 0.0 [0–23] | 94.9 [83–99] | 39.2 [35–44] |
| B2 rrf(BM25+bge-small) | 2.9 [1–15] | 18.8 [11–30] | 90.7 [82–95] | 91.7 [65–99] | 27.5 [19–38] | 16.2 [10–26] | 7.7 [1–33] | 92.3 [80–97] | 41.0 [36–46] |
| B2 wsum(BM25+bge-small) = query-only | 2.9 [1–15] | 20.3 [12–31] | 93.3 [85–97] | 91.7 [65–99] | 26.2 [18–37] | 17.5 [11–27] | 7.7 [1–33] | 94.9 [83–99] | 42.0 [37–47] |

### CR@100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid <6s | 5.9 [2–19] | 24.6 [16–36] | 88.0 [79–94] | 83.3 [55–95] | 23.8 [16–34] | 28.7 [20–39] | 7.7 [1–33] | 92.3 [80–97] | 43.2 [38–48] |
| GB hybrid+cards <6s | 8.8 [3–23] | 31.9 [22–44] | 98.7 [93–100] | 83.3 [55–95] | 58.8 [48–69] | 38.8 [29–50] | 15.4 [4–42] | 92.3 [80–97] | 56.0 [51–61] |
| B2 BM25 | 8.8 [3–23] | 17.4 [10–28] | 84.0 [74–91] | 91.7 [65–99] | 22.5 [15–33] | 8.8 [4–17] | 7.7 [1–33] | 92.3 [80–97] | 37.5 [33–42] |
| B2 bge-small dense | 2.9 [1–15] | 21.7 [14–33] | 96.0 [89–99] | 91.7 [65–99] | 45.0 [35–56] | 30.0 [21–41] | 0.0 [0–23] | 94.9 [83–99] | 49.0 [44–54] |
| B2 rrf(BM25+bge-small) | 8.8 [3–23] | 23.2 [15–34] | 94.7 [87–98] | 100.0 [76–100] | 43.8 [33–55] | 33.8 [24–45] | 15.4 [4–42] | 97.4 [87–100] | 50.7 [46–56] |
| B2 wsum(BM25+bge-small) = query-only | 5.9 [2–19] | 26.1 [17–38] | 96.0 [89–99] | 91.7 [65–99] | 46.2 [36–57] | 32.5 [23–43] | 7.7 [1–33] | 97.4 [87–100] | 51.0 [46–56] |

### Item recall@10 / @100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid <6s | 21.7 / 49.3 | 29.6 / 62.0 | 58.9 / 89.6 | 83.3 / 87.5 | 38.2 / 68.4 | 27.9 / 47.2 | 28.2 / 48.8 | 78.2 / 96.2 | 42.1 / 68.1 |
| GB hybrid+cards <6s | 51.7 / 61.7 | 64.6 / 75.2 | 98.0 / 98.7 | 91.7 / 91.7 | 78.4 / 86.0 | 39.2 / 52.9 | 45.1 / 60.3 | 83.3 / 96.2 | 69.4 / 78.2 |

### Paired tests (CR@10, distinct sets; exact sign test; Δ = arm − comparator, cluster-bootstrap 95% CI)

| arm | vs | class | better/worse | Δ pp [CI] | p |
|---|---|---|---|---|---|
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | ALL | +3/−28 | -6.2 [-9.0, -3.8] | 4.6e-06 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | option | +1/−2 | -1.4 [-7.2, +2.9] | 1 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | current | +1/−15 | -18.7 [-29.3, -9.3] | 0.00052 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | goal | +0/−4 | -5.0 [-10.0, -1.2] | 0.12 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | pref | +1/−0 | +1.2 [+0.0, +3.8] | 1 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | cross | +0/−1 | -7.7 [-23.1, +0.0] | 1 |
| GB hybrid <6s | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−7 | -15.4 [-28.2, -2.6] | 0.07 |
| GB hybrid <6s | B2 cards(<=3)+query | ALL | +2/−88 | -21.5 [-26.0, -17.5] | 6.6e-24 |
| GB hybrid <6s | B2 cards(<=3)+query | decision | +0/−1 | -2.9 [-8.8, +0.0] | 1 |
| GB hybrid <6s | B2 cards(<=3)+query | option | +1/−10 | -13.0 [-21.7, -4.3] | 0.012 |
| GB hybrid <6s | B2 cards(<=3)+query | current | +0/−33 | -44.0 [-56.0, -32.0] | 2.3e-10 |
| GB hybrid <6s | B2 cards(<=3)+query | temporal | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid <6s | B2 cards(<=3)+query | goal | +0/−32 | -40.0 [-50.0, -30.0] | 4.7e-10 |
| GB hybrid <6s | B2 cards(<=3)+query | pref | +1/−5 | -5.0 [-11.2, +0.0] | 0.22 |
| GB hybrid <6s | B2 cards(<=3)+query | cross | +0/−2 | -15.4 [-38.5, +0.0] | 0.5 |
| GB hybrid <6s | B2 cards(<=3)+query | multimodal | +1/−6 | -12.8 [-25.6, +0.0] | 0.12 |
| GB hybrid <6s | B2 bge-small dense | ALL | +6/−23 | -4.4 [-7.0, -1.9] | 0.0023 |
| GB hybrid <6s | B2 bge-small dense | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid <6s | B2 bge-small dense | option | +1/−2 | -1.4 [-7.2, +2.9] | 1 |
| GB hybrid <6s | B2 bge-small dense | current | +3/−12 | -12.0 [-21.3, -2.7] | 0.035 |
| GB hybrid <6s | B2 bge-small dense | temporal | +1/−0 | +8.3 [+0.0, +25.0] | 1 |
| GB hybrid <6s | B2 bge-small dense | goal | +0/−3 | -3.8 [-8.8, +0.0] | 0.25 |
| GB hybrid <6s | B2 bge-small dense | pref | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid <6s | B2 bge-small dense | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid <6s | B2 bge-small dense | multimodal | +1/−6 | -12.8 [-25.6, +0.0] | 0.12 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | ALL | +67/−9 | +14.5 [+10.2, +18.8] | 4.3e-12 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | decision | +1/−0 | +2.9 [+0.0, +8.8] | 1 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | option | +8/−2 | +8.7 [+0.0, +17.4] | 0.11 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | current | +19/−1 | +24.0 [+14.7, +34.7] | 4e-05 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | goal | +25/−1 | +30.0 [+18.8, +41.2] | 8e-07 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | pref | +13/−0 | +16.2 [+8.8, +23.8] | 0.00024 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | cross | +1/−1 | +0.0 [-23.1, +23.1] | 1 |
| GB hybrid+cards <6s | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−5 | -10.3 [-23.1, +0.0] | 0.22 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | ALL | +13/−16 | -0.8 [-3.5, +2.0] | 0.71 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | option | +3/−5 | -2.9 [-11.6, +4.3] | 0.73 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | current | +0/−1 | -1.3 [-4.0, +0.0] | 1 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | temporal | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | goal | +2/−6 | -5.0 [-12.5, +1.2] | 0.29 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | pref | +8/−0 | +10.0 [+3.8, +16.2] | 0.0078 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | cross | +0/−1 | -7.7 [-23.1, +0.0] | 1 |
| GB hybrid+cards <6s | B2 cards(<=3)+query | multimodal | +1/−4 | -7.7 [-17.9, +2.6] | 0.38 |
| GB hybrid+cards <6s | B2 bge-small dense | ALL | +74/−8 | +16.4 [+12.4, +20.6] | 1.6e-14 |
| GB hybrid+cards <6s | B2 bge-small dense | decision | +1/−0 | +2.9 [+0.0, +8.8] | 1 |
| GB hybrid+cards <6s | B2 bge-small dense | option | +8/−2 | +8.7 [+0.0, +17.4] | 0.11 |
| GB hybrid+cards <6s | B2 bge-small dense | current | +24/−1 | +30.7 [+20.0, +41.3] | 1.5e-06 |
| GB hybrid+cards <6s | B2 bge-small dense | temporal | +1/−0 | +8.3 [+0.0, +25.0] | 1 |
| GB hybrid+cards <6s | B2 bge-small dense | goal | +26/−1 | +31.2 [+20.0, +42.5] | 4.2e-07 |
| GB hybrid+cards <6s | B2 bge-small dense | pref | +12/−0 | +15.0 [+7.5, +22.5] | 0.00049 |
| GB hybrid+cards <6s | B2 bge-small dense | cross | +1/−0 | +7.7 [+0.0, +23.1] | 1 |
| GB hybrid+cards <6s | B2 bge-small dense | multimodal | +1/−4 | -7.7 [-17.9, +2.6] | 0.38 |

### Leakage, latency, errors

| arm | returned rows from ungranted sources | tasks with any | tasks | p50 / p95 ms per search | errors |
|---|---|---|---|---|---|
| GB hybrid <6s | 0 | 0 | 540 | 3284 / 5566 | 0 |
| GB hybrid+cards <6s | 0 | 0 | 540 | 3284 / 5566 | 0 |

### Stale probes (E1 definitions; top-10)

| arm | n | stale version above current | stale-quoting note above current | current value missing from top-10 | first value-bearing item stale |
|---|---|---|---|---|---|
| GB hybrid <6s | 138 | 46.4% [38.3–54.7] (64) | 44.9% [36.9–53.3] (62) | 37.0% [29.4–45.3] (51) | 57.9% [48.7–66.6] (66/114) |
| GB hybrid+cards <6s | 138 | 0.0% [0.0–2.7] (0) | 44.9% [36.9–53.3] (62) | 32.6% [25.4–40.8] (45) | 41.2% [32.6–50.4] (47/114) |
