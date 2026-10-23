# Batch 3 generated tables (BrainBench v0.3)

Rates are means over distinct need-sets (seed × class × set), CR_vital unless marked; brackets are Wilson 95% intervals; paired tests are exact sign tests over distinct sets with a cluster-bootstrap 95% CI.


## E9 / N8 / U1 — structure at write

Seeds per arm: A0 query-only: [1, 2, 3]; A1 router (batch-2 best, no gate): [1, 2, 3]; A2 code gate + nbhd: [1, 2, 3]; A5 gold gate + nbhd (typed first): [1, 2, 3]; A5c gold gate, cards only: [1, 2, 3]; A3 haiku gate + nbhd (typed first): [1]; A3c haiku gate, cards only: [1]; A3u haiku gate + nbhd (query order): [1]; X3r haiku gate + nbhd + rule pin (exploratory): [1]; X5r gold gate + nbhd + rule pin (exploratory): [1]; A4 sonnet gate + nbhd (typed first): [1]; A4c sonnet gate, cards only: [1]

### Pools (CR_vital %)

| arm | target5 v@10 | target5 v@50 | target5 v@100 | target5 v@T1000 | target5 v@T4000 | target5 v@T8000 | N8 pool v@10 | N8 pool v@50 | N8 pool v@100 | N8 pool v@T1000 | N8 pool v@T4000 | N8 pool v@T8000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 query-only | 11.3 | 28.8 | 40.2 | 28.8 | 53.7 | 60.0 | 9.9 | 20.3 | 27.6 | 19.3 | 34.9 | 41.7 |
| A1 router (batch-2 best, no gate) | 18.7 | 35.6 | 44.1 | 35.1 | 55.5 | 62.2 | 12.3 | 23.1 | 30.5 | 22.1 | 37.9 | 44.9 |
| A2 code gate + nbhd | 19.4 | 45.9 | 54.7 | 46.0 | 60.6 | 64.1 | 12.0 | 32.5 | 37.9 | 31.1 | 42.4 | 47.0 |
| A3c haiku gate, cards only | 22.5 | 39.2 | 47.9 | 38.7 | 58.6 | 66.2 | 11.1 | 24.4 | 32.9 | 23.3 | 40.7 | 49.0 |
| A3u haiku gate + nbhd (query order) | 23.3 | 51.8 | 61.6 | 49.8 | 67.3 | 70.7 | 13.2 | 39.6 | 45.9 | 36.9 | 51.0 | 55.8 |
| A3 haiku gate + nbhd (typed first) | 24.5 | 52.2 | 61.8 | 50.4 | 67.3 | 70.7 | 14.5 | 40.2 | 46.2 | 38.0 | 51.0 | 55.8 |
| A4c sonnet gate, cards only | 21.0 | 37.2 | 46.2 | 36.5 | 57.3 | 64.8 | 10.6 | 23.1 | 32.3 | 21.8 | 39.6 | 47.4 |
| A4 sonnet gate + nbhd (typed first) | 23.3 | 52.2 | 61.5 | 50.1 | 67.3 | 70.5 | 13.7 | 41.5 | 46.8 | 39.1 | 51.4 | 55.6 |
| A5c gold gate, cards only | 25.9 | 43.0 | 52.3 | 41.9 | 62.7 | 70.3 | 13.4 | 31.8 | 41.7 | 29.8 | 48.4 | 56.9 |
| A5 gold gate + nbhd (typed first) | 30.1 | 58.9 | 68.0 | 57.6 | 71.7 | 75.7 | 18.7 | 47.1 | 55.2 | 44.8 | 59.4 | 64.9 |

(n distinct sets: {'target5': 2004, 'N8 pool': 1212}; CR_vital, % — Wilson intervals in the per-class table)

### Per class (v@10)

| arm | decision | option | goal | pref | cross | current | temporal | media | aggreg | brief | oblig | rule-prec | reconcile | release | carry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 query-only | 12.0 [9–15] | 15.5 [12–19] | 20.7 [17–25] | 7.0 [5–10] | 2.4 [1–4] | 46.8 [44–49] | 38.8 [36–42] | 64.6 [60–69] | 17.3 [13–23] | 2.6 [1–7] | 49.5 [40–59] | 0.0 [0–9] | 17.6 [11–26] | 31.2 [23–41] | 13.0 [6–24] |
| A1 router (batch-2 best, no gate) | 17.6 [14–22] | 14.1 [11–18] | 55.0 [50–60] | 5.0 [3–8] | 5.4 [4–8] | 53.7 [51–56] | 38.8 [36–42] | 64.2 [59–69] | 16.9 [13–22] | 2.6 [1–7] | 47.7 [39–57] | 0.0 [0–9] | 18.6 [12–27] | 31.2 [23–41] | 13.0 [6–24] |
| A2 code gate + nbhd | 18.2 [15–22] | 14.3 [11–18] | 61.3 [56–66] | 3.8 [2–6] | 3.4 [2–6] | 56.1 [54–59] | 38.8 [36–42] | 64.2 [59–69] | 17.8 [13–23] | 2.6 [1–7] | 50.5 [41–60] | 0.0 [0–9] | 19.6 [13–28] | 17.2 [11–26] | 13.0 [6–24] |
| A3c haiku gate, cards only | 15.2 [10–22] | 10.9 [7–17] | 72.6 [64–80] | 10.7 [7–17] | 7.3 [4–13] | 62.5 [58–67] | 38.4 [34–43] | 62.0 [53–70] | 18.7 [11–29] | 10.3 [4–24] | 45.9 [31–62] | 0.0 [0–23] | 23.5 [12–40] | 32.3 [19–50] | 16.7 [6–39] |
| A3u haiku gate + nbhd (query order) | 20.3 [14–28] | 14.0 [9–21] | 72.6 [64–80] | 8.6 [5–14] | 5.5 [3–11] | 63.8 [60–68] | 38.4 [34–43] | 60.5 [52–68] | 21.3 [14–32] | 7.7 [3–20] | 54.1 [38–69] | 0.0 [0–23] | 35.3 [21–52] | 19.4 [9–36] | 16.7 [6–39] |
| A3 haiku gate + nbhd (typed first) | 21.7 [16–29] | 15.9 [11–23] | 75.0 [67–82] | 8.6 [5–14] | 5.8 [3–11] | 67.0 [63–71] | 38.4 [34–43] | 60.5 [52–68] | 20.0 [13–30] | 5.1 [1–17] | 43.2 [29–59] | 0.0 [0–23] | 41.2 [26–58] | 19.4 [9–36] | 16.7 [6–39] |
| A4c sonnet gate, cards only | 15.9 [11–23] | 10.9 [7–17] | 72.6 [64–80] | 5.0 [2–10] | 5.1 [2–10] | 64.7 [61–69] | 38.4 [34–43] | 61.6 [53–70] | 18.7 [11–29] | 7.7 [3–20] | 45.9 [31–62] | 0.0 [0–23] | 17.6 [8–34] | 32.3 [19–50] | 16.7 [6–39] |
| A4 sonnet gate + nbhd (typed first) | 23.6 [17–31] | 15.1 [10–22] | 77.4 [69–84] | 2.9 [1–7] | 2.6 [1–7] | 69.2 [65–73] | 38.4 [34–43] | 60.1 [51–68] | 21.3 [14–32] | 5.1 [1–17] | 43.2 [29–59] | 0.0 [0–23] | 38.2 [24–55] | 19.4 [9–36] | 16.7 [6–39] |
| A5c gold gate, cards only | 18.1 [15–22] | 12.0 [9–16] | 90.5 [87–93] | 4.8 [3–7] | 10.1 [8–13] | 80.9 [79–83] | 39.8 [37–43] | 63.6 [59–68] | 16.4 [12–22] | 12.8 [8–20] | 47.7 [39–57] | 0.0 [0–9] | 19.6 [13–28] | 30.1 [22–40] | 13.0 [6–24] |
| A5 gold gate + nbhd (typed first) | 30.9 [27–36] | 17.3 [14–21] | 89.8 [86–92] | 10.2 [8–14] | 7.8 [6–11] | 80.9 [79–83] | 39.8 [37–43] | 62.3 [57–67] | 17.3 [13–23] | 23.9 [17–32] | 68.5 [59–76] | 0.0 [0–9] | 35.3 [27–45] | 37.6 [28–48] | 13.0 [6–24] |
| *n sets* | 414 | 387 | 372 | 420 | 411 | 1602 | 1236 | 387 | 225 | 117 | 111 | 39 | 102 | 93 | 54 |

### Per class (v@50)

| arm | decision | option | goal | pref | cross | current | temporal | media | aggreg | brief | oblig | rule-prec | reconcile | release | carry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 query-only | 25.6 [22–30] | 29.3 [25–34] | 56.2 [51–61] | 29.3 [25–34] | 6.3 [4–9] | 63.8 [61–66] | 56.9 [54–60] | 76.9 [72–81] | 34.2 [28–41] | 31.6 [24–41] | 77.5 [69–84] | 0.0 [0–9] | 44.1 [35–54] | 45.2 [35–55] | 24.1 [15–37] |
| A1 router (batch-2 best, no gate) | 27.7 [24–32] | 29.3 [25–34] | 83.6 [79–87] | 28.8 [25–33] | 12.8 [10–16] | 67.4 [65–70] | 56.9 [54–60] | 76.9 [72–81] | 34.2 [28–41] | 31.6 [24–41] | 77.5 [69–84] | 0.0 [0–9] | 44.1 [35–54] | 45.2 [35–55] | 24.1 [15–37] |
| A2 code gate + nbhd | 30.9 [27–36] | 51.8 [47–57] | 90.2 [87–93] | 45.4 [41–50] | 15.8 [13–20] | 72.7 [70–75] | 56.8 [54–60] | 76.9 [72–81] | 40.9 [35–47] | 36.8 [29–46] | 81.1 [73–87] | 0.0 [0–9] | 47.1 [38–57] | 19.4 [13–29] | 24.1 [15–37] |
| A3c haiku gate, cards only | 29.0 [22–37] | 29.5 [22–38] | 91.5 [85–95] | 35.7 [28–44] | 15.0 [10–22] | 73.7 [70–77] | 58.1 [53–63] | 75.2 [67–82] | 33.3 [24–45] | 30.8 [19–46] | 78.4 [63–89] | 0.0 [0–23] | 52.9 [37–69] | 45.2 [29–62] | 22.2 [9–45] |
| A3u haiku gate + nbhd (query order) | 39.5 [32–48] | 55.4 [47–64] | 91.9 [86–96] | 51.4 [43–60] | 24.8 [18–33] | 77.1 [73–80] | 58.1 [53–63] | 75.2 [67–82] | 46.7 [36–58] | 38.5 [25–54] | 91.9 [79–97] | 0.0 [0–23] | 61.8 [45–76] | 19.4 [9–36] | 22.2 [9–45] |
| A3 haiku gate + nbhd (typed first) | 40.9 [33–49] | 55.8 [47–64] | 91.9 [86–96] | 51.4 [43–60] | 24.8 [18–33] | 78.0 [74–81] | 58.1 [53–63] | 73.6 [65–80] | 46.7 [36–58] | 48.7 [34–64] | 86.5 [72–94] | 0.0 [0–23] | 61.8 [45–76] | 25.8 [14–43] | 22.2 [9–45] |
| A4c sonnet gate, cards only | 29.3 [22–37] | 29.5 [22–38] | 91.5 [85–95] | 29.6 [23–38] | 10.9 [7–17] | 75.4 [72–79] | 58.4 [54–63] | 75.2 [67–82] | 33.3 [24–45] | 30.8 [19–46] | 78.4 [63–89] | 0.0 [0–23] | 50.0 [34–66] | 45.2 [29–62] | 22.2 [9–45] |
| A4 sonnet gate + nbhd (typed first) | 43.5 [35–52] | 57.8 [49–66] | 92.7 [87–96] | 47.1 [39–55] | 24.1 [18–32] | 80.1 [77–83] | 58.4 [54–63] | 73.6 [65–80] | 53.3 [42–64] | 48.7 [34–64] | 86.5 [72–94] | 0.0 [0–23] | 64.7 [48–79] | 25.8 [14–43] | 22.2 [9–45] |
| A5c gold gate, cards only | 33.7 [29–38] | 35.4 [31–40] | 94.5 [92–96] | 29.4 [25–34] | 26.6 [23–31] | 85.2 [83–87] | 59.7 [57–62] | 76.7 [72–81] | 34.2 [28–41] | 35.0 [27–44] | 77.5 [69–84] | 0.0 [0–9] | 49.0 [40–59] | 44.1 [34–54] | 24.1 [15–37] |
| A5 gold gate + nbhd (typed first) | 47.3 [43–52] | 62.7 [58–67] | 94.5 [92–96] | 61.4 [57–66] | 32.1 [28–37] | 85.2 [83–87] | 59.8 [57–63] | 76.9 [72–81] | 47.1 [41–54] | 59.8 [51–68] | 88.3 [81–93] | 0.0 [0–9] | 60.8 [51–70] | 63.4 [53–73] | 24.1 [15–37] |
| *n sets* | 414 | 387 | 372 | 420 | 411 | 1602 | 1236 | 387 | 225 | 117 | 111 | 39 | 102 | 93 | 54 |

### Per class (v@T4000)

| arm | decision | option | goal | pref | cross | current | temporal | media | aggreg | brief | oblig | rule-prec | reconcile | release | carry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 query-only | 36.2 [32–41] | 59.7 [55–64] | 89.5 [86–92] | 76.2 [72–80] | 10.2 [8–14] | 79.6 [78–81] | 70.0 [67–72] | 85.8 [82–89] | 55.6 [49–62] | 52.1 [43–61] | 88.3 [81–93] | 14.1 [6–28] | 60.8 [51–70] | 60.2 [50–70] | 27.8 [18–41] |
| A1 router (batch-2 best, no gate) | 37.2 [33–42] | 60.1 [55–65] | 90.7 [87–93] | 75.2 [71–79] | 17.8 [14–22] | 80.1 [78–82] | 70.0 [67–72] | 85.8 [82–89] | 55.6 [49–62] | 52.1 [43–61] | 88.3 [81–93] | 14.1 [6–28] | 60.8 [51–70] | 60.2 [50–70] | 27.8 [18–41] |
| A2 code gate + nbhd | 39.1 [35–44] | 67.3 [62–72] | 92.1 [89–94] | 85.2 [82–88] | 22.3 [19–27] | 80.9 [79–83] | 70.0 [67–72] | 85.8 [82–89] | 62.2 [56–68] | 55.6 [47–64] | 89.2 [82–94] | 14.1 [6–28] | 61.8 [52–71] | 59.1 [49–69] | 27.8 [18–41] |
| A3c haiku gate, cards only | 44.2 [36–53] | 57.8 [49–66] | 94.8 [89–98] | 78.2 [71–84] | 21.2 [15–29] | 84.2 [81–87] | 70.8 [66–75] | 83.7 [76–89] | 50.7 [40–62] | 59.0 [43–73] | 91.9 [79–97] | 23.1 [8–50] | 70.6 [54–83] | 54.8 [38–71] | 27.8 [12–51] |
| A3u haiku gate + nbhd (query order) | 49.6 [41–58] | 71.7 [63–79] | 95.2 [90–98] | 89.6 [83–94] | 32.8 [26–41] | 86.1 [83–89] | 70.8 [66–75] | 86.4 [79–91] | 64.0 [53–74] | 66.7 [51–79] | 97.3 [86–100] | 23.1 [8–50] | 73.5 [57–85] | 58.1 [41–74] | 27.8 [12–51] |
| A3 haiku gate + nbhd (typed first) | 49.6 [41–58] | 71.7 [63–79] | 95.2 [90–98] | 89.6 [83–94] | 32.8 [26–41] | 86.3 [83–89] | 70.8 [66–75] | 86.4 [79–91] | 64.0 [53–74] | 66.7 [51–79] | 97.3 [86–100] | 23.1 [8–50] | 73.5 [57–85] | 64.5 [47–79] | 27.8 [12–51] |
| A4c sonnet gate, cards only | 45.3 [37–54] | 57.8 [49–66] | 94.0 [88–97] | 75.7 [68–82] | 16.8 [11–24] | 85.8 [83–88] | 70.8 [66–75] | 83.7 [76–89] | 50.7 [40–62] | 59.0 [43–73] | 91.9 [79–97] | 23.1 [8–50] | 73.5 [57–85] | 54.8 [38–71] | 27.8 [12–51] |
| A4 sonnet gate + nbhd (typed first) | 50.7 [42–59] | 72.9 [65–80] | 94.4 [89–97] | 89.3 [83–93] | 31.8 [25–40] | 87.9 [85–90] | 70.8 [66–75] | 86.4 [79–91] | 69.3 [58–79] | 69.2 [54–81] | 94.6 [82–99] | 23.1 [8–50] | 82.4 [66–92] | 64.5 [47–79] | 27.8 [12–51] |
| A5c gold gate, cards only | 49.3 [44–54] | 61.5 [57–66] | 96.1 [94–98] | 74.5 [70–78] | 35.3 [31–40] | 90.1 [89–91] | 71.3 [69–74] | 86.0 [82–89] | 55.6 [49–62] | 52.1 [43–61] | 88.3 [81–93] | 14.1 [6–28] | 67.6 [58–76] | 60.2 [50–70] | 27.8 [18–41] |
| A5 gold gate + nbhd (typed first) | 56.2 [51–61] | 74.9 [70–79] | 96.1 [94–98] | 85.5 [82–89] | 47.9 [43–53] | 90.1 [89–91] | 71.4 [69–74] | 87.9 [84–91] | 68.9 [63–75] | 68.4 [59–76] | 92.8 [86–96] | 14.1 [6–28] | 72.5 [63–80] | 68.8 [59–77] | 27.8 [18–41] |
| *n sets* | 414 | 387 | 372 | 420 | 411 | 1602 | 1236 | 387 | 225 | 117 | 111 | 39 | 102 | 93 | 54 |

### Per class (a@50)

| arm | decision | option | goal | pref | cross | current | temporal | media | aggreg | brief | oblig | rule-prec | reconcile | release | carry |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 query-only | 7.6 [5–11] | 17.3 [14–21] | 23.0 [19–28] | 20.0 [16–24] | 0.7 [0–2] | 63.8 [61–66] | 56.9 [54–60] | 76.9 [72–81] | 34.2 [28–41] | 25.6 [19–34] | 77.5 [69–84] | 0.0 [0–9] | 34.3 [26–44] | 43.0 [33–53] | 24.1 [15–37] |
| A1 router (batch-2 best, no gate) | 7.9 [6–11] | 17.6 [14–22] | 43.4 [38–48] | 19.5 [16–24] | 4.3 [3–7] | 67.4 [65–70] | 56.9 [54–60] | 76.9 [72–81] | 34.2 [28–41] | 25.6 [19–34] | 77.5 [69–84] | 0.0 [0–9] | 34.3 [26–44] | 43.0 [33–53] | 24.1 [15–37] |
| A2 code gate + nbhd | 10.7 [8–14] | 41.0 [36–46] | 79.0 [75–83] | 43.8 [39–49] | 3.8 [2–6] | 72.7 [70–75] | 56.8 [54–60] | 76.9 [72–81] | 40.9 [35–47] | 29.9 [22–39] | 81.1 [73–87] | 0.0 [0–9] | 39.2 [30–49] | 17.2 [11–26] | 24.1 [15–37] |
| A3c haiku gate, cards only | 8.3 [5–14] | 19.0 [13–27] | 43.5 [35–52] | 25.7 [19–34] | 6.9 [4–12] | 73.7 [70–77] | 58.1 [53–63] | 75.2 [67–82] | 33.3 [24–45] | 28.2 [17–44] | 78.4 [63–89] | 0.0 [0–23] | 35.3 [21–52] | 45.2 [29–62] | 22.2 [9–45] |
| A3u haiku gate + nbhd (query order) | 15.2 [10–22] | 48.8 [40–57] | 79.0 [71–85] | 47.1 [39–55] | 10.9 [7–17] | 77.1 [73–80] | 58.1 [53–63] | 75.2 [67–82] | 46.7 [36–58] | 33.3 [21–49] | 91.9 [79–97] | 0.0 [0–23] | 52.9 [37–69] | 19.4 [9–36] | 22.2 [9–45] |
| A3 haiku gate + nbhd (typed first) | 14.5 [10–21] | 46.5 [38–55] | 79.4 [71–86] | 47.1 [39–55] | 10.9 [7–17] | 78.0 [74–81] | 58.1 [53–63] | 73.6 [65–80] | 46.7 [36–58] | 43.6 [29–59] | 86.5 [72–94] | 0.0 [0–23] | 55.9 [39–71] | 22.6 [11–40] | 22.2 [9–45] |
| A4c sonnet gate, cards only | 9.1 [5–15] | 19.4 [13–27] | 43.5 [35–52] | 23.2 [17–31] | 2.9 [1–7] | 75.4 [72–79] | 58.4 [54–63] | 75.2 [67–82] | 33.3 [24–45] | 28.2 [17–44] | 78.4 [63–89] | 0.0 [0–23] | 32.4 [19–49] | 45.2 [29–62] | 22.2 [9–45] |
| A4 sonnet gate + nbhd (typed first) | 15.9 [11–23] | 48.4 [40–57] | 82.3 [75–88] | 46.4 [38–55] | 5.8 [3–11] | 80.1 [77–83] | 58.4 [54–63] | 73.6 [65–80] | 53.3 [42–64] | 46.2 [32–61] | 86.5 [72–94] | 0.0 [0–23] | 58.8 [42–74] | 22.6 [11–40] | 22.2 [9–45] |
| A5c gold gate, cards only | 21.3 [18–25] | 29.3 [25–34] | 55.8 [51–61] | 28.1 [24–33] | 12.2 [9–16] | 85.2 [83–87] | 59.7 [57–62] | 76.7 [72–81] | 34.2 [28–41] | 29.1 [22–38] | 77.5 [69–84] | 0.0 [0–9] | 44.1 [35–54] | 44.1 [34–54] | 24.1 [15–37] |
| A5 gold gate + nbhd (typed first) | 36.1 [32–41] | 57.8 [53–63] | 84.5 [81–88] | 60.8 [56–65] | 14.6 [12–18] | 85.2 [83–87] | 59.8 [57–63] | 76.9 [72–81] | 47.1 [41–54] | 55.6 [47–64] | 88.3 [81–93] | 0.0 [0–9] | 55.9 [46–65] | 63.4 [53–73] | 24.1 [15–37] |
| *n sets* | 414 | 387 | 372 | 420 | 411 | 1602 | 1236 | 387 | 225 | 117 | 111 | 39 | 102 | 93 | 54 |

### Paired tests (common seeds only)

- **A3 haiku gate + nbhd (typed first) vs A1 router (batch-2 best, no gate)** (seeds [1]):
  - target5 @K50: +16.2 pp [+13.2, +19.1], +134/−13, p=1.7e-26; @K10: +5.8 pp [+3.2, +8.3], +62/−20, p=3.7e-06; @T4k: +11.3 pp [+9.1, +13.6], +93/−4, p=4.6e-23
  - N8 pool @K50: +18.3 pp [+14.5, +22.0], +86/−3, p=3.8e-22; @K10: +3.1 pp [+0.7, +5.6], +23/−7, p=0.0052; @T4k: +14.0 pp [+10.5, +17.5], +68/−3, p=5.1e-17
  - decision+option+goal @K50: +15.1 pp [+11.5, +18.7], +70/−2, p=1.1e-18
- **A1 router (batch-2 best, no gate) vs A0 query-only** (seeds [1, 2, 3]):
  - target5 @K50: +6.7 pp [+5.6, +7.8], +154/−9, p=3.2e-35; @K10: +7.4 pp [+6.0, +8.8], +193/−41, p=9.1e-25; @T4k: +1.8 pp [+1.3, +2.5], +47/−6, p=5.8e-09
  - N8 pool @K50: +2.9 pp [+1.9, +4.0], +46/−7, p=4e-08; @K10: +2.5 pp [+1.3, +3.7], +56/−22, p=0.00015; @T4k: +3.0 pp [+2.2, +4.0], +41/−0, p=9.1e-13
  - decision+option+goal @K50: +9.4 pp [+7.8, +11.1], +124/−6, p=9.2e-30
- **A2 code gate + nbhd vs A1 router (batch-2 best, no gate)** (seeds [1, 2, 3]):
  - target5 @K50: +10.3 pp [+8.9, +11.9], +278/−39, p=1.3e-45; @K10: +0.7 pp [+0.0, +1.3], +34/−20, p=0.076; @T4k: +5.1 pp [+4.2, +6.0], +125/−3, p=2.1e-33
  - N8 pool @K50: +9.3 pp [+7.8, +11.1], +143/−11, p=1.9e-30; @K10: -0.4 pp [-1.0, +0.3], +9/−13, p=0.52; @T4k: +4.5 pp [+3.4, +5.7], +70/−3, p=1.4e-17
  - decision+option+goal @K50: +10.7 pp [+9.1, +12.4], +148/−0, p=5.6e-45
- **A3 haiku gate + nbhd (typed first) vs A2 code gate + nbhd** (seeds [1]):
  - target5 @K50: +6.1 pp [+4.0, +8.1], +55/−9, p=3.5e-09; @K10: +5.5 pp [+3.2, +7.9], +57/−15, p=6.5e-07; @T4k: +6.1 pp [+4.3, +7.9], +51/−4, p=2e-11
  - N8 pool @K50: +8.9 pp [+6.2, +11.8], +44/−2, p=3.1e-11; @K10: +3.8 pp [+1.7, +6.1], +23/−4, p=0.00031; @T4k: +9.4 pp [+6.7, +12.1], +46/−2, p=8.4e-12
  - decision+option+goal @K50: +5.4 pp [+3.1, +7.7], +27/−3, p=8.4e-06
- **A3 haiku gate + nbhd (typed first) vs A3c haiku gate, cards only** (seeds [1]):
  - target5 @K50: +12.9 pp [+10.3, +15.8], +108/−12, p=1.8e-20; @K10: +2.0 pp [+0.3, +3.8], +31/−13, p=0.0096; @T4k: +8.7 pp [+6.7, +10.7], +72/−2, p=2.9e-19
  - N8 pool @K50: +15.8 pp [+12.4, +19.4], +75/−3, p=5.2e-19; @K10: +3.3 pp [+1.2, +5.7], +22/−4, p=0.00053; @T4k: +10.3 pp [+7.4, +13.1], +51/−2, p=3.2e-13
  - decision+option+goal @K50: +13.0 pp [+9.8, +16.5], +59/−1, p=1.1e-16
- **A3 haiku gate + nbhd (typed first) vs A3u haiku gate + nbhd (query order)** (seeds [1]):
  - target5 @K50: +0.4 pp [+0.0, +0.8], +3/−0, p=0.25; @K10: +1.2 pp [+0.2, +2.2], +14/−3, p=0.013; @T4k: +0.0 pp [+0.0, +0.0], +0/−0, p=1
  - N8 pool @K50: +0.6 pp [+0.0, +1.4], +3/−0, p=0.25; @K10: +1.2 pp [+0.4, +2.4], +7/−0, p=0.016; @T4k: +0.0 pp [+0.0, +0.0], +0/−0, p=1
  - decision+option+goal @K50: +0.6 pp [+0.0, +1.5], +3/−0, p=0.25
- **A4 sonnet gate + nbhd (typed first) vs A3 haiku gate + nbhd (typed first)** (seeds [1]):
  - target5 @K50: +0.0 pp [-1.4, +1.4], +17/−14, p=0.72; @K10: -1.2 pp [-2.6, +0.2], +9/−17, p=0.17; @T4k: +0.0 pp [-1.2, +1.3], +12/−11, p=1
  - N8 pool @K50: +1.2 pp [-0.5, +3.0], +14/−6, p=0.12; @K10: -0.7 pp [-2.1, +0.5], +4/−7, p=0.55; @T4k: +0.4 pp [-1.4, +2.1], +11/−8, p=0.65
  - decision+option+goal @K50: +1.8 pp [+0.6, +3.2], +9/−0, p=0.0039
- **A5 gold gate + nbhd (typed first) vs A3 haiku gate + nbhd (typed first)** (seeds [1]):
  - target5 @K50: +6.3 pp [+4.6, +8.3], +55/−5, p=1e-11; @K10: +4.7 pp [+2.7, +6.7], +48/−14, p=1.7e-05; @T4k: +5.2 pp [+3.4, +6.9], +45/−5, p=4.2e-09
  - N8 pool @K50: +5.7 pp [+3.5, +8.2], +31/−2, p=1.3e-07; @K10: +3.3 pp [+1.4, +5.3], +18/−4, p=0.0043; @T4k: +8.3 pp [+5.7, +11.1], +41/−2, p=2.2e-10
  - decision+option+goal @K50: +4.0 pp [+2.2, +5.9], +21/−1, p=1.1e-05
- **A4 sonnet gate + nbhd (typed first) vs A1 router (batch-2 best, no gate)** (seeds [1]):
  - target5 @K50: +16.2 pp [+13.3, +19.0], +136/−12, p=9e-28; @K10: +4.6 pp [+2.4, +6.8], +52/−18, p=5.8e-05; @T4k: +11.3 pp [+9.1, +13.5], +94/−4, p=2.4e-23
  - N8 pool @K50: +19.6 pp [+15.7, +23.4], +94/−3, p=1.9e-24; @K10: +2.4 pp [+0.2, +4.6], +20/−7, p=0.019; @T4k: +14.4 pp [+11.1, +17.8], +71/−3, p=7.2e-18
  - decision+option+goal @K50: +16.9 pp [+13.3, +20.5], +78/−1, p=2.6e-22
- **A5 gold gate + nbhd (typed first) vs A1 router (batch-2 best, no gate)** (seeds [1, 2, 3]):
  - target5 @K50: +23.3 pp [+21.5, +25.2], +551/−21, p=1.5e-134; @K10: +11.4 pp [+9.8, +13.0], +294/−47, p=8.1e-45; @T4k: +16.1 pp [+14.6, +17.7], +386/−6, p=9.8e-106
  - N8 pool @K50: +23.9 pp [+21.7, +26.2], +341/−9, p=1.8e-88; @K10: +6.4 pp [+4.8, +8.0], +118/−28, p=2.4e-14; @T4k: +21.5 pp [+19.3, +23.7], +307/−5, p=5.8e-84
  - decision+option+goal @K50: +21.4 pp [+19.3, +23.8], +294/−1, p=9.3e-87

### CR_vital@50 by reference form (all classes with an entity reference)

| arm | registry | seen | heldout_desc | heldout_nick |
|---|---|---|---|---|
| A0 query-only | 63.7 [61–66] | 20.5 [18–23] | 24.9 [22–28] | 24.9 [22–28] |
| A1 router (batch-2 best, no gate) | 66.2 [64–69] | 21.4 [19–24] | 25.1 [22–29] | 25.6 [23–29] |
| A2 code gate + nbhd | 72.3 [70–75] | 22.2 [19–25] | 25.6 [22–29] | 26.0 [23–29] |
| A3c haiku gate, cards only | 64.8 [60–69] | 36.7 [31–42] | 23.6 [19–29] | 28.0 [23–34] |
| A3u haiku gate + nbhd (query order) | 72.2 [68–76] | 50.7 [45–56] | 23.6 [19–29] | 28.5 [23–35] |
| A3 haiku gate + nbhd (typed first) | 74.7 [70–79] | 51.0 [45–57] | 23.6 [19–29] | 28.5 [23–35] |
| A4c sonnet gate, cards only | 64.8 [60–69] | 39.6 [34–45] | 23.2 [18–29] | 28.0 [23–34] |
| A4 sonnet gate + nbhd (typed first) | 75.2 [71–79] | 60.1 [54–66] | 23.2 [18–29] | 28.5 [23–35] |
| A5c gold gate, cards only | 75.3 [73–78] | 46.2 [43–50] | 26.6 [23–30] | 27.1 [24–30] |
| A5 gold gate + nbhd (typed first) | 81.9 [80–84] | 63.7 [60–67] | 26.6 [23–30] | 27.1 [24–30] |

### Write-gate extraction quality (vs gold; seed-level)

| gate | seed | link P | link P (lenient) | link R | implicit R | explicit R | req-evidence link R | keyed-fact recall | wrong value | decision | constraint | plan | issue | offer | preference |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| code | 1 | 68.0 | 76.8 | 83.7 | 72.9 | 99.4 | 90.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| code | 2 | 67.8 | 76.9 | 83.5 | 72.6 | 99.4 | 91.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| code | 3 | 68.2 | 77.1 | 83.6 | 72.9 | 99.4 | 90.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| gate_haiku | 1 | 77.7 | 87.3 | 92.3 | 87.6 | 99.1 | 92.9 | 82.3 | 9.6 | 36.2 | 79.7 | 82.9 | 72.1 | 98.7 | 91.0 |
| gate_sonnet | 1 | 78.2 | 87.5 | 95.4 | 92.8 | 99.2 | 95.9 | 89.8 | 8.2 | 36.2 | 74.6 | 77.1 | 57.9 | 98.7 | 99.0 |
| gold | 1 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| gold | 2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 100.0 | 0.0 | 100.0 | 100.0 | 0.0 | 100.0 |
| gold | 3 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 100.0 | 0.0 | 100.0 | 100.0 | 0.0 | 100.0 |

### Structure reach: share of VITAL free-text items reachable by structure (target classes)

| gate | seeds | reach (item-weighted) | tasks with every vital free-text item reachable | registry | seen | heldout_desc | heldout_nick |
|---|---|---|---|---|---|---|---|
| code | [1, 2, 3] | 40.5 (with parent entities: 47.5) | 36.0 | 55.9 | 4.2 | 5.0 | 4.5 |
| gate_haiku | [1] | 44.4 (with parent entities: 52.3) | 40.6 | 56.2 | 46.5 | 3.1 | 4.6 |
| gate_sonnet | [1] | 46.3 (with parent entities: 55.4) | 42.3 | 56.2 | 55.9 | 3.1 | 4.6 |
| gold | [1, 2, 3] | 47.1 (with parent entities: 54.9) | 43.1 | 59.3 | 67.5 | 5.0 | 5.1 |

## Release-safe drafting: requester visibility vs requester ∩ recipient

| visibility | forbidden private note in context @10 | @50 | CR_vital@10 | CR_vital@50 | seeds |
|---|---|---|---|---|---|
| requester | 19.4 [9–36] | 45.2 [29–62] | 19.4 [9–36] | 25.8 [14–43] | [1] |
| intersection | 0.0 [0–11] | 0.0 [0–11] | 19.4 [9–36] | 29.0 [16–47] | [1] |

## E10 / E10b / U2 / U2a — double entry


### Query side A0: CR_vital@50 by reference form (all classes)

| entry | seeds | registry | seen | heldout_desc | heldout_nick | held-out pooled | all |
|---|---|---|---|---|---|---|---|
| raw | [1] | 61.7 [57–66] | 23.0 [19–28] | 22.8 [18–29] | 27.1 [22–33] | 25.1 [21–29] | 50.0 [48–52] |
| header | [1] | 72.0 [67–76] | 43.0 [37–49] | 27.6 [22–34] | 27.6 [22–34] | 27.9 [24–32] | 60.2 [58–62] |

Paired (sign test over distinct sets):
- A0: **header vs raw** on ['seen']: @K50 +20.0 pp [+15.4, +24.7], +62/−3, p=2.5e-15; @K10 +12.3 pp [+8.2, +16.4], +41/−5, p=4.4e-08
- A0: **header vs raw** on ['heldout_desc', 'heldout_nick']: @K50 +2.8 pp [+0.5, +5.2], +21/−8, p=0.024; @K10 +0.8 pp [-1.0, +2.8], +12/−8, p=0.5

### Query side A3: CR_vital@50 by reference form (all classes)

| entry | seeds | registry | seen | heldout_desc | heldout_nick | held-out pooled | all |
|---|---|---|---|---|---|---|---|
| raw | [1] | 74.7 [70–79] | 51.0 [45–57] | 23.6 [19–29] | 28.5 [23–35] | 26.2 [22–31] | 61.2 [59–63] |
| header | [1] | 78.4 [74–82] | 59.4 [54–65] | 28.5 [23–34] | 28.0 [23–34] | 28.6 [25–33] | 65.5 [63–68] |

Paired (sign test over distinct sets):
- A3: **header vs raw** on ['seen']: @K50 +8.4 pp [+4.1, +12.8], +35/−10, p=0.00025; @K10 +3.8 pp [+0.5, +7.3], +21/−10, p=0.071
- A3: **header vs raw** on ['heldout_desc', 'heldout_nick']: @K50 +2.4 pp [+0.0, +4.6], +20/−9, p=0.061; @K10 +1.2 pp [-0.6, +3.2], +13/−7, p=0.26

### Stale exposure (stale probes) paired with temporal CR on the same keys

| entry / query side | stale exposure @10 | unresolved stale (no current value) | current value found @10 | temporal CR_vital@10 (paired keys) | n probes |
|---|---|---|---|---|---|
| header / A0 | 30.6 [26–36] | 13.3 | 52.1 | 44.1 | 330 |
| raw / A0 | 29.4 [25–35] | 13.3 | 47.0 | 38.4 | 330 |
| header / A3 | 12.7 [10–17] | 7.3 | 67.9 | 44.1 | 330 |
| raw / A3 | 13.0 [10–17] | 8.8 | 66.4 | 38.4 | 330 |

## H17 — aggregation (exact-set)

| records from | seeds | exact-set recall (records) | recall (item) | precision | absence correct | top-K exact @10 / @50 / @100 |
|---|---|---|---|---|---|---|
| gold | [1, 2, 3] | 72.6 [66–78] | 74.4 | 30.9 | 0.0 (n=24) | 15.1 / 32.4 / 49.8 |
| code | [1, 2, 3] | 0.0 [0–2] | 0.0 | 0.0 | 100.0 (n=24) | 15.1 / 32.4 / 49.8 |
| gate_haiku | [1] | 39.7 [29–51] | 61.4 | 12.9 | 0.0 (n=10) | 16.4 / 31.5 / 46.6 |

## I15 — certified recall (worst-vital-item split conformal, α = 0.10)


## ADR checks


### DA1-4 BM25 statistics policy (query-only)

Share of query terms unseen in WikiText-2: 7.3%

| statistics | retriever | ALL v@10 | ALL v@50 | target5 v@50 | current v@10 | temporal v@10 |
|---|---|---|---|---|---|---|
| frozen | bm25 | 31.5 [30–33] | 55.0 | 40.7 | 43.9 | 41.6 |
| global | bm25 | 27.8 [27–29] | 51.8 | 39.2 | 37.4 | 38.3 |
| partition | bm25 | 21.2 [20–22] | 47.4 | 38.1 | 30.2 | 18.1 |
| visible | bm25 | 28.2 [27–29] | 52.1 | 39.2 | 38.5 | 36.9 |
| frozen | hybrid | 31.3 [30–33] | 49.0 | 28.5 | 47.0 | 39.4 |
| global | hybrid | 30.9 [30–32] | 48.6 | 28.9 | 46.6 | 38.5 |
| partition | hybrid | 30.6 [29–32] | 48.3 | 29.1 | 47.1 | 35.1 |
| visible | hybrid | 31.1 [30–32] | 48.6 | 28.8 | 46.8 | 38.8 |
- bm25: **frozen vs visible** @10: +3.4 pp [+2.7, +4.0], +373/−141, p=3.3e-25; @50: +2.9 pp [+2.3, +3.5], +297/−105, p=2.5e-22
- bm25: **partition vs visible** @10: -7.0 pp [-7.7, -6.2], +87/−535, p=1.4e-79; @50: -4.7 pp [-5.2, -4.1], +63/−369, p=1e-53
- bm25: **global vs visible** @10: -0.4 pp [-0.8, -0.1], +57/−81, p=0.05; @50: -0.3 pp [-0.5, -0.0], +23/−40, p=0.043
- hybrid: **frozen vs visible** @10: +0.3 pp [-0.2, +0.7], +113/−89, p=0.11; @50: +0.5 pp [+0.1, +0.8], +98/−70, p=0.037
- hybrid: **partition vs visible** @10: -0.5 pp [-0.8, -0.1], +61/−91, p=0.018; @50: -0.3 pp [-0.6, +0.0], +52/−72, p=0.088
- hybrid: **global vs visible** @10: -0.2 pp [-0.3, -0.1], +10/−25, p=0.017; @50: +0.0 pp [-0.1, +0.2], +13/−13, p=1

### S2 / S3 twin-world noninterference vs canaries

Identities: ['lachlan', 'rhea', 'tomas', 'priya', 'coach_s_ben_okafor', 'coach_s_corey_lin', 'coach_s_imogen_hartley', 'member_m05', 'member_m21', 'member_m33']. No-grant credential: {'rows': 0, 'err': 'no_grant'}

| engine | twin-world: identities with any observable change | ids changed | own-revocation equivalence failures | canary alarms / probes |
|---|---|---|---|---|
| none | 0/10 | 0/10 | 0/3 | 0/360 |
| seed_only_hop | 10/10 | 10/10 | 3/3 | 0/360 |
| global_idf | 10/10 | 3/10 | 3/3 | 0/360 |
| query_cache | 10/10 | 5/10 | 3/3 | 0/360 |
| hidden_snippet | 10/10 | 0/10 | 0/3 | 208/360 |
| count_before_filter | 10/10 | 0/10 | 0/3 | 0/360 |
| global_tiebreak | 10/10 | 10/10 | 3/3 | 0/360 |
| stale_revocation_cache | 0/10 | 0/10 | 3/3 | 0/360 |
| card_widening | 8/10 | 0/10 | 0/3 | 0/360 |
| shared_prefix_cache | 5/10 | 0/10 | 0/3 | 0/360 |
| semantic_cache | 10/10 | 5/10 | 3/3 | 0/360 |

### DA1-6 history growth: version rows vs key timelines (temporal and current state, CR_vital@10)

| extra versions per key | arm | temporal v@10 | temporal v@50 | current v@10 | seeds |
|---|---|---|---|---|---|
| 0 | rows | 52.9 [50–56] | 63.4 | 47.0 | [1, 2, 3] |
| 0 | timeline | 54.1 [51–57] | 64.4 | 47.0 | [1, 2, 3] |
| 10 | rows | 48.7 [46–52] | 60.7 | 47.2 | [1, 2, 3] |
| 10 | timeline | 54.0 [51–57] | 64.5 | 47.2 | [1, 2, 3] |
| 40 | rows | 47.5 [45–50] | 57.1 | 47.2 | [1, 2, 3] |
| 40 | timeline | 53.8 [51–57] | 64.0 | 47.2 | [1, 2, 3] |

### DA1-7 values-free stub cards (read-time values) vs stored cards (cards ≤3 + query)

- gate_haiku gate: stored 39.4 [37–42] vs stub 39.5 [37–42] (ALL v@10); stub vs stored +0.0 pp [-0.2, +0.3], +4/−3, p=1; @50 +0.0 pp [-0.1, +0.2], +2/−1, p=1
- gold gate: stored 44.9 [43–47] vs stub 45.1 [43–47] (ALL v@10); stub vs stored +0.1 pp [-0.1, +0.4], +6/−3, p=0.51; @50 +0.1 pp [-0.2, +0.3], +5/−3, p=0.73

### Exit check vs a delayed index (revocation + erasure)

- seed 1: leaks without exit check: 1813 items in 302 task contexts (top 50) + 364 items in revoked-coach probes; with exit check: 0. CR_vital@10 on unaffected tasks: 30.2 → 30.3 (+0.1 pp [+0.0, +0.2], +1/−0, p=1).
- seed 2: leaks without exit check: 1554 items in 344 task contexts (top 50) + 190 items in revoked-coach probes; with exit check: 0. CR_vital@10 on unaffected tasks: 30.5 → 30.5 (+0.0 pp [+0.0, +0.0], +0/−0, p=1).
- seed 3: leaks without exit check: 1684 items in 312 task contexts (top 50) + 214 items in revoked-coach probes; with exit check: 0. CR_vital@10 on unaffected tasks: 32.4 → 32.4 (+0.0 pp [+0.0, +0.1], +1/−0, p=1).

## E11 — self-healing vocabulary (simulated year)

| seed | arm | held-out CR_vital@50 months 0–2 | months 9–11 | drifted phrases after drift | control regressions vs none | corrections |
|---|---|---|---|---|---|---|
| 1 | none | 16.8 | 19.8 | 14.0 | 0 | 150 |
| 1 | item-append | 27.1 | 56.2 | 23.3 | 0 | 110 |
| 1 | entity-alias | 32.7 | 55.2 | 27.9 | 0 | 99 |

## DT-U1a fabrication suite (seed 1; 100 stated + 100 not-stated fields)

| writer / schema | fabrication (raw) | fabrication after code validator | recall (raw) | recall after validator | answered |
|---|---|---|---|---|---|
| haiku/required | 6.1 [3–13] | 6.1 [3–13] | 96.0 | 94.0 | 199 |
| haiku/nullable | 6.1 [3–13] | 6.1 [3–13] | 96.0 | 96.0 | 199 |
| haiku/span | 4.0 [2–10] | 4.0 [2–10] | 97.0 | 97.0 | 199 |
| sonnet/required | 6.1 [3–13] | 6.1 [3–13] | 96.0 | 96.0 | 199 |
| sonnet/nullable | 3.0 [1–9] | 3.0 [1–9] | 99.0 | 99.0 | 199 |
| sonnet/span | 2.0 [1–7] | 2.0 [1–7] | 97.0 | 97.0 | 199 |

## E-SCR — the owner's scribe (seed 1)

| writer | entries | unparsable | clean at first check (G0) | coverage keep-worthy | coverage implicit | filler recorded | spouse turns recorded | invented value tokens | link P | link R | G1 extra flags |
|---|---|---|---|---|---|---|---|---|---|---|---|
| haiku | 202 | 0 | 199/202 | 52.0 | 66.7 | 32.0 | 0/40 | 4/255 (1.6) | 67.5 | 61.9 | 4 {'C2': 4} |

haiku: G0 rule counts {'SC04': 3}; summary: 3 problem(s); 202 entries checked

Seeded bad readings (haiku): wrong_value: n=30, G0 caught 0, G1 29, G2 29, G1+C6 29, G2+C6 29; wrong_entity: n=30, G0 caught 1, G1 3, G2 7, G1+C6 16, G2+C6 16; unsupported: n=30, G0 caught 27, G1 29, G2 29, G1+C6 30, G2+C6 30 (G2 threshold 0.001, set at a 10% flag rate on 103 unseeded readings)
| sonnet | 268 | 0 | 262/268 | 64.0 | 80.4 | 68.0 | 0/40 | 3/412 (0.7) | 72.4 | 71.2 | 2 {'C2': 2} |

sonnet: G0 rule counts {'SC25': 5, 'SC19': 1}; summary: 6 problem(s); 268 entries checked

Seeded bad readings (sonnet): wrong_value: n=30, G0 caught 0, G1 29, G2 29, G1+C6 29, G2+C6 29; wrong_entity: n=30, G0 caught 3, G1 5, G2 11, G1+C6 18, G2+C6 19; unsupported: n=30, G0 caught 24, G1 29, G2 29, G1+C6 29, G2+C6 29 (G2 threshold 0.000, set at a 10% flag rate on 138 unseeded readings)

Spoof probe (home: self-confirmation): {'g0_flags_spoof': False, 'g0_summary': 'clean: 2 entries', 'g1_flags_spoof': True, 'g1': [('C1', "home: reference not in home base's review list")]}

## Spend ledger

| stage | model | calls | USD | output tokens | wall s |
|---|---|---|---|---|---|
| escr-haiku | claude-haiku-5-5 | 6 | 0.12 | 155441 | 605 |
| escr-sonnet | claude-sonnet-5-5 | 6 | 1.37 | 54544 | 306 |
| fab-haiku-nullable | claude-haiku-5-5 | 4 | 0.02 | 21290 | 77 |
| fab-haiku-required | claude-haiku-5-5 | 4 | 0.02 | 21115 | 80 |
| fab-haiku-span | claude-haiku-5-5 | 4 | 0.02 | 29245 | 97 |
| fab-sonnet-nullable | claude-sonnet-5-5 | 4 | 0.21 | 8296 | 49 |
| fab-sonnet-required | claude-sonnet-5-5 | 4 | 0.25 | 11723 | 70 |
| fab-sonnet-span | claude-sonnet-5-5 | 4 | 0.25 | 12403 | 70 |
| gate-haiku-s1 | claude-haiku-5-5 | 176 | 1.47 | 2204079 | 8255 |
| gate-haiku-s2 | claude-haiku-5-5 | 24 | 0.21 | 312829 | 1155 |
| gate-sonnet-s1 | claude-sonnet-5-5 | 167 | 13.02 | 774599 | 4503 |
| orphan-adjustment | claude-haiku-5-5 | 2 | 0.02 | 0 | 0 |
| pilot-haiku | claude-haiku-5-5 | 3 | 0.03 | 38806 | 133 |
| pilot-haiku-effort-low | claude-haiku-5-5 | 3 | 0.03 | 32843 | 116 |
| pilot-sonnet | claude-sonnet-5-5 | 3 | 0.32 | 14014 | 74 |
| **total** | | | **17.35** | | |
