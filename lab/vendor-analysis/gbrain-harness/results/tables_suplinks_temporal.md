## GBrain on BrainBench v0.2 seed 1

Rates: mean over distinct required sets, Wilson 95% (n = distinct sets). Batch-2 comparators re-read from results_v02 pickles, same seed and tasks.

### CR@10 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | – | 57.5 [47–68] | – | – | – | – | 57.5 [47–68] |
| GB + supersedes links | – | – | – | 2.5 [1–9] | – | – | – | – | 2.5 [1–9] |
| B2 BM25 | – | – | – | 45.0 [35–56] | – | – | – | – | 45.0 [35–56] |
| B2 bge-small dense | – | – | – | 55.0 [44–65] | – | – | – | – | 55.0 [44–65] |
| B2 rrf(BM25+bge-small) | – | – | – | 56.2 [45–67] | – | – | – | – | 56.2 [45–67] |
| B2 wsum(BM25+bge-small) = query-only | – | – | – | 57.5 [47–68] | – | – | – | – | 57.5 [47–68] |
| B2 cards(<=3)+query | – | – | – | 55.0 [44–65] | – | – | – | – | 55.0 [44–65] |
| B2 cards+slots+query | – | – | – | 32.5 [23–43] | – | – | – | – | 32.5 [23–43] |

### CR@20 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | – | 77.5 [67–85] | – | – | – | – | 77.5 [67–85] |
| GB + supersedes links | – | – | – | 2.5 [1–9] | – | – | – | – | 2.5 [1–9] |
| B2 BM25 | – | – | – | 55.0 [44–65] | – | – | – | – | 55.0 [44–65] |
| B2 bge-small dense | – | – | – | 71.2 [61–80] | – | – | – | – | 71.2 [61–80] |
| B2 rrf(BM25+bge-small) | – | – | – | 75.0 [65–83] | – | – | – | – | 75.0 [65–83] |
| B2 wsum(BM25+bge-small) = query-only | – | – | – | 76.2 [66–84] | – | – | – | – | 76.2 [66–84] |

### CR@50 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | – | 86.2 [77–92] | – | – | – | – | 86.2 [77–92] |
| GB + supersedes links | – | – | – | 2.5 [1–9] | – | – | – | – | 2.5 [1–9] |
| B2 BM25 | – | – | – | 75.0 [65–83] | – | – | – | – | 75.0 [65–83] |
| B2 bge-small dense | – | – | – | 83.8 [74–90] | – | – | – | – | 83.8 [74–90] |
| B2 rrf(BM25+bge-small) | – | – | – | 87.5 [78–93] | – | – | – | – | 87.5 [78–93] |
| B2 wsum(BM25+bge-small) = query-only | – | – | – | 86.2 [77–92] | – | – | – | – | 86.2 [77–92] |

### CR@100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | – | – | – | 88.8 [80–94] | – | – | – | – | 88.8 [80–94] |
| GB + supersedes links | – | – | – | 88.8 [80–94] | – | – | – | – | 88.8 [80–94] |
| B2 BM25 | – | – | – | 78.8 [69–86] | – | – | – | – | 78.8 [69–86] |
| B2 bge-small dense | – | – | – | 83.8 [74–90] | – | – | – | – | 83.8 [74–90] |
| B2 rrf(BM25+bge-small) | – | – | – | 92.5 [85–97] | – | – | – | – | 92.5 [85–97] |
| B2 wsum(BM25+bge-small) = query-only | – | – | – | 90.0 [81–95] | – | – | – | – | 90.0 [81–95] |

### Item recall@10 / @100 %

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| GB hybrid | nan / nan | nan / nan | nan / nan | 66.1 / 89.4 | nan / nan | nan / nan | nan / nan | nan / nan | 66.1 / 89.4 |
| GB + supersedes links | nan / nan | nan / nan | nan / nan | 30.2 / 89.4 | nan / nan | nan / nan | nan / nan | nan / nan | 30.2 / 89.4 |

### Paired tests (CR@10, distinct sets; exact sign test; Δ = arm − comparator, cluster-bootstrap 95% CI)

| arm | vs | class | better/worse | Δ pp [CI] | p |
|---|---|---|---|---|---|
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | ALL | +7/−7 | +0.0 [-8.8, +8.8] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | current | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | temporal | +7/−7 | +0.0 [-8.8, +8.8] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 wsum(BM25+bge-small) = query-only | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | ALL | +7/−5 | +2.5 [-6.2, +11.2] | 0.77 |
| GB hybrid | B2 cards(<=3)+query | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | current | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | temporal | +7/−5 | +2.5 [-6.2, +11.2] | 0.77 |
| GB hybrid | B2 cards(<=3)+query | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 cards(<=3)+query | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | ALL | +8/−6 | +2.5 [-6.2, +11.2] | 0.79 |
| GB hybrid | B2 bge-small dense | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | current | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | temporal | +8/−6 | +2.5 [-6.2, +11.2] | 0.79 |
| GB hybrid | B2 bge-small dense | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB hybrid | B2 bge-small dense | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | ALL | +0/−44 | -55.0 [-66.2, -43.8] | 1.1e-13 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | current | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | temporal | +0/−44 | -55.0 [-66.2, -43.8] | 1.1e-13 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 wsum(BM25+bge-small) = query-only | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | ALL | +0/−42 | -52.5 [-62.5, -41.2] | 4.5e-13 |
| GB + supersedes links | B2 cards(<=3)+query | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | current | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | temporal | +0/−42 | -52.5 [-62.5, -41.2] | 4.5e-13 |
| GB + supersedes links | B2 cards(<=3)+query | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 cards(<=3)+query | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | ALL | +1/−43 | -52.5 [-63.7, -41.2] | 5.1e-12 |
| GB + supersedes links | B2 bge-small dense | decision | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | option | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | current | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | temporal | +1/−43 | -52.5 [-63.7, -41.2] | 5.1e-12 |
| GB + supersedes links | B2 bge-small dense | goal | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | pref | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | cross | +0/−0 | +nan [+nan, +nan] | 1 |
| GB + supersedes links | B2 bge-small dense | multimodal | +0/−0 | +nan [+nan, +nan] | 1 |

### Leakage, latency, errors

| arm | returned rows from ungranted sources | tasks with any | tasks | p50 / p95 ms per search | errors |
|---|---|---|---|---|---|
| GB hybrid | 0 | 0 | 80 | 8122 / 12044 | 0 |
| GB + supersedes links | 0 | 0 | 80 | 7942 / 11088 | 0 |
