# BrainBench v0 — generated tables
Items: 8038 · entities: 130 · keyed facts: 186 · tasks: 1577
Item types: chat 2516, log 1838, note 1016, image 926, email 537, fact 514, video_segment 323, page 304, preference 39, canary 18, meeting 7
Tasks per class: cross_domain 152, current_state 222, decision_support 153, goal_tracking 151, multimodal 150, option_analysis 152, preference_recommendation 154, stale_probe 286, temporal_change 157
Required-set sizes: 1:276, 2:228, 3:240, 4:275, 5:145, 6:71, 7:49, 9:3, 10:4

## E0 — baseline retrievers (keyed store, access pre-filter, temporal router, no scope), CR@10 % [Wilson 95%]
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.0 [0–2] | 13.8 [9–20] | 40.5 [34–47] | 22.3 [16–29] | 1.3 [0–5] | 8.4 [5–14] | 2.0 [1–6] | 68.7 [61–76] | 20.7 [19–23] |
| tfidf | 0.0 [0–2] | 11.8 [8–18] | 40.1 [34–47] | 24.8 [19–32] | 1.3 [0–5] | 7.1 [4–12] | 2.0 [1–6] | 60.7 [53–68] | 19.6 [18–22] |
| lsa | 0.0 [0–2] | 2.0 [1–6] | 43.7 [37–50] | 24.8 [19–32] | 0.0 [0–2] | 4.5 [2–9] | 0.0 [0–2] | 49.3 [41–57] | 17.0 [15–19] |
| rrf | 0.0 [0–2] | 5.9 [3–11] | 45.9 [40–53] | 27.4 [21–35] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 54.0 [46–62] | 18.7 [17–21] |
| wsum | 0.0 [0–2] | 5.9 [3–11] | 45.5 [39–52] | 29.9 [23–38] | 0.0 [0–2] | 5.8 [3–11] | 0.7 [0–4] | 66.7 [59–74] | 20.7 [19–23] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Item-level recall@10 (share of required items present):
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| bm25 | 12.0 | 29.3 | 41.7 | 27.9 | 31.4 | 22.5 | 17.1 | 71.7 | 32.1 |
| tfidf | 11.8 | 29.7 | 41.0 | 33.5 | 34.7 | 23.9 | 15.4 | 63.7 | 32.1 |
| lsa | 9.6 | 21.7 | 45.0 | 31.8 | 34.4 | 25.9 | 7.8 | 53.8 | 29.6 |
| rrf | 11.7 | 23.5 | 46.7 | 33.5 | 35.5 | 22.2 | 8.2 | 58.1 | 30.8 |
| wsum | 12.3 | 27.2 | 46.2 | 35.0 | 36.4 | 27.6 | 12.5 | 69.7 | 34.0 |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Temporal router (regex): fires on 141/157 temporal_change tasks; false-fires on 46/1420 others.

### E0 — depth diagnostic (default hybrid): item recall / CR at depth d
| class | d=10 | d=20 | d=50 | d=100 | d=200 |
|---|---|---|---|---|---|
| decision | 12 / 0 | 19 / 0 | 30 / 1 | 46 / 6 | 63 / 22 |
| option | 21 / 6 | 32 / 9 | 49 / 17 | 59 / 27 | 74 / 47 |
| current | 47 / 43 | 62 / 58 | 78 / 76 | 85 / 84 | 91 / 90 |
| temporal | 30 / 27 | 36 / 33 | 50 / 46 | 60 / 56 | 80 / 75 |
| goal | 34 / 0 | 41 / 1 | 51 / 7 | 60 / 14 | 77 / 52 |
| pref | 19 / 4 | 33 / 9 | 45 / 21 | 54 / 30 | 73 / 60 |
| cross | 8 / 1 | 13 / 1 | 23 / 1 | 36 / 5 | 48 / 10 |
| multimodal | 57 / 55 | 68 / 65 | 83 / 81 | 89 / 86 | 97 / 96 |

### E0 — gold-set lexical difficulty and entity-linker recall

| class | required items with ZERO token overlap with the request | tasks with ≥1 such item | linker recall of required fact entities |
|---|---|---|---|
| decision | 43% | 84% | 45% |
| option | 38% | 71% | 52% |
| current | 7% | 7% | 88% |
| temporal | 25% | 22% | 82% |
| goal | 34% | 76% | 59% |
| pref | 54% | 68% | 55% |
| cross | 36% | 82% | 31% |
| multimodal | 2% | 1% | – |

## E1 — write paths on stale probes (n=286), % [Wilson 95%]
Columns: **stale-fact** = a superseded version of the same key ranks above the head (or head absent and old version in top-10); **stale-trap** = a free-text note quoting an old value ranks above the head; **stale-summary** = a derived summary holding an old value ranks above the head; **head miss** = current version not in top-10; **first value stale** = the first value-bearing item in the top-10 carries an old value (n = probes where any value-bearing item surfaced).

| arm | stale-fact | stale-trap | stale-summary | head miss@10 | first value stale |
|---|---|---|---|---|---|
| (c) add-only, no recency | 28.7 [23.7–34.2] | 33.2 [28.0–38.9] | 0.0 [0.0–1.3] | 58.0 [52.3–63.6] | 132/205 = 64.4 [57.6–70.6] |
| (b) add-only + recency prior (w=0.5) | 6.6 [4.3–10.1] | 28.0 [23.1–33.4] | 0.0 [0.0–1.3] | 55.9 [50.1–61.6] | 52/210 = 24.8 [19.4–31.0] |
| (b') add-only + recency prior (w=1.0) | 1.7 [0.7–4.0] | 24.1 [19.5–29.4] | 0.0 [0.0–1.3] | 55.9 [50.1–61.6] | 29/211 = 13.7 [9.7–19.0] |
| (b'') add-only + recency prior (w=2.0) | 0.0 [0.0–1.3] | 11.5 [8.3–15.8] | 0.0 [0.0–1.3] | 63.6 [57.9–69.0] | 9/195 = 4.6 [2.4–8.5] |
| I3 alone: add-only + forward-to-head | 0.0 [0.0–1.3] | 28.7 [23.7–34.2] | 0.0 [0.0–1.3] | 48.6 [42.9–54.4] | 73/213 = 34.3 [28.2–40.9] |
| simulated imperfect invalidation, miss=2% | 1.7 [0.7–4.0] | 34.3 [29.0–39.9] | 0.0 [0.0–1.3] | 52.4 [46.7–58.2] | 86/212 = 40.6 [34.2–47.3] |
| simulated imperfect invalidation, miss=5% | 3.1 [1.7–5.9] | 33.9 [28.7–39.6] | 0.0 [0.0–1.3] | 52.8 [47.0–58.5] | 90/211 = 42.7 [36.2–49.4] |
| simulated imperfect invalidation, miss=10% | 4.5 [2.7–7.6] | 33.9 [28.7–39.6] | 0.0 [0.0–1.3] | 53.1 [47.4–58.9] | 86/209 = 41.1 [34.7–47.9] |
| simulated imperfect invalidation, miss=20% | 8.7 [6.0–12.6] | 33.9 [28.7–39.6] | 0.0 [0.0–1.3] | 53.5 [47.7–59.2] | 92/210 = 43.8 [37.3–50.6] |
| (a) keyed upsert (superseded out of live index) | 0.0 [0.0–1.3] | 33.9 [28.7–39.6] | 0.0 [0.0–1.3] | 52.4 [46.7–58.2] | 81/211 = 38.4 [32.1–45.1] |
| (a)+I3 keyed upsert + forward-to-head | 0.0 [0.0–1.3] | 33.9 [28.7–39.6] | 0.0 [0.0–1.3] | 52.4 [46.7–58.2] | 81/211 = 38.4 [32.1–45.1] |
| (a)+I3+mention-forwarding (traps pull in head) | 0.0 [0.0–1.3] | 27.3 [22.4–32.7] | 0.0 [0.0–1.3] | 29.7 [24.7–35.3] | 78/204 = 38.2 [31.8–45.1] |
| (a)+I3 + recency prior (w=1.0) | 0.0 [0.0–1.3] | 22.7 [18.3–27.9] | 0.0 [0.0–1.3] | 53.1 [47.4–58.9] | 29/217 = 13.4 [9.5–18.5] |
| add-only + I3 forward + mention-forwarding (all versions indexed) | 0.0 [0.0–1.3] | 24.1 [19.5–29.4] | 0.0 [0.0–1.3] | 27.6 [22.8–33.1] | 69/207 = 33.3 [27.3–40.0] |
| (a)+I3 + stale-mention suppression (extraction recall 70%) | 0.0 [0.0–1.3] | 18.2 [14.1–23.1] | 0.0 [0.0–1.3] | 48.3 [42.5–54.0] | 44/208 = 21.2 [16.2–27.2] |
| (a)+I3 + stale-mention suppression (extraction recall 90%) | 0.0 [0.0–1.3] | 8.0 [5.4–11.8] | 0.0 [0.0–1.3] | 45.5 [39.8–51.2] | 18/203 = 8.9 [5.7–13.6] |
| (a)+I3 + stale-mention suppression (extraction recall 100%) | 0.0 [0.0–1.3] | 0.0 [0.0–1.3] | 0.0 [0.0–1.3] | 44.8 [39.1–50.5] | 0/197 = 0.0 [0.0–1.9] |
| (a)+I3 + suppression(90%) + mention-forwarding + recency(1.0) | 0.0 [0.0–1.3] | 0.7 [0.2–2.5] | 0.0 [0.0–1.3] | 33.6 [28.3–39.2] | 2/196 = 1.0 [0.3–3.6] |
| (a)+I3 + stale summaries (generated month 6, not regenerated) | 0.0 [0.0–1.3] | 35.0 [29.7–40.7] | 3.8 [2.2–6.8] | 52.4 [46.7–58.2] | 87/214 = 40.7 [34.3–47.3] |
| (a)+I3 + summaries regenerated on dependency change (current) | 0.0 [0.0–1.3] | 33.9 [28.7–39.6] | 0.0 [0.0–1.3] | 49.7 [43.9–55.4] | 80/214 = 37.4 [31.2–44.0] |

Paired head-found@10 comparisons (exact McNemar):

| A | B | B finds head, A not / A finds, B not | p |
|---|---|---|---|
| (a) keyed upsert (superseded out of live index) | I3 alone: add-only + forward-to-head | 12 / 1 | 0.00342 |
| (a)+I3+mention-forwarding (traps pull in head) | add-only + I3 forward + mention-forwarding (all versions indexed) | 6 / 0 | 0.0312 |
| (a) keyed upsert (superseded out of live index) | (a)+I3+mention-forwarding (traps pull in head) | 69 / 4 | 2.44e-16 |
| (a) keyed upsert (superseded out of live index) | (a)+I3 + stale-mention suppression (extraction recall 90%) | 20 / 0 | 1.91e-06 |

Stale summaries: 39 entity summaries generated at month 6 hold 122 values that were later superseded.

Write path vs temporal_change CR@10:

| store | CR@10 temporal_change |
|---|---|
| keyed, history never searched | 0.0 [0.0–2.4] (n=157) |
| keyed + temporal router -> history | 27.4 [21.0–34.8] (n=157) |
| add-only (all versions live) | 35.0 [28.0–42.8] (n=157) |

## E2 — scope modes, CR@10 % [Wilson 95%]
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| none (access filter only) | 0.0 [0–2] | 5.9 [3–11] | 43.2 [37–50] | 27.4 [21–35] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 54.7 [47–62] | 18.4 [16–21] |
| declared: hard filter | 0.0 [0–2] | 5.9 [3–11] | 46.8 [40–53] | 32.5 [26–40] | 1.3 [0–5] | 5.8 [3–11] | 0.0 [0–2] | 57.3 [49–65] | 20.2 [18–22] |
| declared: boost (RRF w=1) | 0.0 [0–2] | 5.9 [3–11] | 46.4 [40–53] | 31.8 [25–39] | 1.3 [0–5] | 5.8 [3–11] | 0.7 [0–4] | 58.7 [51–66] | 20.3 [18–23] |
| declared: boost (RRF w=2) | 0.0 [0–2] | 5.9 [3–11] | 46.8 [40–53] | 33.1 [26–41] | 1.3 [0–5] | 5.8 [3–11] | 0.0 [0–2] | 59.3 [51–67] | 20.5 [18–23] |
| inferred from query: boost | 0.0 [0–2] | 5.9 [3–11] | 45.0 [39–52] | 28.0 [22–36] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 52.0 [44–60] | 18.4 [16–21] |
| inferred from query: hard filter | 0.0 [0–2] | 5.9 [3–11] | 36.5 [30–43] | 26.8 [20–34] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 52.0 [44–60] | 16.8 [15–19] |
| trail (noise 0.3): boost | 0.0 [0–2] | 5.9 [3–11] | 45.5 [39–52] | 31.8 [25–39] | 1.3 [0–5] | 5.8 [3–11] | 0.7 [0–4] | 58.7 [51–66] | 20.1 [18–22] |
| trail (noise 0.6): boost | 0.0 [0–2] | 5.9 [3–11] | 44.1 [38–51] | 31.2 [24–39] | 1.3 [0–5] | 5.8 [3–11] | 0.7 [0–4] | 55.3 [47–63] | 19.4 [17–22] |
| trail+query (noise 0.3): boost | 0.0 [0–2] | 5.9 [3–11] | 46.4 [40–53] | 31.8 [25–39] | 1.3 [0–5] | 5.8 [3–11] | 0.7 [0–4] | 58.7 [51–66] | 20.3 [18–23] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Item-level recall@10:
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| none (access filter only) | 12.1 | 23.5 | 44.0 | 33.7 | 34.7 | 22.2 | 8.4 | 59.0 | 30.4 |
| declared: hard filter | 15.2 | 27.6 | 47.6 | 40.8 | 41.1 | 25.3 | 9.7 | 62.9 | 34.5 |
| declared: boost (RRF w=1) | 14.9 | 28.2 | 47.1 | 39.5 | 40.4 | 25.4 | 10.6 | 63.3 | 34.4 |
| declared: boost (RRF w=2) | 15.5 | 28.4 | 47.6 | 40.4 | 41.0 | 25.6 | 10.1 | 63.3 | 34.7 |
| inferred from query: boost | 12.9 | 24.0 | 45.8 | 35.3 | 35.6 | 22.2 | 8.9 | 56.9 | 31.0 |
| inferred from query: hard filter | 12.9 | 20.3 | 37.2 | 29.7 | 29.4 | 20.9 | 8.9 | 57.0 | 27.5 |
| trail (noise 0.3): boost | 14.9 | 28.1 | 46.2 | 39.2 | 39.4 | 25.4 | 10.9 | 63.3 | 34.1 |
| trail (noise 0.6): boost | 14.6 | 26.5 | 44.9 | 38.4 | 39.3 | 25.3 | 11.0 | 60.0 | 33.1 |
| trail+query (noise 0.3): boost | 14.9 | 28.2 | 47.1 | 39.2 | 40.1 | 25.4 | 10.9 | 63.3 | 34.3 |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Hard-filter ceiling (share of tasks whose required items all sit in the declared scope group): cross 0%, current 100%, decision 95%, goal 98%, multimodal 100%, option 90%, pref 100%, temporal 100%

Scope inference accuracy (vs declared primary scope):

| method | correct | abstain | prediction ∈ required groups |
|---|---|---|---|
| query | 39.1 [36.5–41.8] | 618 | 42.1 [39.4–44.8] |
| trail noise 0.0 | 99.5 [99.0–99.8] | 0 | 100.0 [99.7–100.0] |
| trail noise 0.3 | 97.3 [96.3–98.0] | 0 | 98.1 [97.2–98.7] |
| trail noise 0.6 | 82.3 [80.2–84.3] | 0 | 84.0 [81.9–85.9] |
| trail+query noise 0.3 | 99.1 [98.5–99.5] | 0 | 99.6 [99.1–99.8] |
| trail+query noise 0.6 | 90.2 [88.5–91.7] | 0 | 92.2 [90.6–93.5] |

Paired tests vs 'none':

| arm vs base | class | wins / losses | exact McNemar p |
|---|---|---|---|
| declared: hard filter | ALL | +26 / −2 | 3.03e-06 |
| declared: hard filter | cross_domain | +0 / −1 | 1 |
| declared: hard filter | current_state | +8 / −0 | 0.00781 |
| declared: hard filter | temporal_change | +8 / −0 | 0.00781 |
| declared: boost (RRF w=1) | ALL | +25 / −0 | 5.96e-08 |
| declared: boost (RRF w=1) | cross_domain | +0 / −0 | 1 |
| declared: boost (RRF w=1) | current_state | +7 / −0 | 0.0156 |
| declared: boost (RRF w=1) | temporal_change | +7 / −0 | 0.0156 |
| declared: boost (RRF w=2) | ALL | +29 / −1 | 5.77e-08 |
| declared: boost (RRF w=2) | cross_domain | +0 / −1 | 1 |
| declared: boost (RRF w=2) | current_state | +8 / −0 | 0.00781 |
| declared: boost (RRF w=2) | temporal_change | +9 / −0 | 0.00391 |
| inferred from query: boost | ALL | +6 / −5 | 1 |
| inferred from query: boost | cross_domain | +0 / −0 | 1 |
| inferred from query: boost | current_state | +4 / −0 | 0.125 |
| inferred from query: boost | temporal_change | +1 / −0 | 1 |
| inferred from query: hard filter | ALL | +7 / −27 | 0.000821 |
| inferred from query: hard filter | cross_domain | +0 / −0 | 1 |
| inferred from query: hard filter | current_state | +4 / −19 | 0.0026 |
| inferred from query: hard filter | temporal_change | +2 / −3 | 1 |
| trail (noise 0.3): boost | ALL | +25 / −2 | 5.65e-06 |
| trail (noise 0.3): boost | cross_domain | +0 / −0 | 1 |
| trail (noise 0.3): boost | current_state | +7 / −2 | 0.18 |
| trail (noise 0.3): boost | temporal_change | +7 / −0 | 0.0156 |
| trail (noise 0.6): boost | ALL | +21 / −7 | 0.0125 |
| trail (noise 0.6): boost | cross_domain | +0 / −0 | 1 |
| trail (noise 0.6): boost | current_state | +5 / −3 | 0.727 |
| trail (noise 0.6): boost | temporal_change | +6 / −0 | 0.0312 |
| trail+query (noise 0.3): boost | ALL | +25 / −0 | 5.96e-08 |
| trail+query (noise 0.3): boost | cross_domain | +0 / −0 | 1 |
| trail+query (noise 0.3): boost | current_state | +7 / −0 | 0.0156 |
| trail+query (noise 0.3): boost | temporal_change | +7 / −0 | 0.0156 |

## E3 — context assembly at equal k=10, CR@10 % [Wilson 95%]
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only top-10 | 0.0 [0–2] | 5.9 [3–11] | 43.2 [37–50] | 27.4 [21–35] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 54.7 [47–62] | 18.4 [16–21] |
| query + mention->head forwarding (new) | 0.0 [0–2] | 5.9 [3–11] | 59.0 [52–65] | 26.8 [20–34] | 4.6 [2–9] | 5.8 [3–11] | 0.7 [0–4] | 54.7 [47–62] | 21.8 [20–24] |
| ORACLE frequency packet(5) + query(5) [ceiling] | 0.0 [0–2] | 10.5 [7–16] | 37.8 [32–44] | 15.9 [11–22] | 6.6 [4–12] | 22.7 [17–30] | 0.7 [0–4] | 46.7 [39–55] | 18.7 [17–21] |
| packet(3) + query(7) | 0.0 [0–2] | 7.2 [4–12] | 41.9 [36–48] | 22.3 [16–29] | 2.0 [1–6] | 3.9 [2–8] | 0.7 [0–4] | 50.0 [42–58] | 17.4 [15–20] |
| packet(5) + query(5) | 0.0 [0–2] | 7.2 [4–12] | 39.6 [33–46] | 19.1 [14–26] | 2.0 [1–6] | 3.9 [2–8] | 0.7 [0–4] | 48.7 [41–57] | 16.4 [15–19] |
| hand slot contract(<=5) + query | 1.3 [0–5] | 6.6 [4–12] | 85.6 [80–90] | 21.7 [16–29] | 11.3 [7–17] | 3.2 [1–7] | 0.7 [0–4] | 46.7 [39–55] | 25.5 [23–28] |
| generic slots(<=5) + query | 1.3 [0–5] | 5.9 [3–11] | 90.1 [85–93] | 22.3 [16–29] | 5.3 [3–10] | 3.9 [2–8] | 0.7 [0–4] | 48.0 [40–56] | 25.8 [23–28] |
| entity cards(<=3, pinned) + query (cards indexed) | 4.6 [2–9] | 13.2 [9–19] | 94.6 [91–97] | 33.8 [27–41] | 8.6 [5–14] | 3.2 [1–7] | 0.7 [0–4] | 53.3 [45–61] | 30.1 [28–33] |
| cards(<=3) + hand static slots (<=5 total) + query | 8.5 [5–14] | 13.2 [9–19] | 98.2 [95–99] | 25.5 [19–33] | 13.2 [9–20] | 2.6 [1–6] | 0.7 [0–4] | 48.0 [40–56] | 30.1 [28–33] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Item-level recall@10:
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only top-10 | 12.1 | 23.5 | 44.0 | 33.7 | 34.7 | 22.2 | 8.4 | 59.0 | 30.4 |
| query + mention->head forwarding (new) | 22.7 | 29.9 | 61.5 | 39.0 | 44.2 | 26.7 | 12.9 | 58.1 | 38.1 |
| ORACLE frequency packet(5) + query(5) [ceiling] | 38.7 | 40.0 | 40.2 | 32.9 | 50.2 | 61.1 | 35.0 | 49.4 | 43.2 |
| packet(3) + query(7) | 23.5 | 26.2 | 42.8 | 33.6 | 41.4 | 19.3 | 10.7 | 53.9 | 32.0 |
| packet(5) + query(5) | 25.7 | 26.0 | 42.0 | 31.5 | 45.1 | 18.2 | 14.9 | 52.6 | 32.5 |
| hand slot contract(<=5) + query | 50.7 | 55.7 | 87.4 | 47.0 | 63.0 | 31.8 | 28.2 | 49.4 | 53.5 |
| generic slots(<=5) + query | 46.6 | 48.9 | 91.6 | 48.3 | 59.3 | 32.3 | 19.3 | 51.6 | 52.0 |
| entity cards(<=3, pinned) + query (cards indexed) | 47.7 | 51.2 | 94.6 | 52.9 | 57.3 | 33.8 | 22.7 | 56.9 | 54.4 |
| cards(<=3) + hand static slots (<=5 total) + query | 70.6 | 57.8 | 98.2 | 53.2 | 65.7 | 33.0 | 37.5 | 51.2 | 60.5 |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Mean share of required items covered by the prefix (packet/slots/cards) alone:

| prefix | decision | option | current | temporal | goal | pref | cross | multimodal |
|---|---|---|---|---|---|---|---|---|
| ORACLE frequency packet(5) + query(5) [ceiling] | 33 | 24 | 9 | 7 | 27 | 52 | 30 | 0 |
| ORACLE frequency packet(5) + query(5) [ceiling] [all req. covered by prefix alone] | 0 | 3 | 9 | 0 | 0 | 5 | 0 | 0 |
| packet(3) + query(7) | 15 | 6 | 7 | 4 | 21 | 0 | 4 | 0 |
| packet(3) + query(7) [all req. covered by prefix alone] | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 |
| packet(5) + query(5) | 19 | 8 | 9 | 4 | 28 | 0 | 9 | 0 |
| packet(5) + query(5) [all req. covered by prefix alone] | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| hand slot contract(<=5) + query | 48 | 48 | 79 | 31 | 60 | 20 | 24 | 0 |
| hand slot contract(<=5) + query [all req. covered by prefix alone] | 0 | 0 | 77 | 0 | 7 | 0 | 0 | 0 |
| generic slots(<=5) + query | 45 | 40 | 88 | 33 | 57 | 20 | 15 | 0 |
| generic slots(<=5) + query [all req. covered by prefix alone] | 0 | 0 | 86 | 0 | 1 | 0 | 0 | 0 |
| entity cards(<=3, pinned) + query (cards indexed) | 44 | 40 | 88 | 34 | 47 | 20 | 17 | 0 |
| entity cards(<=3, pinned) + query (cards indexed) [all req. covered by prefix alone] | 5 | 2 | 88 | 6 | 3 | 0 | 0 | 0 |
| cards(<=3) + hand static slots (<=5 total) + query | 69 | 49 | 95 | 39 | 62 | 20 | 34 | 0 |
| cards(<=3) + hand static slots (<=5 total) + query [all req. covered by prefix alone] | 5 | 2 | 95 | 6 | 9 | 0 | 0 | 0 |

Paired tests vs query-only:

| arm vs base | class | wins / losses | exact McNemar p |
|---|---|---|---|
| query + mention->head forwarding (new) | ALL | +52 / −8 | 5.21e-09 |
| query + mention->head forwarding (new) | current_state | +41 / −6 | 1.77e-07 |
| query + mention->head forwarding (new) | decision_support | +0 / −0 | 1 |
| query + mention->head forwarding (new) | goal_tracking | +7 / −0 | 0.0156 |
| ORACLE frequency packet(5) + query(5) [ceiling] | ALL | +58 / −54 | 0.777 |
| ORACLE frequency packet(5) + query(5) [ceiling] | current_state | +12 / −24 | 0.0652 |
| ORACLE frequency packet(5) + query(5) [ceiling] | decision_support | +0 / −0 | 1 |
| ORACLE frequency packet(5) + query(5) [ceiling] | goal_tracking | +10 / −0 | 0.00195 |
| packet(3) + query(7) | ALL | +17 / −30 | 0.0789 |
| packet(3) + query(7) | current_state | +12 / −15 | 0.701 |
| packet(3) + query(7) | decision_support | +0 / −0 | 1 |
| packet(3) + query(7) | goal_tracking | +3 / −0 | 0.25 |
| packet(5) + query(5) | ALL | +20 / −45 | 0.00263 |
| packet(5) + query(5) | current_state | +15 / −23 | 0.256 |
| packet(5) + query(5) | decision_support | +0 / −0 | 1 |
| packet(5) + query(5) | goal_tracking | +3 / −0 | 0.25 |
| hand slot contract(<=5) + query | ALL | +116 / −24 | 1.15e-15 |
| hand slot contract(<=5) + query | current_state | +94 / −0 | 1.01e-28 |
| hand slot contract(<=5) + query | decision_support | +2 / −0 | 0.5 |
| hand slot contract(<=5) + query | goal_tracking | +17 / −0 | 1.53e-05 |
| generic slots(<=5) + query | ALL | +118 / −22 | 4.49e-17 |
| generic slots(<=5) + query | current_state | +106 / −2 | 3.63e-29 |
| generic slots(<=5) + query | decision_support | +2 / −0 | 0.5 |
| generic slots(<=5) + query | goal_tracking | +8 / −0 | 0.00781 |
| entity cards(<=3, pinned) + query (cards indexed) | ALL | +159 / −7 | 1.36e-38 |
| entity cards(<=3, pinned) + query (cards indexed) | current_state | +114 / −0 | 9.63e-35 |
| entity cards(<=3, pinned) + query (cards indexed) | decision_support | +7 / −0 | 0.0156 |
| entity cards(<=3, pinned) + query (cards indexed) | goal_tracking | +13 / −0 | 0.000244 |
| cards(<=3) + hand static slots (<=5 total) + query | ALL | +178 / −27 | 1.83e-28 |
| cards(<=3) + hand static slots (<=5 total) + query | current_state | +122 / −0 | 3.76e-37 |
| cards(<=3) + hand static slots (<=5 total) + query | decision_support | +13 / −0 | 0.000244 |
| cards(<=3) + hand static slots (<=5 total) + query | goal_tracking | +20 / −0 | 1.91e-06 |

## E4 — BM25 statistics side channel (attacker identity: partner_cafe)

Attacker plants a one-word note in its own partition, queries the word, and inverts BM25 to estimate document frequency.

| term | true df (all) | true df (hidden from attacker) | estimated df — global stats | — visible-set stats | — per-partition stats |
|---|---|---|---|---|---|
| halyard | 327 | 326 | 327.0 | 1.0 | 1.0 |
| refix | 7 | 6 | 7.0 | 1.0 | 1.0 |
| wren | 89 | 88 | 89.0 | 1.0 | 1.0 |
| biopsy | 1 | 0 | 1.0 | 1.0 | 1.0 |
| kestrel | 87 | 86 | 87.0 | 1.0 | 1.0 |
| zzqprobe | 1 | 0 | 1.0 | 1.0 | 1.0 |
| glyph | 3 | 2 | 3.0 | 1.0 | 1.0 |

Controlled insertion of M hidden documents (owner partition) containing a rare term; BM25 score of the attacker's visible document:

| hidden docs M | global | Δ global | visible-set | Δ visible | per-partition | Δ per-partition |
|---|---|---|---|---|---|---|
| 0 | 12.262 | +0.000 | 9.497 | +0.000 | 9.383 | +0.000 |
| 1 | 11.532 | -0.729 | 9.497 | +0.000 | 9.383 | +0.000 |
| 5 | 10.168 | -2.093 | 9.497 | +0.000 | 9.383 | +0.000 |
| 20 | 8.462 | -3.800 | 9.497 | +0.000 | 9.383 | +0.000 |

Rank flip between two visible docs as hidden docs are added:

| hidden docs | global | visible-set | per-partition |
|---|---|---|---|
| 0 | A>B | A>B | A>B |
| 3 | B>A | A>B | A>B |
| 10 | B>A | A>B | A>B |

Corpus-fitted vector models leak too: adding 10 hidden docs changes a visible doc's TF-IDF cosine by -0.0387 and its LSA cosine by +0.0038.

## E5 — entity-graph expansion, CR@10 % [Wilson 95%]
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| no graph | 0.0 [0–2] | 5.9 [3–11] | 43.2 [37–50] | 27.4 [21–35] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 54.7 [47–62] | 18.4 [16–21] |
| 1-hop, per-hop ACL, 3 reserved slots | 0.0 [0–2] | 5.9 [3–11] | 43.2 [37–50] | 28.0 [22–36] | 1.3 [0–5] | 3.9 [2–8] | 0.7 [0–4] | 59.3 [51–67] | 19.1 [17–21] |
| 2-hop, per-hop ACL, 3 reserved slots | 0.0 [0–2] | 5.9 [3–11] | 42.3 [36–49] | 28.0 [22–36] | 1.3 [0–5] | 3.9 [2–8] | 0.7 [0–4] | 59.3 [51–67] | 19.0 [17–21] |
| 1-hop, per-hop ACL, RRF w=1 | 0.0 [0–2] | 5.9 [3–11] | 44.6 [38–51] | 30.6 [24–38] | 1.3 [0–5] | 3.2 [1–7] | 0.0 [0–2] | 59.3 [51–67] | 19.5 [17–22] |
| 2-hop, per-hop ACL, RRF w=1 | 0.0 [0–2] | 5.9 [3–11] | 43.7 [37–50] | 30.6 [24–38] | 1.3 [0–5] | 3.2 [1–7] | 0.0 [0–2] | 58.7 [51–66] | 19.3 [17–22] |
| 1-hop, NO per-hop ACL, 3 reserved slots | 0.0 [0–2] | 5.9 [3–11] | 43.2 [37–50] | 28.0 [22–36] | 0.7 [0–4] | 3.2 [1–7] | 0.7 [0–4] | 59.3 [51–67] | 19.0 [17–21] |
| 2-hop, NO per-hop ACL, 3 reserved slots | 0.0 [0–2] | 5.9 [3–11] | 42.3 [36–49] | 27.4 [21–35] | 0.0 [0–2] | 3.2 [1–7] | 0.7 [0–4] | 59.3 [51–67] | 18.7 [17–21] |
| 2-hop, NO per-hop ACL, RRF w=1 | 0.0 [0–2] | 5.9 [3–11] | 43.7 [37–50] | 30.6 [24–38] | 1.3 [0–5] | 3.2 [1–7] | 0.0 [0–2] | 58.7 [51–66] | 19.3 [17–22] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Paired tests vs no graph:

| arm vs base | class | wins / losses | exact McNemar p |
|---|---|---|---|
| 1-hop, per-hop ACL, 3 reserved slots | ALL | +20 / −10 | 0.0987 |
| 1-hop, per-hop ACL, 3 reserved slots | option_analysis | +0 / −0 | 1 |
| 1-hop, per-hop ACL, 3 reserved slots | cross_domain | +0 / −0 | 1 |
| 2-hop, per-hop ACL, 3 reserved slots | ALL | +18 / −10 | 0.185 |
| 2-hop, per-hop ACL, 3 reserved slots | option_analysis | +0 / −0 | 1 |
| 2-hop, per-hop ACL, 3 reserved slots | cross_domain | +0 / −0 | 1 |
| 1-hop, per-hop ACL, RRF w=1 | ALL | +27 / −12 | 0.0237 |
| 1-hop, per-hop ACL, RRF w=1 | option_analysis | +0 / −0 | 1 |
| 1-hop, per-hop ACL, RRF w=1 | cross_domain | +0 / −1 | 1 |
| 2-hop, per-hop ACL, RRF w=1 | ALL | +26 / −14 | 0.0807 |
| 2-hop, per-hop ACL, RRF w=1 | option_analysis | +0 / −0 | 1 |
| 2-hop, per-hop ACL, RRF w=1 | cross_domain | +0 / −1 | 1 |
| 1-hop, NO per-hop ACL, 3 reserved slots | ALL | +18 / −10 | 0.185 |
| 1-hop, NO per-hop ACL, 3 reserved slots | option_analysis | +0 / −0 | 1 |
| 1-hop, NO per-hop ACL, 3 reserved slots | cross_domain | +0 / −0 | 1 |
| 2-hop, NO per-hop ACL, 3 reserved slots | ALL | +14 / −10 | 0.541 |
| 2-hop, NO per-hop ACL, 3 reserved slots | option_analysis | +0 / −0 | 1 |
| 2-hop, NO per-hop ACL, 3 reserved slots | cross_domain | +0 / −0 | 1 |
| 2-hop, NO per-hop ACL, RRF w=1 | ALL | +26 / −14 | 0.0807 |
| 2-hop, NO per-hop ACL, RRF w=1 | option_analysis | +0 / −0 | 1 |
| 2-hop, NO per-hop ACL, RRF w=1 | cross_domain | +0 / −1 | 1 |

Leakage (any returned item outside requester's access) and canary monitor:

| arm | tasks with leak | leaked items | tasks leaking a canary | leaking tiers | canary monitor alarms / probes |
|---|---|---|---|---|---|
| no graph | 0.0 [0.0–0.3] | 0 | 0 | {} | 0/501 |
| 1-hop, per-hop ACL, 3 reserved slots | 0.0 [0.0–0.3] | 0 | 0 | {} | 0/501 |
| 2-hop, per-hop ACL, 3 reserved slots | 0.0 [0.0–0.3] | 0 | 0 | {} | 0/501 |
| 1-hop, per-hop ACL, RRF w=1 | 0.0 [0.0–0.3] | 0 | 0 | {} | 0/501 |
| 2-hop, per-hop ACL, RRF w=1 | 0.0 [0.0–0.3] | 0 | 0 | {} | 0/501 |
| 1-hop, NO per-hop ACL, 3 reserved slots | 4.5 [3.5–5.8] | 111 | 32 | {'partner': 25, 'member': 33} | 278/501 |
| 2-hop, NO per-hop ACL, 3 reserved slots | 8.5 [7.1–10.2] | 252 | 15 | {'partner': 44, 'member': 63, 'household': 3} | 193/501 |
| 2-hop, NO per-hop ACL, RRF w=1 | 1.0 [0.6–1.7] | 35 | 9 | {'partner': 13} | 18/501 |

## E7 — packing at equal k=10, CR@10 % [Wilson 95%]
| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| top-k | 0.0 [0–2] | 5.9 [3–11] | 43.2 [37–50] | 27.4 [21–35] | 0.0 [0–2] | 3.9 [2–8] | 0.7 [0–4] | 54.7 [47–62] | 18.4 [16–21] |
| MMR (lambda=0.7, LSA sim) | 0.0 [0–2] | 7.9 [5–13] | 48.6 [42–55] | 15.9 [11–22] | 0.0 [0–2] | 6.5 [4–12] | 1.3 [0–5] | 55.3 [47–63] | 18.6 [17–21] |
| coverage packing (lambda=0.5) | 0.0 [0–2] | 7.2 [4–12] | 42.3 [36–49] | 17.8 [13–25] | 0.0 [0–2] | 2.6 [1–6] | 0.7 [0–4] | 54.7 [47–62] | 17.0 [15–19] |
| coverage packing (lambda=0.25) | 0.0 [0–2] | 7.2 [4–12] | 41.9 [36–48] | 21.0 [15–28] | 0.0 [0–2] | 2.6 [1–6] | 0.7 [0–4] | 54.7 [47–62] | 17.4 [15–20] |
| coverage packing (lambda=1.0) | 0.0 [0–2] | 7.2 [4–12] | 31.5 [26–38] | 8.9 [5–14] | 0.0 [0–2] | 3.2 [1–7] | 0.7 [0–4] | 42.7 [35–51] | 12.8 [11–15] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

Paired tests vs top-k:

| arm vs base | class | wins / losses | exact McNemar p |
|---|---|---|---|
| MMR (lambda=0.7, LSA sim) | ALL | +43 / −40 | 0.826 |
| coverage packing (lambda=0.5) | ALL | +12 / −29 | 0.0115 |
| coverage packing (lambda=0.25) | ALL | +7 / −20 | 0.0192 |
| coverage packing (lambda=1.0) | ALL | +15 / −87 | 1.65e-13 |

CR@k by required-set size (default hybrid, query-only):

| arm | size 1 | size 2 | size 3 | size 4 | size 5 | size 6 | size 7 | size 8 |
|---|---|---|---|---|---|---|---|---|
| top-k @k=10 | 51 (276) | 23 (228) | 12 (240) | 5 (275) | 1 (145) | 0 (71) | 0 (49) | 0 (7) |
| coverage(0.5) @k=10 | 51 (276) | 20 (228) | 11 (240) | 1 (275) | 1 (145) | 0 (71) | 0 (49) | 0 (7) |
| top-k @k=20 | 66 (276) | 29 (228) | 18 (240) | 5 (275) | 1 (145) | 3 (71) | 0 (49) | 0 (7) |
| coverage(0.5) @k=20 | 66 (276) | 26 (228) | 17 (240) | 5 (275) | 1 (145) | 1 (71) | 0 (49) | 0 (7) |
| top-k @k=30 | 75 (276) | 38 (228) | 23 (240) | 8 (275) | 1 (145) | 3 (71) | 0 (49) | 0 (7) |
| coverage(0.5) @k=30 | 75 (276) | 36 (228) | 22 (240) | 7 (275) | 1 (145) | 3 (71) | 0 (49) | 0 (7) |

CR@k by required-set size, best E3 pipeline (cards + static slots + query); size 8 = 9–10:

| k | size 1 | size 2 | size 3 | size 4 | size 5 | size 6 | size 7 | size 8 |
|---|---|---|---|---|---|---|---|---|
| k=10 | 85.1 [80.5–88.9] (n=276) | 32.9 [27.1–39.2] (n=228) | 20.4 [15.8–26.0] (n=240) | 9.8 [6.8–13.9] (n=275) | 0.7 [0.1–3.8] (n=145) | 0.0 [0.0–5.1] (n=71) | 2.0 [0.4–10.7] (n=49) | 0.0 [0.0–35.4] (n=7) |
| k=20 | 90.2 [86.1–93.2] (n=276) | 37.3 [31.3–43.7] (n=228) | 29.6 [24.2–35.6] (n=240) | 16.0 [12.1–20.8] (n=275) | 4.8 [2.4–9.6] (n=145) | 1.4 [0.2–7.6] (n=71) | 8.2 [3.2–19.2] (n=49) | 0.0 [0.0–35.4] (n=7) |
| k=30 | 93.5 [89.9–95.8] (n=276) | 45.6 [39.3–52.1] (n=228) | 37.5 [31.6–43.8] (n=240) | 21.5 [17.0–26.7] (n=275) | 5.5 [2.8–10.5] (n=145) | 2.8 [0.8–9.7] (n=71) | 8.2 [3.2–19.2] (n=49) | 0.0 [0.0–35.4] (n=7) |

Same pipeline, CR@k by class:

| k | decision | option | current | temporal | goal | pref | cross | multimodal |
|---|---|---|---|---|---|---|---|---|
| k=10 | 8.5 [5.0–14.0] | 13.2 [8.7–19.5] | 98.2 [95.5–99.3] | 25.5 [19.3–32.8] | 13.2 [8.7–19.6] | 2.6 [1.0–6.5] | 0.7 [0.1–3.6] | 48.0 [40.2–55.9] |
| k=20 | 17.0 [11.9–23.7] | 15.1 [10.3–21.7] | 98.2 [95.5–99.3] | 35.7 [28.6–43.4] | 15.2 [10.4–21.8] | 14.9 [10.2–21.4] | 0.7 [0.1–3.6] | 60.7 [52.7–68.1] |
| k=30 | 23.5 [17.5–30.8] | 21.7 [15.9–28.9] | 98.6 [96.1–99.5] | 41.4 [34.0–49.2] | 19.9 [14.3–26.9] | 20.8 [15.1–27.9] | 1.3 [0.4–4.7] | 72.0 [64.3–78.6] |

## I8 — origin-context enrichment, multimodal CR@10 % [Wilson 95%]

| index | retriever | all multimodal | caption sufficient | needs origin-only item |
|---|---|---|---|---|
| without origin context | rrf | 28.0 [21.4–35.7] (n=150) | 71.0 [53.4–83.9] (n=31) | 16.8 [11.2–24.5] (n=119) |
| without origin context | bm25 | 38.0 [30.6–46.0] (n=150) | 83.9 [67.4–92.9] (n=31) | 26.1 [19.0–34.6] (n=119) |
| with origin context (I8) | rrf | 54.7 [46.7–62.4] (n=150) | 71.0 [53.4–83.9] (n=31) | 50.4 [41.6–59.2] (n=119) |
| with origin context (I8) | bm25 | 68.7 [60.9–75.5] (n=150) | 83.9 [67.4–92.9] (n=31) | 64.7 [55.8–72.7] (n=119) |

Paired (rrf): with-origin wins 40, loses 0, exact McNemar p=1.8e-12.

Paired (bm25): with-origin wins 47, loses 1, exact McNemar p=3.5e-13.

## Robustness — headline arms re-run with BM25-only first stage (CR@10 % [Wilson 95%])

**E2**

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| none (access filter only) | 0.0 [0–2] | 13.8 [9–20] | 32.4 [27–39] | 22.3 [16–29] | 1.3 [0–5] | 8.4 [5–14] | 2.0 [1–6] | 68.7 [61–76] | 19.3 [17–22] |
| declared: hard filter | 0.0 [0–2] | 8.6 [5–14] | 34.2 [28–41] | 25.5 [19–33] | 3.3 [1–8] | 8.4 [5–14] | 0.0 [0–2] | 70.0 [62–77] | 19.5 [17–22] |
| declared: boost (RRF w=1) | 0.0 [0–2] | 10.5 [7–16] | 34.2 [28–41] | 25.5 [19–33] | 3.3 [1–8] | 8.4 [5–14] | 1.3 [0–5] | 70.0 [62–77] | 19.9 [18–22] |
| trail (noise 0.3): boost | 0.0 [0–2] | 10.5 [7–16] | 32.9 [27–39] | 25.5 [19–33] | 3.3 [1–8] | 8.4 [5–14] | 1.3 [0–5] | 70.0 [62–77] | 19.7 [18–22] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

**E3**

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| query-only top-10 | 0.0 [0–2] | 13.8 [9–20] | 32.4 [27–39] | 22.3 [16–29] | 1.3 [0–5] | 8.4 [5–14] | 2.0 [1–6] | 68.7 [61–76] | 19.3 [17–22] |
| query + mention->head forwarding (new) | 0.0 [0–2] | 14.5 [10–21] | 55.4 [49–62] | 21.0 [15–28] | 4.6 [2–9] | 8.4 [5–14] | 2.0 [1–6] | 63.3 [55–71] | 22.9 [21–25] |
| packet(5) + query(5) | 0.0 [0–2] | 11.2 [7–17] | 29.7 [24–36] | 17.8 [13–25] | 3.3 [1–8] | 8.4 [5–14] | 1.3 [0–5] | 59.3 [51–67] | 17.0 [15–19] |
| hand slot contract(<=5) + query | 3.9 [2–8] | 11.8 [8–18] | 83.3 [78–88] | 19.1 [14–26] | 9.9 [6–16] | 7.1 [4–12] | 1.3 [0–5] | 58.0 [50–66] | 27.4 [25–30] |
| entity cards(<=3, pinned) + query (cards indexed) | 7.8 [5–13] | 17.8 [13–25] | 95.5 [92–98] | 27.4 [21–35] | 8.6 [5–14] | 9.1 [5–15] | 2.0 [1–6] | 66.7 [59–74] | 32.8 [30–35] |
| cards(<=3) + hand static slots (<=5 total) + query | 13.1 [9–19] | 13.2 [9–19] | 97.3 [94–99] | 24.2 [18–31] | 11.9 [8–18] | 7.1 [4–12] | 2.0 [1–6] | 58.0 [50–66] | 32.0 [30–35] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

**E5**

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| no graph | 0.0 [0–2] | 13.8 [9–20] | 32.4 [27–39] | 22.3 [16–29] | 1.3 [0–5] | 8.4 [5–14] | 2.0 [1–6] | 68.7 [61–76] | 19.3 [17–22] |
| 1-hop, per-hop ACL, RRF w=1 | 0.0 [0–2] | 11.8 [8–18] | 38.3 [32–45] | 28.7 [22–36] | 2.6 [1–7] | 7.8 [5–13] | 1.3 [0–5] | 70.0 [62–77] | 21.0 [19–23] |
| 2-hop, per-hop ACL, RRF w=1 | 0.0 [0–2] | 11.8 [8–18] | 39.2 [33–46] | 29.3 [23–37] | 2.6 [1–7] | 7.8 [5–13] | 1.3 [0–5] | 70.0 [62–77] | 21.2 [19–24] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

**E7**

| arm | decision | option | current | temporal | goal | pref | cross | multimodal | ALL |
|---|---|---|---|---|---|---|---|---|---|
| top-k | 0.0 [0–2] | 13.8 [9–20] | 32.4 [27–39] | 22.3 [16–29] | 1.3 [0–5] | 8.4 [5–14] | 2.0 [1–6] | 68.7 [61–76] | 19.3 [17–22] |
| MMR (lambda=0.7, LSA sim) | 0.0 [0–2] | 13.8 [9–20] | 38.3 [32–45] | 18.5 [13–25] | 0.7 [0–4] | 7.8 [5–13] | 3.3 [1–7] | 61.3 [53–69] | 19.0 [17–21] |
| coverage packing (lambda=0.5) | 0.0 [0–2] | 11.8 [8–18] | 37.8 [32–44] | 17.2 [12–24] | 0.0 [0–2] | 4.5 [2–9] | 2.0 [1–6] | 59.3 [51–67] | 17.7 [16–20] |
| *n* | 153 | 152 | 222 | 157 | 151 | 154 | 152 | 150 | 1291 |

E5 leakage with BM25 base: no graph: 0 tasks / canary monitor n/a; 1-hop, per-hop ACL, 3 reserved slots: 0 tasks / canary monitor n/a; 2-hop, per-hop ACL, 3 reserved slots: 0 tasks / canary monitor n/a; 1-hop, per-hop ACL, RRF w=1: 0 tasks / canary monitor n/a; 2-hop, per-hop ACL, RRF w=1: 0 tasks / canary monitor n/a; 1-hop, NO per-hop ACL, 3 reserved slots: 73 tasks / canary monitor n/a; 2-hop, NO per-hop ACL, 3 reserved slots: 125 tasks / canary monitor n/a; 2-hop, NO per-hop ACL, RRF w=1: 56 tasks / canary monitor n/a
