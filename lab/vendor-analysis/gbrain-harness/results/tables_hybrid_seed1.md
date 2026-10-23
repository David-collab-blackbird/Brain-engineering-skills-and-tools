## GBrain on BrainBench v0.2 seed 1

Rates: mean over distinct required sets, Wilson 95% (n = distinct sets). Batch-2 comparators re-read from results_v02 pickles, same seed and tasks.

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | 0.0 [0–5] | 2.5 [1–9] | 57.5 [47–68] | 57.5 [47–68] | 3.8 [1–10] | 6.2 [3–14] | 0.0 [0–5] | 67.5 [57–77] | 24.4 [21–28] |
| GB hybrid keyed | 0.0 [0–5] | 6.2 [3–14] | 63.7 [53–73] | 52.5 [42–63] | 7.5 [3–15] | 6.2 [3–14] | 0.0 [0–5] | 72.5 [62–81] | 26.1 [23–30] |
| GB hybrid+cards | 11.2 [6–20] | 15.0 [9–24] | 97.5 [91–99] | 51.2 [40–62] | 38.8 [29–50] | 21.2 [14–31] | 1.2 [0–7] | 71.2 [61–80] | 38.5 [35–42] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | 0.0 [0–5] | 1.2 [0–7] | 47.5 [37–58] | 45.0 [35–56] | 8.8 [4–17] | 6.2 [3–14] | 1.2 [0–7] | 73.8 [63–82] | 22.9 [20–26] |
| B2 bge-small dense | 0.0 [0–5] | 3.8 [1–10] | 68.8 [58–78] | 55.0 [44–65] | 7.5 [3–15] | 6.2 [3–14] | 0.0 [0–5] | 83.8 [74–90] | 28.2 [25–32] |
| B2 rrf(BM25+bge-small) | 0.0 [0–5] | 2.5 [1–9] | 70.0 [59–79] | 56.2 [45–67] | 8.8 [4–17] | 5.0 [2–12] | 1.2 [0–7] | 81.2 [71–88] | 28.1 [25–32] |
| B2 wsum(BM25+bge-small) = query-only | 0.0 [0–5] | 3.8 [1–10] | 75.0 [65–83] | 57.5 [47–68] | 8.8 [4–17] | 5.0 [2–12] | 1.2 [0–7] | 88.8 [80–94] | 30.0 [27–34] |
| B2 cards(<=3)+query | 10.0 [5–19] | 17.5 [11–27] | 98.8 [93–100] | 55.0 [44–65] | 43.8 [33–55] | 11.2 [6–20] | 2.5 [1–9] | 87.5 [78–93] | 40.8 [37–45] |
| B2 cards+slots+query | 18.8 [12–29] | 17.5 [11–27] | 100.0 [95–100] | 32.5 [23–43] | 42.5 [32–53] | 11.2 [6–20] | 6.2 [3–14] | 76.2 [66–84] | 38.2 [34–42] |

### CR@20 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | 0.0 [0–5] | 7.5 [3–15] | 71.2 [61–80] | 77.5 [67–85] | 8.8 [4–17] | 8.8 [4–17] | 0.0 [0–5] | 76.2 [66–84] | 31.3 [28–35] |
| GB hybrid keyed | 0.0 [0–5] | 7.5 [3–15] | 75.0 [65–83] | 72.5 [62–81] | 8.8 [4–17] | 8.8 [4–17] | 0.0 [0–5] | 77.5 [67–85] | 31.3 [28–35] |
| GB hybrid+cards | 11.2 [6–20] | 21.2 [14–31] | 98.8 [93–100] | 70.0 [59–79] | 41.2 [31–52] | 22.5 [15–33] | 1.2 [0–7] | 77.5 [67–85] | 43.0 [39–47] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | 1.2 [0–7] | 2.5 [1–9] | 60.0 [49–70] | 55.0 [44–65] | 17.5 [11–27] | 6.2 [3–14] | 1.2 [0–7] | 75.0 [65–83] | 27.3 [24–31] |
| B2 bge-small dense | 1.2 [0–7] | 10.0 [5–19] | 78.8 [69–86] | 71.2 [61–80] | 10.0 [5–19] | 7.5 [3–15] | 0.0 [0–5] | 87.5 [78–93] | 33.4 [30–37] |
| B2 rrf(BM25+bge-small) | 1.2 [0–7] | 10.0 [5–19] | 82.5 [73–89] | 75.0 [65–83] | 16.2 [10–26] | 10.0 [5–19] | 1.2 [0–7] | 90.0 [81–95] | 35.7 [32–40] |
| B2 wsum(BM25+bge-small) = query-only | 0.0 [0–5] | 10.0 [5–19] | 85.0 [76–91] | 76.2 [66–84] | 11.2 [6–20] | 8.8 [4–17] | 1.2 [0–7] | 90.0 [81–95] | 35.3 [32–39] |

### CR@50 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | 6.2 [3–14] | 16.2 [10–26] | 82.5 [73–89] | 86.2 [77–92] | 11.2 [6–20] | 16.2 [10–26] | 1.2 [0–7] | 81.2 [71–88] | 37.6 [34–41] |
| GB hybrid keyed | 8.8 [4–17] | 20.0 [13–30] | 83.8 [74–90] | 81.2 [71–88] | 11.2 [6–20] | 16.2 [10–26] | 1.2 [0–7] | 83.8 [74–90] | 38.2 [35–42] |
| GB hybrid+cards | 18.8 [12–29] | 27.5 [19–38] | 98.8 [93–100] | 81.2 [71–88] | 47.5 [37–58] | 32.5 [23–43] | 3.8 [1–10] | 83.8 [74–90] | 49.2 [45–53] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | 11.2 [6–20] | 13.8 [8–23] | 76.2 [66–84] | 75.0 [65–83] | 21.2 [14–31] | 8.8 [4–17] | 1.2 [0–7] | 87.5 [78–93] | 36.8 [33–41] |
| B2 bge-small dense | 10.0 [5–19] | 21.2 [14–31] | 91.2 [83–96] | 83.8 [74–90] | 18.8 [12–29] | 17.5 [11–27] | 0.0 [0–5] | 90.0 [81–95] | 41.7 [38–46] |
| B2 rrf(BM25+bge-small) | 10.0 [5–19] | 22.5 [15–33] | 91.2 [83–96] | 87.5 [78–93] | 27.5 [19–38] | 16.2 [10–26] | 1.2 [0–7] | 91.2 [83–96] | 43.4 [40–47] |
| B2 wsum(BM25+bge-small) = query-only | 12.5 [7–22] | 23.8 [16–34] | 93.8 [86–97] | 86.2 [77–92] | 26.2 [18–37] | 17.5 [11–27] | 2.5 [1–9] | 93.8 [86–97] | 44.5 [41–48] |

### CR@100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | 16.2 [10–26] | 28.7 [20–39] | 88.8 [80–94] | 88.8 [80–94] | 23.8 [16–34] | 28.7 [20–39] | 1.2 [0–7] | 91.2 [83–96] | 45.9 [42–50] |
| GB hybrid keyed | 16.2 [10–26] | 28.7 [20–39] | 88.8 [80–94] | 83.8 [74–90] | 23.8 [16–34] | 28.7 [20–39] | 1.2 [0–7] | 91.2 [83–96] | 45.3 [41–49] |
| GB hybrid+cards | 22.5 [15–33] | 35.0 [25–46] | 98.8 [93–100] | 82.5 [73–89] | 58.8 [48–69] | 38.8 [29–50] | 7.5 [3–15] | 91.2 [83–96] | 54.4 [51–58] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | 16.2 [10–26] | 21.2 [14–31] | 85.0 [76–91] | 78.8 [69–86] | 22.5 [15–33] | 8.8 [4–17] | 1.2 [0–7] | 92.5 [85–97] | 40.8 [37–45] |
| B2 bge-small dense | 16.2 [10–26] | 26.2 [18–37] | 96.2 [90–99] | 83.8 [74–90] | 45.0 [35–56] | 30.0 [21–41] | 1.2 [0–7] | 96.2 [90–99] | 49.5 [46–53] |
| B2 rrf(BM25+bge-small) | 21.2 [14–31] | 28.7 [20–39] | 95.0 [88–98] | 92.5 [85–97] | 43.8 [33–55] | 33.8 [24–45] | 3.8 [1–10] | 97.5 [91–99] | 52.0 [48–56] |
| B2 wsum(BM25+bge-small) = query-only | 21.2 [14–31] | 30.0 [21–41] | 96.2 [90–99] | 90.0 [81–95] | 46.2 [36–57] | 32.5 [23–43] | 5.0 [2–12] | 97.5 [91–99] | 52.4 [48–56] |

### Item recall@10 / @100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | 19.2 / 55.9 | 29.3 / 64.7 | 61.5 / 90.2 | 66.1 / 89.4 | 38.2 / 68.4 | 27.9 / 47.2 | 24.5 / 49.7 | 72.1 / 94.4 | 42.4 / 70.0 |
| GB hybrid keyed | 21.8 / 55.9 | 36.7 / 64.7 | 67.1 / 90.2 | 63.6 / 86.9 | 40.0 / 68.4 | 28.3 / 47.2 | 26.8 / 49.7 | 76.9 / 94.4 | 45.2 / 69.7 |
| GB hybrid+cards | 56.8 / 66.4 | 63.4 / 76.1 | 98.1 / 98.8 | 74.0 / 90.6 | 78.4 / 86.0 | 39.2 / 52.9 | 40.3 / 56.4 | 76.5 / 94.4 | 65.8 / 77.7 |
| ours wsum add-only | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan |
| ours wsum keyed | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan |

### Paired tests (CR@10, distinct sets; exact sign test; Δ = arm − comparator, cluster-bootstrap 95% CI)

| arm | vs | class | better/worse | Δ pp [CI] | p |
|---|---|---|---|---|---|
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | ALL | +10/−46 | -5.6 [-7.8, -3.4] | 1.2e-06 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | option | +1/−2 | -1.2 [-6.2, +2.5] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | current | +1/−15 | -17.5 [-26.2, -8.8] | 0.00052 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | temporal | +7/−7 | +0.0 [-8.8, +8.8] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | goal | +0/−4 | -5.0 [-10.0, -1.2] | 0.12 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | pref | +1/−0 | +1.2 [+0.0, +3.8] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | cross | +0/−1 | -1.2 [-3.8, +0.0] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−18 | -21.2 [-31.2, -12.5] | 7.6e-05 |
| GB hybrid | B2 cards(<=3)+query | ALL | +9/−114 | -16.5 [-19.7, -13.3] | 2.7e-24 |
| GB hybrid | B2 cards(<=3)+query | decision | +0/−8 | -10.0 [-16.2, -3.8] | 0.0078 |
| GB hybrid | B2 cards(<=3)+query | option | +1/−13 | -15.0 [-23.8, -6.2] | 0.0018 |
| GB hybrid | B2 cards(<=3)+query | current | +0/−33 | -41.2 [-52.5, -30.0] | 2.3e-10 |
| GB hybrid | B2 cards(<=3)+query | temporal | +7/−5 | +2.5 [-6.2, +11.2] | 0.77 |
| GB hybrid | B2 cards(<=3)+query | goal | +0/−32 | -40.0 [-50.0, -30.0] | 4.7e-10 |
| GB hybrid | B2 cards(<=3)+query | pref | +1/−5 | -5.0 [-11.2, +0.0] | 0.22 |
| GB hybrid | B2 cards(<=3)+query | cross | +0/−2 | -2.5 [-6.2, +0.0] | 0.5 |
| GB hybrid | B2 cards(<=3)+query | multimodal | +1/−17 | -20.0 [-30.0, -11.2] | 0.00014 |
| GB hybrid | B2 bge-small dense | ALL | +14/−38 | -3.8 [-6.0, -1.7] | 0.0012 |
| GB hybrid | B2 bge-small dense | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | option | +1/−2 | -1.2 [-6.2, +2.5] | 1 |
| GB hybrid | B2 bge-small dense | current | +3/−12 | -11.2 [-20.0, -2.5] | 0.035 |
| GB hybrid | B2 bge-small dense | temporal | +8/−6 | +2.5 [-6.2, +11.2] | 0.79 |
| GB hybrid | B2 bge-small dense | goal | +0/−3 | -3.8 [-8.8, +0.0] | 0.25 |
| GB hybrid | B2 bge-small dense | pref | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid | B2 bge-small dense | multimodal | +2/−15 | -16.2 [-26.2, -7.5] | 0.0023 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | ALL | +8/−33 | -3.9 [-6.0, -2.0] | 0.00011 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | option | +2/−0 | +2.5 [+0.0, +6.2] | 0.5 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | current | +1/−10 | -11.2 [-18.8, -3.8] | 0.012 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | temporal | +3/−7 | -5.0 [-12.5, +2.5] | 0.34 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | goal | +1/−2 | -1.2 [-5.0, +2.5] | 1 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | pref | +1/−0 | +1.2 [+0.0, +3.8] | 1 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | cross | +0/−1 | -1.2 [-3.8, +0.0] | 1 |
| GB hybrid keyed | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−14 | -16.2 [-26.2, -7.5] | 0.00098 |
| GB hybrid keyed | B2 cards(<=3)+query | ALL | +6/−100 | -14.7 [-17.9, -11.9] | 4.5e-23 |
| GB hybrid keyed | B2 cards(<=3)+query | decision | +0/−8 | -10.0 [-16.2, -3.8] | 0.0078 |
| GB hybrid keyed | B2 cards(<=3)+query | option | +2/−11 | -11.2 [-20.0, -2.5] | 0.022 |
| GB hybrid keyed | B2 cards(<=3)+query | current | +0/−28 | -35.0 [-46.2, -25.0] | 7.5e-09 |
| GB hybrid keyed | B2 cards(<=3)+query | temporal | +3/−5 | -2.5 [-8.8, +5.0] | 0.73 |
| GB hybrid keyed | B2 cards(<=3)+query | goal | +0/−29 | -36.2 [-47.5, -26.2] | 3.7e-09 |
| GB hybrid keyed | B2 cards(<=3)+query | pref | +1/−5 | -5.0 [-11.2, +0.0] | 0.22 |
| GB hybrid keyed | B2 cards(<=3)+query | cross | +0/−2 | -2.5 [-6.2, +0.0] | 0.5 |
| GB hybrid keyed | B2 cards(<=3)+query | multimodal | +1/−13 | -15.0 [-25.0, -6.2] | 0.0018 |
| GB hybrid keyed | B2 bge-small dense | ALL | +12/−25 | -2.1 [-4.0, -0.3] | 0.047 |
| GB hybrid keyed | B2 bge-small dense | decision | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid keyed | B2 bge-small dense | option | +2/−0 | +2.5 [+0.0, +6.2] | 0.5 |
| GB hybrid keyed | B2 bge-small dense | current | +3/−7 | -5.0 [-12.5, +2.5] | 0.34 |
| GB hybrid keyed | B2 bge-small dense | temporal | +4/−6 | -2.5 [-10.0, +5.0] | 0.75 |
| GB hybrid keyed | B2 bge-small dense | goal | +1/−1 | +0.0 [-3.8, +3.8] | 1 |
| GB hybrid keyed | B2 bge-small dense | pref | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid keyed | B2 bge-small dense | cross | +0/−0 | +0.0 [+0.0, +0.0] | 1 |
| GB hybrid keyed | B2 bge-small dense | multimodal | +2/−11 | -11.2 [-20.0, -3.8] | 0.022 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | ALL | +81/−27 | +8.5 [+5.3, +11.6] | 1.9e-07 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | decision | +9/−0 | +11.2 [+5.0, +18.8] | 0.0039 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | option | +11/−2 | +11.2 [+2.5, +20.0] | 0.022 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | current | +19/−1 | +22.5 [+12.5, +32.5] | 4e-05 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | temporal | +3/−8 | -6.2 [-13.8, +2.5] | 0.23 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | goal | +25/−1 | +30.0 [+18.8, +41.2] | 8e-07 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | pref | +13/−0 | +16.2 [+8.8, +23.8] | 0.00024 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | cross | +1/−1 | +0.0 [-3.8, +3.8] | 1 |
| GB hybrid+cards | B2 wsum(BM25+bge-small) = query-only | multimodal | +1/−15 | -17.5 [-27.5, -8.8] | 0.00052 |
| GB hybrid+cards | B2 cards(<=3)+query | ALL | +18/−33 | -2.4 [-4.5, -0.2] | 0.049 |
| GB hybrid+cards | B2 cards(<=3)+query | decision | +1/−0 | +1.2 [+0.0, +3.8] | 1 |
| GB hybrid+cards | B2 cards(<=3)+query | option | +4/−6 | -2.5 [-11.2, +5.0] | 0.75 |
| GB hybrid+cards | B2 cards(<=3)+query | current | +0/−1 | -1.2 [-3.8, +0.0] | 1 |
| GB hybrid+cards | B2 cards(<=3)+query | temporal | +3/−6 | -3.8 [-11.2, +3.8] | 0.51 |
| GB hybrid+cards | B2 cards(<=3)+query | goal | +2/−6 | -5.0 [-12.5, +1.2] | 0.29 |
| GB hybrid+cards | B2 cards(<=3)+query | pref | +8/−0 | +10.0 [+3.8, +16.2] | 0.0078 |
| GB hybrid+cards | B2 cards(<=3)+query | cross | +0/−1 | -1.2 [-3.8, +0.0] | 1 |
| GB hybrid+cards | B2 cards(<=3)+query | multimodal | +1/−14 | -16.2 [-26.2, -7.5] | 0.00098 |
| GB hybrid+cards | B2 bge-small dense | ALL | +89/−23 | +10.3 [+7.1, +13.6] | 2.4e-10 |
| GB hybrid+cards | B2 bge-small dense | decision | +9/−0 | +11.2 [+5.0, +18.8] | 0.0039 |
| GB hybrid+cards | B2 bge-small dense | option | +11/−2 | +11.2 [+2.5, +20.0] | 0.022 |
| GB hybrid+cards | B2 bge-small dense | current | +24/−1 | +28.7 [+18.8, +40.0] | 1.5e-06 |
| GB hybrid+cards | B2 bge-small dense | temporal | +4/−7 | -3.8 [-11.2, +3.8] | 0.55 |
| GB hybrid+cards | B2 bge-small dense | goal | +26/−1 | +31.2 [+20.0, +42.5] | 4.2e-07 |
| GB hybrid+cards | B2 bge-small dense | pref | +12/−0 | +15.0 [+7.5, +22.5] | 0.00049 |
| GB hybrid+cards | B2 bge-small dense | cross | +1/−0 | +1.2 [+0.0, +3.8] | 1 |
| GB hybrid+cards | B2 bge-small dense | multimodal | +2/−12 | -12.5 [-21.2, -3.8] | 0.013 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | ALL | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | option | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | current | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 wsum(BM25+bge-small) = query-only | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | ALL | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | option | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | current | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 cards(<=3)+query | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | ALL | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | option | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | current | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum add-only | B2 bge-small dense | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | ALL | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | option | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | current | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 wsum(BM25+bge-small) = query-only | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | ALL | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | option | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | current | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 cards(<=3)+query | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | ALL | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | option | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | current | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| ours wsum keyed | B2 bge-small dense | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |

### Leakage, latency, errors

| arm | returned rows from ungranted sources | tasks with any | tasks | p50 / p95 ms per search | errors |
|---|---|---|---|---|---|
| GB hybrid | 0 | 0 | 790 | 4202 / 9786 | 0 |
| GB hybrid keyed | 0 | 0 | 790 | 4202 / 9786 | 0 |
| GB hybrid+cards | 0 | 0 | 790 | 4202 / 9786 | 0 |
| ours wsum add-only | 0 | 0 | 150 | 0 / 0 | 0 |
| ours wsum keyed | 0 | 0 | 150 | 0 / 0 | 0 |

### Stale probes (E1 definitions; top-10)

| arm | n | stale version above current | stale-quoting note above current | current value missing from top-10 | first value-bearing item stale |
|---|---|---|---|---|---|
| GB hybrid | 150 | 45.3% [37.6–53.3] (68) | 46.7% [38.9–54.6] (70) | 39.3% [31.9–47.3] (59) | 58.1% [49.3–66.4] (72/124) |
| GB hybrid keyed | 150 | 0.0% [0.0–2.5] (0) | 46.7% [38.9–54.6] (70) | 34.7% [27.5–42.6] (52) | 42.7% [34.4–51.5] (53/124) |
| GB hybrid+cards | 150 | 0.0% [0.0–2.5] (0) | 46.7% [38.9–54.6] (70) | 34.7% [27.5–42.6] (52) | 42.7% [34.4–51.5] (53/124) |
| ours wsum add-only | 150 | 47.3% [39.5–55.3] (71) | 35.3% [28.1–43.3] (53) | 30.7% [23.8–38.5] (46) | 57.3% [48.5–65.6] (71/124) |
| ours wsum keyed | 150 | 0.0% [0.0–2.5] (0) | 37.3% [30.0–45.3] (56) | 25.3% [19.0–32.8] (38) | 37.2% [29.4–45.8] (48/129) |
