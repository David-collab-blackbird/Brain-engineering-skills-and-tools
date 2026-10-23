## GBrain on BrainBench v0.2 seed 1

Rates: mean over distinct required sets, Wilson 95% (n = distinct sets). Batch-2 comparators re-read from results_v02 pickles, same seed and tasks.

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | 57.5 [47–68] | – | – | – | – | – | 57.5 [47–68] |
| GB + supersedes links | – | – | 63.7 [53–73] | – | – | – | – | – | 63.7 [53–73] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | – | – | 47.5 [37–58] | – | – | – | – | – | 47.5 [37–58] |
| B2 bge-small dense | – | – | 68.8 [58–78] | – | – | – | – | – | 68.8 [58–78] |
| B2 rrf(BM25+bge-small) | – | – | 70.0 [59–79] | – | – | – | – | – | 70.0 [59–79] |
| B2 wsum(BM25+bge-small) = query-only | – | – | 75.0 [65–83] | – | – | – | – | – | 75.0 [65–83] |
| B2 cards(<=3)+query | – | – | 98.8 [93–100] | – | – | – | – | – | 98.8 [93–100] |
| B2 cards+slots+query | – | – | 100.0 [95–100] | – | – | – | – | – | 100.0 [95–100] |

### CR@20 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | 71.2 [61–80] | – | – | – | – | – | 71.2 [61–80] |
| GB + supersedes links | – | – | 75.0 [65–83] | – | – | – | – | – | 75.0 [65–83] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | – | – | 60.0 [49–70] | – | – | – | – | – | 60.0 [49–70] |
| B2 bge-small dense | – | – | 78.8 [69–86] | – | – | – | – | – | 78.8 [69–86] |
| B2 rrf(BM25+bge-small) | – | – | 82.5 [73–89] | – | – | – | – | – | 82.5 [73–89] |
| B2 wsum(BM25+bge-small) = query-only | – | – | 85.0 [76–91] | – | – | – | – | – | 85.0 [76–91] |

### CR@50 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | 82.5 [73–89] | – | – | – | – | – | 82.5 [73–89] |
| GB + supersedes links | – | – | 83.8 [74–90] | – | – | – | – | – | 83.8 [74–90] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | – | – | 76.2 [66–84] | – | – | – | – | – | 76.2 [66–84] |
| B2 bge-small dense | – | – | 91.2 [83–96] | – | – | – | – | – | 91.2 [83–96] |
| B2 rrf(BM25+bge-small) | – | – | 91.2 [83–96] | – | – | – | – | – | 91.2 [83–96] |
| B2 wsum(BM25+bge-small) = query-only | – | – | 93.8 [86–97] | – | – | – | – | – | 93.8 [86–97] |

### CR@100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | 88.8 [80–94] | – | – | – | – | – | 88.8 [80–94] |
| GB + supersedes links | – | – | 88.8 [80–94] | – | – | – | – | – | 88.8 [80–94] |
| ours wsum add-only | – | – | – | – | – | – | – | – | – |
| ours wsum keyed | – | – | – | – | – | – | – | – | – |
| B2 BM25 | – | – | 85.0 [76–91] | – | – | – | – | – | 85.0 [76–91] |
| B2 bge-small dense | – | – | 96.2 [90–99] | – | – | – | – | – | 96.2 [90–99] |
| B2 rrf(BM25+bge-small) | – | – | 95.0 [88–98] | – | – | – | – | – | 95.0 [88–98] |
| B2 wsum(BM25+bge-small) = query-only | – | – | 96.2 [90–99] | – | – | – | – | – | 96.2 [90–99] |

### Item recall@10 / @100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | nan / nan | nan / nan | 61.5 / 90.2 | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | 61.5 / 90.2 |
| GB + supersedes links | nan / nan | nan / nan | 67.1 / 90.2 | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | 67.1 / 90.2 |
| ours wsum add-only | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan |
| ours wsum keyed | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan | nan / nan |

### Paired tests (CR@10, distinct sets; exact sign test; Δ = arm − comparator, cluster-bootstrap 95% CI)

| arm | vs | class | better/worse | Δ pp [CI] | p |
|---|---|---|---|---|---|
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | ALL | +1/−15 | -17.5 [-26.2, -8.8] | 0.00052 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | current | +1/−15 | -17.5 [-26.2, -8.8] | 0.00052 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | ALL | +0/−33 | -41.2 [-52.5, -30.0] | 2.3e-10 |
| GB hybrid | B2 cards(<=3)+query | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | current | +0/−33 | -41.2 [-52.5, -30.0] | 2.3e-10 |
| GB hybrid | B2 cards(<=3)+query | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | ALL | +3/−12 | -11.2 [-20.0, -2.5] | 0.035 |
| GB hybrid | B2 bge-small dense | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | current | +3/−12 | -11.2 [-20.0, -2.5] | 0.035 |
| GB hybrid | B2 bge-small dense | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | ALL | +1/−10 | -11.2 [-18.8, -3.8] | 0.012 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | current | +1/−10 | -11.2 [-18.8, -3.8] | 0.012 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | ALL | +0/−28 | -35.0 [-46.2, -25.0] | 7.5e-09 |
| GB + supersedes links | B2 cards(<=3)+query | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | current | +0/−28 | -35.0 [-46.2, -25.0] | 7.5e-09 |
| GB + supersedes links | B2 cards(<=3)+query | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | ALL | +3/−7 | -5.0 [-12.5, +2.5] | 0.34 |
| GB + supersedes links | B2 bge-small dense | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | current | +3/−7 | -5.0 [-12.5, +2.5] | 0.34 |
| GB + supersedes links | B2 bge-small dense | temporal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
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
| GB hybrid | 0 | 0 | 230 | 3132 / 6242 | 0 |
| GB + supersedes links | 0 | 0 | 230 | 4379 / 7584 | 0 |
| ours wsum add-only | 0 | 0 | 150 | 0 / 0 | 0 |
| ours wsum keyed | 0 | 0 | 150 | 0 / 0 | 0 |

### Stale probes (E1 definitions; top-10)

| arm | n | stale version above current | stale-quoting note above current | current value missing from top-10 | first value-bearing item stale |
|---|---|---|---|---|---|
| GB hybrid | 150 | 45.3% [37.6–53.3] (68) | 46.7% [38.9–54.6] (70) | 39.3% [31.9–47.3] (59) | 58.1% [49.3–66.4] (72/124) |
| GB + supersedes links | 150 | 0.0% [0.0–2.5] (0) | 47.3% [39.5–55.3] (71) | 34.0% [26.9–41.9] (51) | 43.2% [34.8–52.0] (54/125) |
| ours wsum add-only | 150 | 47.3% [39.5–55.3] (71) | 35.3% [28.1–43.3] (53) | 30.7% [23.8–38.5] (46) | 57.3% [48.5–65.6] (71/124) |
| ours wsum keyed | 150 | 0.0% [0.0–2.5] (0) | 37.3% [30.0–45.3] (56) | 25.3% [19.0–32.8] (38) | 37.2% [29.4–45.8] (48/129) |
