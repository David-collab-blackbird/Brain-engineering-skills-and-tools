# R6 sandbox check (E13b-lite): conformal "all vital items" sets on existing BrainBench v0.2 rankings.
# For each task we compute r = the smallest K such that ALL required items are in the top K of an arm's ranking
# (cards cover their items, as in DA2 A7). Then per class:
#   (a) split conformal on r  -> fixed K_hat per class  (guarantee: P(all vital in top K_hat) >= 1-alpha, marginal, exchangeable)
#   (b) CRC on the false-negative-rate loss (recall)  -> shows expected-recall control is NOT all-items coverage
#   (c) adaptive per-request sets: nonconformity = normalised score gap of the worst-ranked vital item (query-only arm)
# Calibration/test split is by distinct required set (set_id), 50/50, repeated R times. Also cross-seed: calibrate s1, test s2/s3.
import sys, os, collections, time, json, math, random
os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.path.insert(0, '/home/claude/brainbench')
import numpy as np
from bb.ctx2 import Ctx, CLASSES2, query_ranked, fill, ids_of, live
from bb.experiments2 import Assembler
from bb.retrieval import item_text

NMAX = 400
ALPHA = 0.10
OUT = os.path.dirname(os.path.abspath(__file__))


def rank_needed(ids, t, covers):
    req = set(t['required']); got = set()
    for k, i in enumerate(ids, 1):
        got.add(i); got |= covers.get(i, set())
        if req <= got:
            return k
    return math.inf


def per_seed(seed):
    t0 = time.time()
    ctx = Ctx(seed, embedders=("bge-small",), lsa=False)
    A = Assembler(ctx, method="wsum", emb="bge-small", alpha=0.2)
    bc = ctx.bc
    tok = np.array([max(1, int(len(item_text(it, True).split()) * 1.3)) for it in bc.ix.items])
    byent = collections.defaultdict(list)
    for i, it in enumerate(bc.ix.items):
        if it.get('derived'):
            continue
        for e in it.get('entities') or []:
            byent[e].append(i)
    rows = []
    for t in ctx.tasks:
        ranked = query_ranked(bc, A.sc, t, n=NMAX)
        m, temporal = live(bc, t)
        s = A.sc.fused(t['query'], t['requester'], m)
        arms = {}
        arms['query'] = ranked
        pre = A.card_prefix(t, 3, True)
        ents = ctx.L.link(t['query'], t['requester'])
        nb = sorted({i for e in ents for i in byent[e] if m[i] and np.isfinite(s[i])}, key=lambda i: -s[i])
        arms['nbhd'] = fill(pre + [i for i in nb if i not in pre], ranked, NMAX)
        r = dict(seed=seed, id=t['id'], cls=t['cls'], set_id=t['set_id'], size=len(t['required']))
        for a, idx in arms.items():
            ids = ids_of(bc, idx)
            r[f'r_{a}'] = rank_needed(ids, t, ctx.covers)
            ctoks = np.cumsum([tok[i] for i in idx])
            r[f'tok_{a}'] = ctoks.tolist()[:NMAX]
        # adaptive score for the query arm: normalised gap of worst vital item (recall-style, cards ignored here)
        top = s[ranked[0]] if ranked else 0.0
        gaps = []
        for q in t['required']:
            p = bc.pos.get(q) if hasattr(bc.pos, 'get') else bc.pos[q]
            v = s[p] if (p is not None and np.isfinite(s[p])) else -np.inf
            gaps.append((top - v) / (abs(top) + 1e-9) if np.isfinite(v) else math.inf)
        r['gap_worst'] = float(max(gaps))
        # per-request set sizes for a grid of gap thresholds (count of items with normalised gap <= tau)
        fin = np.isfinite(s)
        g_all = np.where(fin, (top - s) / (abs(top) + 1e-9), np.inf)
        r['gap_sorted'] = np.sort(g_all[fin])[:2000].astype(float).tolist()
        # recall at K for CRC
        req = set(t['required'])
        rec = []
        got = set()
        for k, i in enumerate(ids_of(bc, arms['query'])[:NMAX], 1):
            got.add(i); got |= ctx.covers.get(i, set())
            rec.append(len(got & req) / len(req))
        r['rec_query'] = rec
        rows.append(r)
    print('seed', seed, 'tasks', len(rows), 't', round(time.time() - t0), flush=True)
    return rows


def conf_quantile(scores, alpha):
    n = len(scores)
    k = math.ceil((n + 1) * (1 - alpha))
    if k > n:
        return math.inf
    return sorted(scores)[k - 1]


def split_by_set(rows, rng):
    sets = sorted({r['set_id'] for r in rows}); rng.shuffle(sets)
    cal = set(sets[:len(sets) // 2])
    return [r for r in rows if r['set_id'] in cal], [r for r in rows if r['set_id'] not in cal]


def set_weighted_cov(rows, ok):
    agg = collections.defaultdict(list)
    for r, o in zip(rows, ok):
        agg[r['set_id']].append(o)
    return float(np.mean([np.mean(v) for v in agg.values()])), len(agg)


def analyse(rows_by_seed, R=200):
    out = {}
    rng = random.Random(0)
    allrows = [r for rs in rows_by_seed.values() for r in rs]
    for cls in CLASSES2:
        rows = [r for r in rows_by_seed[1] if r['cls'] == cls]
        res = collections.defaultdict(list)
        for _ in range(R):
            cal, test = split_by_set(rows, rng)
            # one score per distinct set in calibration (dedupe: take a random task per set to keep exchangeability at set level)
            bys = collections.defaultdict(list)
            for r in cal:
                bys[r['set_id']].append(r)
            calr = [rng.choice(v) for v in bys.values()]
            for arm in ('query', 'nbhd'):
                Kh = conf_quantile([r[f'r_{arm}'] for r in calr], ALPHA)
                ok = [r[f'r_{arm}'] <= Kh for r in test]
                cov, nset = set_weighted_cov(test, ok)
                res[f'{arm}_K'].append(Kh)
                res[f'{arm}_cov'].append(cov)
                if math.isfinite(Kh):
                    res[f'{arm}_tok'].append(float(np.mean([r[f'tok_{arm}'][min(int(Kh), len(r[f"tok_{arm}"])) - 1] for r in test])))
            # CRC on FNR (recall loss) for query arm, B=1: smallest K with (n/(n+1)) Rhat(K) + 1/(n+1) <= alpha
            n = len(calr)
            Kc = math.inf
            for K in range(1, NMAX + 1):
                Rhat = np.mean([1 - r['rec_query'][min(K, len(r['rec_query'])) - 1] if r['rec_query'] else 1.0 for r in calr])
                if (n / (n + 1)) * Rhat + 1 / (n + 1) <= ALPHA:
                    Kc = K; break
            if math.isfinite(Kc):
                res['crc_K'].append(Kc)
                res['crc_meanrecall'].append(float(np.mean([r['rec_query'][min(Kc, len(r['rec_query'])) - 1] if r['rec_query'] else 0.0 for r in test])))
                res['crc_allitems'].append(set_weighted_cov(test, [(r['rec_query'][min(Kc, len(r['rec_query'])) - 1] if r['rec_query'] else 0.0) == 1.0 for r in test])[0])
            else:
                res['crc_inf'].append(1)
            # adaptive gap threshold (query arm, items only): tau = conformal quantile of gap_worst
            tau = conf_quantile([r['gap_worst'] for r in calr], ALPHA)
            ok = [r['gap_worst'] <= tau for r in test]
            res['adapt_cov'].append(set_weighted_cov(test, ok)[0])
            if math.isfinite(tau):
                sizes = [int(np.searchsorted(r['gap_sorted'], tau, side='right')) for r in test]
                res['adapt_size_mean'].append(float(np.mean(sizes)))
                res['adapt_size_p90'].append(float(np.percentile(sizes, 90)))
                res['adapt_size_max'].append(float(np.max(sizes)))
        summ = {}
        for k, v in res.items():
            v = [x for x in v if (not isinstance(x, float) or math.isfinite(x)) and x != math.inf]
            if not v:
                summ[k] = None; continue
            arr = np.array(v, dtype=float)
            summ[k] = dict(mean=round(float(arr.mean()), 4), p05=round(float(np.percentile(arr, 5)), 4),
                           p95=round(float(np.percentile(arr, 95)), 4), n=len(arr))
        summ['n_sets_total'] = len({r['set_id'] for r in rows})
        summ['inf_rate_query'] = round(float(np.mean([not math.isfinite(r['r_query']) for r in rows])), 3)
        summ['inf_rate_nbhd'] = round(float(np.mean([not math.isfinite(r['r_nbhd']) for r in rows])), 3)
        # cross-seed: calibrate on all of seed 1 (one task per set), test on seeds 2 and 3
        bys = collections.defaultdict(list)
        for r in rows:
            bys[r['set_id']].append(r)
        calr = [v[0] for v in bys.values()]
        for arm in ('query', 'nbhd'):
            Kh = conf_quantile([r[f'r_{arm}'] for r in calr], ALPHA)
            for sd in (2, 3):
                if sd not in rows_by_seed:
                    continue
                test = [r for r in rows_by_seed[sd] if r['cls'] == cls]
                ok = [r[f'r_{arm}'] <= Kh for r in test]
                summ[f'xseed_{arm}_K'] = Kh if math.isfinite(Kh) else 'inf'
                summ[f'xseed_{arm}_cov_s{sd}'] = round(set_weighted_cov(test, ok)[0], 4)
        out[cls] = summ
    return out


if __name__ == '__main__':
    seeds = [int(x) for x in sys.argv[1:]] or [1]
    rows_by_seed = {}
    for sd in seeds:
        rows_by_seed[sd] = per_seed(sd)
        import pickle
        with open(os.path.join(OUT, f'rows_s{sd}.pkl'), 'wb') as f:
            pickle.dump(rows_by_seed[sd], f)
    res = analyse(rows_by_seed)
    with open(os.path.join(OUT, 'summary.json'), 'w') as f:
        json.dump(res, f, indent=1, default=str)
    for cls, s in res.items():
        print('##', cls, json.dumps(s, default=str))
