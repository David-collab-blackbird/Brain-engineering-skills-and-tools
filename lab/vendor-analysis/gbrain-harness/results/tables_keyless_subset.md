## GBrain on BrainBench v0.2 seed 1

Rates: mean over distinct required sets, Wilson 95% (n = distinct sets). Batch-2 comparators re-read from results_v02 pickles, same seed and tasks.

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB keyless | 0.0 [0–9] | 0.0 [0–9] | 60.8 [47–73] | 70.0 [55–82] | 2.5 [0–13] | 5.0 [1–17] | 0.0 [0–9] | 52.5 [37–67] | 25.1 [21–30] |
| GB hybrid | 0.0 [0–9] | 2.5 [0–13] | 62.7 [49–75] | 55.0 [40–69] | 2.5 [0–13] | 5.0 [1–17] | 0.0 [0–9] | 72.5 [57–84] | 26.3 [22–31] |
| B2 BM25 | 0.0 [0–9] | 0.0 [0–9] | 56.9 [43–69] | 42.5 [29–58] | 10.0 [4–23] | 5.0 [1–17] | 0.0 [0–9] | 75.0 [60–86] | 24.8 [20–30] |
| B2 bge-small dense | 0.0 [0–9] | 5.0 [1–17] | 70.6 [57–81] | 42.5 [29–58] | 5.0 [1–17] | 5.0 [1–17] | 0.0 [0–9] | 87.5 [74–95] | 28.4 [24–33] |
| B2 rrf(BM25+bge-small) | 0.0 [0–9] | 5.0 [1–17] | 72.5 [59–83] | 52.5 [37–67] | 10.0 [4–23] | 5.0 [1–17] | 0.0 [0–9] | 80.0 [65–90] | 29.6 [25–35] |
| B2 wsum(BM25+bge-small) = query-only | 0.0 [0–9] | 5.0 [1–17] | 78.4 [65–88] | 55.0 [40–69] | 7.5 [3–20] | 5.0 [1–17] | 0.0 [0–9] | 90.0 [77–96] | 31.7 [27–37] |
| B2 cards(<=3)+query | 15.0 [7–29] | 10.0 [4–23] | 100.0 [93–100] | 50.0 [35–65] | 45.0 [31–60] | 15.0 [7–29] | 0.0 [0–9] | 87.5 [74–95] | 42.3 [37–48] |
| B2 cards+slots+query | 27.5 [16–43] | 17.5 [9–32] | 100.0 [93–100] | 30.0 [18–45] | 42.5 [29–58] | 15.0 [7–29] | 7.5 [3–20] | 77.5 [62–88] | 41.7 [37–47] |

### CR@20 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB keyless | 0.0 [0–9] | 10.0 [4–23] | 70.6 [57–81] | 82.5 [68–91] | 7.5 [3–20] | 7.5 [3–20] | 0.0 [0–9] | 55.0 [40–69] | 30.5 [26–36] |
| GB hybrid | 0.0 [0–9] | 10.0 [4–23] | 72.5 [59–83] | 77.5 [62–88] | 7.5 [3–20] | 10.0 [4–23] | 0.0 [0–9] | 77.5 [62–88] | 33.2 [28–38] |
| B2 BM25 | 2.5 [0–13] | 0.0 [0–9] | 64.7 [51–76] | 55.0 [40–69] | 22.5 [12–38] | 5.0 [1–17] | 0.0 [0–9] | 75.0 [60–86] | 29.3 [25–34] |
| B2 bge-small dense | 0.0 [0–9] | 10.0 [4–23] | 78.4 [65–88] | 70.0 [55–82] | 7.5 [3–20] | 7.5 [3–20] | 0.0 [0–9] | 90.0 [77–96] | 34.4 [30–40] |
| B2 rrf(BM25+bge-small) | 0.0 [0–9] | 5.0 [1–17] | 84.3 [72–92] | 70.0 [55–82] | 15.0 [7–29] | 7.5 [3–20] | 0.0 [0–9] | 92.5 [80–97] | 36.0 [31–41] |
| B2 wsum(BM25+bge-small) = query-only | 0.0 [0–9] | 7.5 [3–20] | 86.3 [74–93] | 75.0 [60–86] | 10.0 [4–23] | 7.5 [3–20] | 0.0 [0–9] | 92.5 [80–97] | 36.6 [32–42] |

### CR@50 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB keyless | 15.0 [7–29] | 15.0 [7–29] | 86.3 [74–93] | 95.0 [83–99] | 10.0 [4–23] | 15.0 [7–29] | 0.0 [0–9] | 62.5 [47–76] | 39.0 [34–44] |
| GB hybrid | 5.0 [1–17] | 15.0 [7–29] | 84.3 [72–92] | 90.0 [77–96] | 10.0 [4–23] | 15.0 [7–29] | 0.0 [0–9] | 80.0 [65–90] | 39.0 [34–44] |
| B2 BM25 | 15.0 [7–29] | 7.5 [3–20] | 80.4 [68–89] | 77.5 [62–88] | 25.0 [14–40] | 7.5 [3–20] | 0.0 [0–9] | 87.5 [74–95] | 39.0 [34–44] |
| B2 bge-small dense | 12.5 [5–26] | 22.5 [12–38] | 94.1 [84–98] | 80.0 [65–90] | 10.0 [4–23] | 17.5 [9–32] | 0.0 [0–9] | 90.0 [77–96] | 42.6 [37–48] |
| B2 rrf(BM25+bge-small) | 12.5 [5–26] | 17.5 [9–32] | 92.2 [82–97] | 87.5 [74–95] | 22.5 [12–38] | 12.5 [5–26] | 0.0 [0–9] | 95.0 [83–99] | 44.1 [39–49] |
| B2 wsum(BM25+bge-small) = query-only | 15.0 [7–29] | 20.0 [10–35] | 94.1 [84–98] | 82.5 [68–91] | 20.0 [10–35] | 15.0 [7–29] | 2.5 [0–13] | 95.0 [83–99] | 44.7 [39–50] |

### CR@100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB keyless | 22.5 [12–38] | 27.5 [16–43] | 86.3 [74–93] | 100.0 [91–100] | 27.5 [16–43] | 30.0 [18–45] | 2.5 [0–13] | 92.5 [80–97] | 49.8 [44–55] |
| GB hybrid | 17.5 [9–32] | 25.0 [14–40] | 90.2 [79–96] | 90.0 [77–96] | 17.5 [9–32] | 32.5 [20–48] | 0.0 [0–9] | 95.0 [83–99] | 47.4 [42–53] |
| B2 BM25 | 17.5 [9–32] | 15.0 [7–29] | 84.3 [72–92] | 80.0 [65–90] | 25.0 [14–40] | 7.5 [3–20] | 0.0 [0–9] | 92.5 [80–97] | 41.7 [37–47] |
| B2 bge-small dense | 17.5 [9–32] | 25.0 [14–40] | 98.0 [90–100] | 80.0 [65–90] | 40.0 [26–55] | 30.0 [18–45] | 2.5 [0–13] | 95.0 [83–99] | 50.2 [45–56] |
| B2 rrf(BM25+bge-small) | 22.5 [12–38] | 27.5 [16–43] | 96.1 [87–99] | 90.0 [77–96] | 40.0 [26–55] | 32.5 [20–48] | 5.0 [1–17] | 97.5 [87–100] | 52.9 [47–58] |
| B2 wsum(BM25+bge-small) = query-only | 22.5 [12–38] | 27.5 [16–43] | 96.1 [87–99] | 87.5 [74–95] | 45.0 [31–60] | 30.0 [18–45] | 7.5 [3–20] | 97.5 [87–100] | 53.2 [48–58] |

### Item recall@10 / @100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB keyless | 20.8 / 68.8 | 34.7 / 72.3 | 64.4 / 86.3 | 73.8 / 100.0 | 32.5 / 65.6 | 25.0 / 49.5 | 25.9 / 60.3 | 54.6 / 96.2 | 42.2 / 75.3 |
| GB hybrid | 19.0 / 56.6 | 33.2 / 66.2 | 65.4 / 91.5 | 66.0 / 90.0 | 35.6 / 67.7 | 29.2 / 48.0 | 22.5 / 50.4 | 75.0 / 97.5 | 44.0 / 71.7 |

### Paired tests (CR@10, distinct sets; exact sign test; Δ = arm − comparator, cluster-bootstrap 95% CI)

| arm | vs | class | better/worse | Δ pp [CI] | p |
|---|---|---|---|---|---|
| GB keyless | B2 wsum(BM25+bge-small) = query-only | ALL | +15/−37 | -6.6 [-11.2, -2.4] | 0.0032 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | option | +0/−2 | -5.0 [-12.5, +0.0] | 0.5 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | current | +1/−10 | -17.6 [-29.4, -5.9] | 0.012 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | temporal | +12/−6 | +15.0 [-5.0, +35.0] | 0.24 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | goal | +0/−2 | -5.0 [-12.5, +0.0] | 0.5 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | pref | +1/−1 | +0.0 [-7.5, +7.5] | 1 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB keyless | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−16 | -37.5 [-55.0, -22.5] | 0.00027 |
| GB keyless | B2 cards(<=3)+query | ALL | +16/−73 | -17.2 [-22.7, -12.1] | 7.2e-10 |
| GB keyless | B2 cards(<=3)+query | decision | +0/−6 | -15.0 [-27.5, -5.0] | 0.031 |
| GB keyless | B2 cards(<=3)+query | option | +0/−4 | -10.0 [-20.0, -2.5] | 0.12 |
| GB keyless | B2 cards(<=3)+query | current | +0/−20 | -39.2 [-52.9, -27.5] | 1.9e-06 |
| GB keyless | B2 cards(<=3)+query | temporal | +14/−6 | +20.0 [+0.0, +42.5] | 0.12 |
| GB keyless | B2 cards(<=3)+query | goal | +0/−17 | -42.5 [-57.5, -27.5] | 1.5e-05 |
| GB keyless | B2 cards(<=3)+query | pref | +1/−5 | -10.0 [-22.5, +0.0] | 0.22 |
| GB keyless | B2 cards(<=3)+query | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB keyless | B2 cards(<=3)+query | multimodal | +1/−15 | -35.0 [-52.5, -20.0] | 0.00052 |
| GB keyless | B2 bge-small dense | ALL | +22/−33 | -3.3 [-7.9, +1.2] | 0.18 |
| GB keyless | B2 bge-small dense | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB keyless | B2 bge-small dense | option | +0/−2 | -5.0 [-12.5, +0.0] | 0.5 |
| GB keyless | B2 bge-small dense | current | +4/−9 | -9.8 [-23.5, +3.9] | 0.27 |
| GB keyless | B2 bge-small dense | temporal | +16/−5 | +27.5 [+7.5, +47.5] | 0.027 |
| GB keyless | B2 bge-small dense | goal | +0/−1 | -2.5 [-7.5, +0.0] | 1 |
| GB keyless | B2 bge-small dense | pref | +1/−1 | +0.0 [-7.5, +7.5] | 1 |
| GB keyless | B2 bge-small dense | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB keyless | B2 bge-small dense | multimodal | +1/−15 | -35.0 [-52.5, -20.0] | 0.00052 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | ALL | +7/−25 | -5.4 [-8.8, -2.1] | 0.0021 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | option | +0/−1 | -2.5 [-7.5, +0.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | current | +1/−9 | -15.7 [-27.5, -3.9] | 0.021 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | temporal | +5/−5 | +0.0 [-15.0, +15.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | goal | +0/−2 | -5.0 [-12.5, +0.0] | 0.5 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−8 | -17.5 [-32.5, -5.0] | 0.039 |
| GB hybrid | B2 cards(<=3)+query | ALL | +6/−59 | -16.0 [-20.5, -11.8] | 5e-12 |
| GB hybrid | B2 cards(<=3)+query | decision | +0/−6 | -15.0 [-27.5, -5.0] | 0.031 |
| GB hybrid | B2 cards(<=3)+query | option | +0/−3 | -7.5 [-17.5, +0.0] | 0.25 |
| GB hybrid | B2 cards(<=3)+query | current | +0/−19 | -37.3 [-49.0, -23.5] | 3.8e-06 |
| GB hybrid | B2 cards(<=3)+query | temporal | +5/−3 | +5.0 [-7.5, +17.6] | 0.73 |
| GB hybrid | B2 cards(<=3)+query | goal | +0/−17 | -42.5 [-57.5, -27.5] | 1.5e-05 |
| GB hybrid | B2 cards(<=3)+query | pref | +0/−4 | -10.0 [-20.0, -2.5] | 0.12 |
| GB hybrid | B2 cards(<=3)+query | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 cards(<=3)+query | multimodal | +1/−7 | -15.0 [-27.5, -2.5] | 0.07 |
| GB hybrid | B2 bge-small dense | ALL | +8/−15 | -2.1 [-4.8, +0.6] | 0.21 |
| GB hybrid | B2 bge-small dense | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | option | +0/−1 | -2.5 [-7.5, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | current | +1/−5 | -7.8 [-17.6, +0.0] | 0.22 |
| GB hybrid | B2 bge-small dense | temporal | +6/−1 | +12.5 [+0.0, +25.0] | 0.12 |
| GB hybrid | B2 bge-small dense | goal | +0/−1 | -2.5 [-7.5, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | pref | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | multimodal | +1/−7 | -15.0 [-27.5, -2.5] | 0.07 |

### Leakage, latency, errors

| arm | returned rows from ungranted sources | tasks with any | tasks | p50 / p95 ms per search | errors |
|---|---|---|---|---|---|
| GB keyless | 0 | 0 | 371 | 5504 / 9863 | 0 |
| GB hybrid | 0 | 0 | 371 | 4178 / 9964 | 0 |

### Stale probes (E1 definitions; top-10)

| arm | n | stale version above current | stale-quoting note above current | current value missing from top-10 | first value-bearing item stale |
|---|---|---|---|---|---|
| GB keyless | 40 | 50.0% [35.2–64.8] (20) | 12.5% [5.5–26.1] (5) | 52.5% [37.5–67.1] (21) | 76.0% [56.6–88.5] (19/25) |
| GB hybrid | 40 | 40.0% [26.3–55.4] (16) | 50.0% [35.2–64.8] (20) | 47.5% [32.9–62.5] (19) | 58.8% [42.2–73.6] (20/34) |
