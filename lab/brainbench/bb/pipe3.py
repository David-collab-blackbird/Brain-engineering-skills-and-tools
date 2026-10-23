"""BrainBench v0.3 pipeline core: world loading, access (grants at a day), index (BM25 variants + bge-small),
structured stores built from a write gate's output, context assembly arms, and scoring at item AND token budgets.

Scoring (DA2 / DA1-1):
  * CR_vital@B  = all VITAL required items in the context (cards/timelines credit the items whose facts they state CORRECTLY)
  * CR_all@B    = all required items (vital + helpful)
  * budgets B: K = 10 / 50 / 100 items and T = 1k / 4k / 8k tokens (bge tokenizer over the text shown to the reader)
  * rates are means over DISTINCT required sets (cluster-aware), as in batch 2.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import defaultdict

import numpy as np

from .brain import is_temporal_query
from .common import NOW_DAY, ROOT, read_jsonl, tokenize
from .experiments2 import HAND_SLOTS2, MEDIA_RE

DATA3 = os.path.join(ROOT, "data_v03")
CACHE3 = os.path.join(ROOT, "cache_v03")
KS = (10, 50, 100)
TS = (1000, 4000, 8000)
CLASSES_V2 = ["decision_support", "option_analysis", "current_state", "temporal_change", "goal_tracking", "preference_recommendation", "cross_domain", "multimodal"]
CLASSES_NEW = ["aggregation", "standing_brief", "obligation_status", "rule_precedence", "match_reconcile", "release_safe", "carry_forward"]
TARGET5 = ["decision_support", "option_analysis", "goal_tracking", "preference_recommendation", "cross_domain"]
RULE_Q = re.compile(r"\b(can (we|i|the|a|tomas|kira|ben|coaches|staff)|allowed|who (approves|can)|need[s]? (both|sign)|is .{0,30} allowed|do we need)\b", re.I)


# ============================================================================ tokens
_TOK = None


def ntok(texts):
    global _TOK
    if _TOK is None:
        os.environ.setdefault("HF_HOME", "/home/claude/models/hf"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from transformers import AutoTokenizer
        _TOK = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
    return [len(x) for x in _TOK(list(texts), add_special_tokens=False)["input_ids"]]


# ============================================================================ embeddings (own cache; batch-2 caches untouched)
class Emb:
    def __init__(self, name="bge-small"):
        assert name == "bge-small"
        self.path = os.path.join(CACHE3, "emb_bge-small.npz")
        self.store = None
        self.model = None
        self.dirty = 0

    def _load(self):
        if self.store is None:
            self.store = {}
            if os.path.exists(self.path):
                z = np.load(self.path)
                self.store = dict(zip(z["keys"].tolist(), z["vecs"]))

    def _m(self):
        if self.model is None:
            os.environ.setdefault("HF_HOME", "/home/claude/models/hf"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")
            self.model.max_seq_length = 512
        return self.model

    def save(self):
        """Merge with whatever another process saved meanwhile, then atomic replace (pid-unique temp file; fcntl lock)."""
        if self.dirty:
            import fcntl
            os.makedirs(CACHE3, exist_ok=True)
            with open(self.path + ".lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                if os.path.exists(self.path):
                    try:
                        z = np.load(self.path)
                        for k, v in zip(z["keys"].tolist(), z["vecs"]):
                            self.store.setdefault(k, v)
                    except Exception:
                        pass
                tmp = f"{self.path}.{os.getpid()}.tmp.npz"
                np.savez(tmp, keys=np.array(list(self.store.keys())), vecs=np.stack(list(self.store.values())))
                os.replace(tmp, self.path)
            self.dirty = 0

    def enc(self, texts, prefix=""):
        self._load()
        keys = [hashlib.md5((prefix + "\x00" + t).encode()).hexdigest() for t in texts]
        todo = sorted({k: t for k, t in zip(keys, texts) if k not in self.store}.items())
        for i in range(0, len(todo), 2048):
            ch = todo[i:i + 2048]
            v = self._m().encode([prefix + t for _, t in ch], batch_size=32, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
            for (k, _), vv in zip(ch, v):
                self.store[k] = vv
            self.dirty += len(ch)
            if self.dirty >= 1000:
                self.save()
        return np.stack([self.store[k] for k in keys]) if keys else np.zeros((0, 384), np.float32)

    def prefetch_queries(self, qs):
        self.queries(list(dict.fromkeys(qs)))
        self.save()

    def docs(self, texts):
        return self.enc(texts, "")

    def queries(self, qs):
        return self.enc(qs, "Represent this sentence for searching relevant passages: ")


EMB = Emb()


# ============================================================================ world
class World3:
    def __init__(self, seed):
        d = os.path.join(DATA3, f"s{seed}")
        self.seed = seed
        self.items = read_jsonl(os.path.join(d, "items.jsonl"))
        self.by_id = {it["id"]: it for it in self.items}
        self.entities = {e["id"]: e for e in read_jsonl(os.path.join(d, "entities.jsonl"))}
        self.keys_conn = {k["key"]: k for k in read_jsonl(os.path.join(d, "keys_connector.jsonl"))}
        self.tasks = read_jsonl(os.path.join(d, "tasks.jsonl"))
        with open(os.path.join(d, "meta.json")) as f:
            self.meta = json.load(f)
        self.grants = self.meta["grants"]
        # gold (scoring and oracle arms only)
        self.gold = {g["id"]: g for g in read_jsonl(os.path.join(d, "gold", "items_gold.jsonl"))}
        self.keys_all = {k["key"]: k for k in read_jsonl(os.path.join(d, "gold", "keys_all.jsonl"))}
        with open(os.path.join(d, "gold", "vocab.json")) as f:
            self.vocab = json.load(f)
        with open(os.path.join(d, "gold", "specials.json")) as f:
            self.specials = json.load(f)
        self._vis = {}

    def visible(self, who, day=NOW_DAY, grants=None):
        key = (who, day, id(grants))
        if key not in self._vis:
            gs = grants if grants is not None else self.grants
            self._vis[key] = frozenset(g["space"] for g in gs if g["identity"] == who and g["valid_from"] <= day and (g["valid_to"] is None or day < g["valid_to"]))
        return self._vis[key]


def ctx_text(it):
    """Text shown to the reader and indexed: title, text, thread/sender context, media origin."""
    parts = []
    if it.get("title"):
        parts.append(it["title"] + ":")
    parts.append(it["text"])
    ctx = []
    if it.get("thread"):
        ctx.append(f"[thread: {it['thread']}]")
    if it.get("sender"):
        ctx.append(f"[from: {it['sender']}]")
    m = it.get("media")
    if m:
        o = m.get("origin") or {}
        ctx.append(" ".join(x for x in (o.get("folder", "").replace("/", " "), o.get("album", ""), o.get("chat", ""),
                                         ("shared by " + o["shared_by"]) if o.get("shared_by") else "", o.get("adjacent_text", "")) if x))
    return " ".join(parts + ctx)


# ============================================================================ write-gate output -> structured store
NUM_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?\s*(?:%|k|m|kg|am|pm)?", re.I)


def norm_val(s):
    s = (s or "").lower().replace("—", "-").replace("–", "-")
    s = re.sub(r"[^a-z0-9.%$]+", " ", s)
    return " ".join(s.split())


class Gate:
    """A write gate's output for one seed: per item, entity links and typed records.
    links: iid -> [eid]; records: iid -> [dict(t, e(list), a, v, s)]; aliases: [(phrase, eid, iid)]."""

    def __init__(self, name, links, records, aliases=(), entries=None):
        self.name = name
        self.links = links
        self.records = records
        self.aliases = list(aliases)
        self.entries = entries or {}

    @staticmethod
    def gold(w: World3):
        links, recs, al = {}, {}, []
        for iid, g in w.gold.items():
            links[iid] = list(g["entities"])
            rr = []
            for r in g["records"]:
                if r["t"] == "fact" and r.get("a"):
                    rr.append(dict(t="fact", e=r["e"], a=r["a"], v=r["v"], s=w.by_id[iid]["text"]))
                elif r["t"] == "fact":
                    rr.append(dict(t="fact", e=r.get("e", []), a=None, v=None, s=w.by_id[iid]["text"]))
                elif r["t"] == "alias":
                    al.append((r["v"], r["e"][0], iid))
                elif r["t"] == "mention":
                    rr.append(dict(t="fact", e=r["e"], a=r["a"], v=None, s=None))
                else:
                    rr.append(dict(t=r["t"], e=r.get("e", []), s=w.by_id[iid]["text"]))
            recs[iid] = rr
        # connector facts: links/records come from the connector, not the gate
        return Gate("gold", links, recs, al)


def build_store(w: World3, gate: Gate | None, attr_entity_ok=True):
    """Keyed store = connector keys + gate-extracted facts (keyed by entity.attr, versions by item day).
    Returns dict(keys: key -> [version dicts sorted by day], item_facts: iid -> [key], correct: iid -> set(keys correct vs gold))."""
    keys = {}
    for k in w.keys_conn.values():
        vs = []
        for vid in k["versions"]:
            c = w.by_id[vid]["connector"]
            vs.append(dict(key=k["key"], src=vid, day=c["valid_from"], v=c["value_str"], label=k["label"], entity=k["entity"], attr=k["attr"], conn=True, ok=True))
        keys[k["key"]] = dict(entity=k["entity"], attr=k["attr"], label=k["label"], space=k["space"], versions=vs, conn=True)
    item_facts = defaultdict(list)
    n_fact = n_ok = 0
    if gate is not None:
        gold_key = {}
        for kk in w.keys_all.values():
            gold_key[(kk["entity"], kk["attr"])] = kk
        labels = {}
        for kk in w.keys_all.values():
            labels[(w.entities[kk["entity"]]["kind"], kk["attr"])] = kk["label"]
        for iid, recs in gate.records.items():
            it = w.by_id.get(iid)
            if it is None or it.get("connector"):
                continue
            for r in recs:
                if r.get("t") != "fact" or not r.get("a") or not r.get("e") or r.get("v") in (None, "", "not stated"):
                    continue
                eid = r["e"][0] if isinstance(r["e"], list) else r["e"]
                if eid not in w.entities:
                    continue
                attr = r["a"]
                key = f"{eid}.{attr}"
                # match to a gold key on (entity, attr): the gate does not see key names
                gk = gold_key.get((eid, attr))
                if gk is not None:
                    key = gk["key"]
                    if not gk["extract_only"]:
                        continue          # connector owns this key (source precedence: connector > extraction)
                gi = w.gold[iid]
                ok = any(gr["t"] == "fact" and gr.get("key") == key and norm_val(gr["v"]) in norm_val(r["v"]) for gr in gi["records"]) or \
                     any(gr["t"] == "fact" and gr.get("key") == key and norm_val(r["v"]) and norm_val(r["v"]) in norm_val(gr["v"]) and len(norm_val(r["v"])) >= 0.6 * len(norm_val(gr["v"])) for gr in gi["records"])
                n_fact += 1; n_ok += ok
                lab = labels.get((w.entities[eid]["kind"], attr), attr.replace("_", " "))
                d = keys.setdefault(key, dict(entity=eid, attr=attr, label=lab, space=it["space"], versions=[], conn=False))
                d["versions"].append(dict(key=key, src=iid, day=it["created_day"], v=r["v"], label=lab, entity=eid, attr=attr, conn=False, ok=ok))
                item_facts[iid].append(key)
        for d in keys.values():
            if not d["conn"]:
                d["versions"].sort(key=lambda x: (x["day"], x["src"]))
    return dict(keys=keys, item_facts=item_facts, n_fact=n_fact, n_ok=n_ok)


def head_srcs(store):
    """item id -> the item id that holds the current head of the same key (for mention forwarding)."""
    out = {}
    for k, d in store["keys"].items():
        if d["conn"] or not d["versions"]:
            continue
        h = d["versions"][-1]["src"]
        for v in d["versions"][:-1]:
            out.setdefault(v["src"], set()).add(h)
    return out


# ============================================================================ index
class Index:
    """Docs = items (+ derived docs). BM25 statistics policy: visible | global | frozen | partition."""

    def __init__(self, docs, texts, ext_idf=None):
        from sklearn.feature_extraction.text import CountVectorizer
        self.docs = docs
        self.ids = [d["id"] for d in docs]
        self.pos = {i: n for n, i in enumerate(self.ids)}
        self.N = len(docs)
        self.texts = texts
        self.cv = CountVectorizer(analyzer=tokenize)
        tf = self.cv.fit_transform(texts).astype(np.float32)
        self.tf_csc = tf.tocsc()
        self.dl = np.asarray(tf.sum(axis=1)).ravel()
        self.vocab = self.cv.vocabulary_
        self.inv = {v: k for k, v in self.vocab.items()}
        self.space = np.array([d["space"] for d in docs])
        self.ext = ext_idf

    def bm25(self, q, mask, stats="visible", k1=1.2, b=0.75):
        terms = [self.vocab[t] for t in tokenize(q) if t in self.vocab]
        s = np.zeros(self.N)
        if not terms:
            return s
        if stats == "partition":
            for sp in np.unique(self.space[mask]):
                pm = self.space == sp
                s[pm] = self._core(terms, pm, k1, b, "visible")[pm]
            return s
        sm = np.ones(self.N, bool) if stats == "global" else mask
        return self._core(terms, sm, k1, b, stats)

    def _core(self, terms, sm, k1, b, stats):
        if stats == "frozen":
            n, avgdl = self.ext["N"], self.ext["avgdl"]
        else:
            n = sm.sum(); avgdl = self.dl[sm].mean() if n else 1.0
        s = np.zeros(self.N)
        for t in terms:
            col = self.tf_csc.getcol(t)
            rows, tfv = col.indices, col.data
            if stats == "frozen":
                df = self.ext["df"].get(self.inv[t], 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            else:
                df = sm[rows].sum()
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            s[rows] += idf * tfv * (k1 + 1) / (tfv + k1 * (1 - b + b * self.dl[rows] / avgdl))
        return s


def ext_idf_wikitext():
    """Frozen external statistics fitted once on WikiText-2 (train), never on brain data."""
    p = os.path.join(CACHE3, "ext_idf_wikitext2.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    import pyarrow.parquet as pq
    col = pq.read_table(os.path.join(CACHE3, "ext", "wikitext2_train.parquet")).column("text").to_pylist()
    # documents = paragraphs (non-empty lines that are not headings)
    df, dls = defaultdict(int), []
    for x in col:
        x = x.strip()
        if not x or x.startswith("="):
            continue
        toks = tokenize(x)
        dls.append(len(toks))
        for t in set(toks):
            df[t] += 1
    out = dict(N=len(dls), avgdl=float(np.mean(dls)), df=dict(df))
    with open(p, "w") as f:
        json.dump(out, f)
    return out


def minmax(s, m):
    v = s[m]
    if v.size == 0:
        return np.zeros_like(s)
    lo, hi = v.min(), v.max()
    if hi - lo < 1e-12:
        return np.zeros_like(s)
    return np.where(m, (s - lo) / (hi - lo), 0.0)


def topn(scores, mask, n):
    """Stable top-n: ties broken by doc position among VISIBLE docs only (noninterference-safe; see DA3 X1b)."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    s = scores[idx]
    order = np.lexsort((idx, -s))      # primary: -score, secondary: position (visible docs only)
    sel = idx[order[:n]]
    return [int(i) for i in sel if np.isfinite(scores[i])]


# ============================================================================ the brain under test (one arm configuration)
class Brain3:
    """One seed + one gate output + one index-text variant. Holds the docs (items + cards + timelines), index and embeddings."""

    def __init__(self, w: World3, gate: Gate | None, entries=None, alias_table=None, timelines=False, stub_cards=False, stats="visible",
                 ext=None, alpha=0.2, card_mode="read", embed=True, extra_items=(), drop_items=()):
        self.w, self.gate, self.alpha, self.stats = w, gate, alpha, stats
        self.store = build_store(w, gate)
        self.heads = head_srcs(self.store)
        self.links = gate.links if gate else {}
        self.records = gate.records if gate else {}
        drop = set(drop_items)
        items = [it for it in w.items if it["id"] not in drop] + list(extra_items)
        self.items_by_id = {it["id"]: it for it in items}
        docs, texts, disp = [], [], []
        for it in items:
            t = ctx_text(it)
            docs.append(dict(id=it["id"], space=it["space"], kind="item", type=it["type"], day=it["created_day"],
                             super=bool(it.get("connector") and it["connector"]["superseded_by"])))
            disp.append(t)
            e = (entries or {}).get(it["id"])
            texts.append(t + (" " + e if e else ""))
        # cards (code-compiled from the keyed store) per (entity, space); stub = values-free index text, values at read time
        self.cards, self.card_cover, self.card_of = {}, {}, defaultdict(list)
        per = defaultdict(list)
        for k, d in self.store["keys"].items():
            if d["versions"]:
                per[(d["entity"], d["space"])].append(k)
        for (eid, sp), ks in sorted(per.items()):
            e = w.entities[eid]
            heads = [self.store["keys"][k]["versions"][-1] for k in ks]
            body = "; ".join(f"{h['label']}: {h['v']}" for h in heads)
            labels = "; ".join(sorted({h["label"] for h in heads}))
            cid = f"card:{eid}:{sp}"
            full = f"Entity card — {e['name']} ({', '.join(e['aliases'][1:])}). Current facts: {body}."
            stub = f"Entity card — {e['name']} ({', '.join(e['aliases'][1:])}). Facts held: {labels}."
            docs.append(dict(id=cid, space=sp, kind="card", type="card", day=NOW_DAY, super=False, entity=eid))
            disp.append(full)
            texts.append(stub if stub_cards else full)
            self.card_cover[cid] = {h["src"] for h in heads if h["ok"]}
            self.card_of[eid].append(cid)
        # key timelines (DA1-6): one doc per key listing every version; covers all correct versions
        self.tl_of = {}
        self.tl_for_src = {}
        if timelines:
            for k, d in self.store["keys"].items():
                if len(d["versions"]) < 2:
                    continue
                e = w.entities[d["entity"]]
                body = "; ".join(f"{v['v']} (from {v['day']})" for v in d["versions"][-12:])
                tid = f"tl:{k}"
                docs.append(dict(id=tid, space=d["space"], kind="timeline", type="timeline", day=NOW_DAY, super=False, entity=d["entity"]))
                txt = f"Timeline — {e['name']} · {d['label']}: {body}."
                disp.append(txt); texts.append(f"Timeline — {e['name']} ({', '.join(e['aliases'][1:3])}) · {d['label']} history, changes over time")
                self.card_cover[tid] = {v["src"] for v in d["versions"][-12:] if v["ok"]}
                self.tl_of[k] = tid
                for v in d["versions"]:
                    self.tl_for_src[v["src"]] = tid
        self.docs, self.disp = docs, disp
        self.ix = Index(docs, texts, ext)
        self.ntok = np.array(ntok(disp))
        self.E = EMB.docs(texts) if embed else None
        self.is_super = np.array([d["super"] for d in docs])
        self.kind = np.array([d["kind"] for d in docs])
        # query linker: registry aliases (+ alias table)
        self.alias_pats = []
        for e in w.entities.values():
            for a in e["aliases"]:
                if len(a) >= 3 and a.lower() not in ("me", "p", "training", "portfolio", "offset", "reading list", "my training", "my reading"):
                    self.alias_pats.append((a.lower(), e["id"]))
        for phrase, eid in (alias_table or []):
            self.alias_pats.append((phrase.lower(), eid))
        self.alias_pats.sort(key=lambda x: -len(x[0]))
        self.member_ent = {f"member_{e['member_id']}": e["id"] for e in w.entities.values() if e.get("member_id")}
        self.ent_items = defaultdict(list)
        for iid, es in self.links.items():
            if iid in self.ix.pos:
                for e in es:
                    self.ent_items[e].append(self.ix.pos[iid])
        self.typed = np.zeros(self.ix.N, bool)
        self.constraint = np.zeros(self.ix.N, bool)
        for iid, rr in self.records.items():
            if iid in self.ix.pos and any(r.get("t") in ("decision", "rule", "plan", "issue", "quote", "preference", "fact", "constraint", "offer") for r in rr):
                self.typed[self.ix.pos[iid]] = True
            if iid in self.ix.pos and any(r.get("t") in ("constraint", "rule") for r in rr):
                self.constraint[self.ix.pos[iid]] = True
        self._mask = {}
        self._q = {}

    # ---------------------------------------------------------------- access
    def mask(self, who, temporal=False, day=NOW_DAY, spaces=None):
        key = (who, temporal, day, spaces)
        if key not in self._mask:
            vis = spaces if spaces is not None else self.w.visible(who, day)
            m = np.array([d["space"] in vis for d in self.docs])
            if not temporal:
                m &= ~self.is_super
            self._mask[key] = m
        return self._mask[key]

    def scores(self, q, m):
        key = (q, m.tobytes().__hash__() if False else id(m))
        bm = self.ix.bm25(q, m, self.stats)
        if self.E is None:
            return np.where(m, bm, -np.inf)
        qv = EMB.queries([q])[0]
        dv = self.E @ qv
        s = self.alpha * minmax(bm, m) + (1 - self.alpha) * minmax(dv, m)
        return np.where(m, s, -np.inf)

    def link_query(self, q, who, vis):
        ql = q.lower()
        found = []
        for a, eid in self.alias_pats:
            if eid in found:
                continue
            if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", ql):
                e = self.w.entities.get(eid)
                if e and set(e["spaces"]) & vis:
                    found.append(eid)
        if who in self.member_ent and re.search(r"\b(i|my|me|i'm|i've)\b", ql):
            found.insert(0, self.member_ent[who])
        return found

    # ---------------------------------------------------------------- assembly
    def assemble(self, t, arm, maxk=100, maxt=8000, spaces=None):
        """Return ordered doc positions (context), up to max budgets. arm: dict(prefix=none|cards|cards+slots|router, nbhd=bool, typed_first=bool,
        C=3, fwd=bool, timeline=bool)."""
        q, who = t["query"], t["requester"]
        temporal = is_temporal_query(q)
        vis = spaces if spaces is not None else self.w.visible(who)
        m = self.mask(who, temporal, spaces=frozenset(vis) if spaces is not None else None)
        s = self.scores(q, m)
        ranked = topn(s, m & (self.kind == "item") if not arm.get("cards_in_search", True) else m, 400)
        pre = []
        mode = arm.get("prefix", "none")
        if mode == "router":
            mode = "none" if (temporal or MEDIA_RE.search(q)) else arm.get("router_else", "cards+slots")
        ents = self.link_query(q, who, vis) if mode != "none" or arm.get("nbhd") else []
        if mode in ("cards", "cards+slots"):
            for eid in ents:
                for cid in self.card_of.get(eid, []):
                    p = self.ix.pos[cid]
                    if m[p] and p not in pre and len(pre) < arm.get("C", 3):
                        pre.append(p)
            if mode == "cards+slots":
                cov = set().union(*[self.card_cover.get(self.ix.ids[p], set()) for p in pre]) if pre else set()
                for ent, attr in self.slot_keys(t):
                    k = self.key_for(ent, attr)
                    if not k:
                        continue
                    h = self.store["keys"][k]["versions"][-1]["src"]
                    if h in self.ix.pos and m[self.ix.pos[h]] and self.ix.pos[h] not in pre and h not in cov and len(pre) < 5:
                        pre.append(self.ix.pos[h])
        if temporal and arm.get("timeline"):
            # DA1 innovation 3: collapse versions per key in ranking — every version row hit is replaced by its key's timeline
            # (computed over the version chain), deduplicated; timeline docs can also be hit directly
            coll = []
            for p in ranked:
                tid = self.tl_for_src.get(self.ix.ids[p])
                if tid is not None and tid in self.ix.pos and m[self.ix.pos[tid]]:
                    p = self.ix.pos[tid]
                if p not in coll:
                    coll.append(p)
            ranked = coll
        if arm.get("rule_pin") and RULE_Q.search(q):
            # exploratory (PM13-style declared mapping): permission/approval questions get the space's constraint records pinned
            cons = [p for p in np.flatnonzero(m & self.constraint) if p not in pre]
            cons.sort(key=lambda p: (-s[p], p))
            pre += cons[: arm.get("rule_pin_n", 6)]
        out = list(dict.fromkeys(pre))
        seen = set(out)
        if arm.get("nbhd") and ents and not (arm.get("nbhd_router") and (temporal or MEDIA_RE.search(q))):
            cand = []
            for eid in ents:
                for p in self.ent_items.get(eid, []):
                    if m[p] and p not in seen:
                        cand.append(p)
            cand = list(dict.fromkeys(cand))
            if arm.get("typed_first"):
                cand.sort(key=lambda p: (-int(self.typed[p]), -s[p], p))
            else:
                cand.sort(key=lambda p: (-s[p], p))
            nb = cand[: arm.get("nbhd_cap", 10_000)]
            if arm.get("parents"):
                # exploratory: decisions, policies and plans often live on the PARENT entity (property -> portfolio,
                # project -> company, staff -> business); add the parents' evidence after the entity's own, ranked by query
                par = []
                for eid in ents:
                    for pe in self.parents_of(eid):
                        if pe in ents:
                            continue
                        for p in self.ent_items.get(pe, []):
                            if m[p] and p not in seen and p not in nb:
                                par.append(p)
                par = sorted(set(par), key=lambda p: (-int(self.typed[p]) if arm.get("typed_first") else 0, -s[p], p))
                nb = nb + par[: arm.get("parent_cap", 30)]
            # interleave: a few top search hits first so query-matching items are never crowded out
            lead = [p for p in ranked[: arm.get("search_lead", 0)] if p not in seen]
            for p in lead + nb:
                if p not in seen:
                    out.append(p); seen.add(p)
        fwd = arm.get("fwd", True)
        for p in ranked:
            if p in seen:
                continue
            out.append(p); seen.add(p)
            if fwd and not temporal:
                iid = self.ix.ids[p]
                for h in self.heads.get(iid, ()):
                    hp = self.ix.pos.get(h)
                    if hp is not None and m[hp] and hp not in seen:
                        out.append(hp); seen.add(hp)
            if len(out) >= maxk and self.ntok[out].sum() >= maxt:
                break
        return out

    def parents_of(self, eid):
        """Registry hierarchy by entity kind and space (configuration, not gold): property/holding -> portfolio; project/tender ->
        the building company; staff -> their business; supplier -> the businesses it serves; offset -> portfolio."""
        if not hasattr(self, "_par"):
            biz = {"company/ironbark": "b_gym", "company/stonefield": "b_con", "company/copperleaf": "b_cafe"}
            self._par = {}
            for e in self.w.entities.values():
                k, sp = e["kind"], set(e.get("spaces", []))
                ps = []
                if k in ("property", "holding"):
                    ps = ["fin_portfolio"]
                elif k in ("project", "tender"):
                    ps = ["b_con"]
                elif e["id"] == "fin_offset":
                    ps = ["fin_portfolio"]
                elif k in ("person", "supplier") and not e.get("member_id"):
                    ps = [b for s2, b in biz.items() if s2 in sp]
                self._par[e["id"]] = [x for x in ps if x in self.w.entities and x != e["id"]]
        return self._par.get(eid, [])

    def slot_keys(self, t):
        g = t.get("declared_scope")
        spec = HAND_SLOTS2.get(g)
        if not spec:
            return []
        out = []
        for k in spec["static"]:
            kk = self.w.keys_all.get(k)
            if kk:
                out.append((kk["entity"], kk["attr"]))
        return out

    def key_for(self, ent, attr):
        for k, d in self.store["keys"].items():
            if d["entity"] == ent and d["attr"] == attr and d["versions"]:
                return k
        return None

    # ---------------------------------------------------------------- scoring
    def score(self, t, ctx):
        vital, req = set(t["vital"]), set(t["required"])
        r = dict(id=t["id"], cls=t["cls"], set_id=t["set_id"], ref_form=t.get("ref_form"), requester=t["requester"], nvital=len(vital), nreq=len(req))
        got = set()
        cum = 0
        tok = self.ntok
        budgets = sorted([("K", k) for k in KS] + [("T", x) for x in TS], key=lambda x: x[1])
        cov_k = {}
        cov_t = {}
        cum_tok = np.cumsum(tok[ctx]) if ctx else np.array([])
        for n, p in enumerate(ctx):
            did = self.ix.ids[p]
            got.add(did)
            got |= self.card_cover.get(did, set())
            for k in KS:
                if n + 1 == k:
                    cov_k[k] = set(got)
            for T in TS:
                if cum_tok[n] <= T:
                    cov_t[T] = set(got)
        for k in KS:
            cov_k.setdefault(k, set(got))
        for T in TS:
            cov_t.setdefault(T, set() if not len(cum_tok) or cum_tok[0] > T else set(got))
        for k, c in cov_k.items():
            r[f"v@{k}"] = vital <= c
            r[f"a@{k}"] = req <= c
            r[f"rv@{k}"] = len(vital & c) / len(vital) if vital else 1.0
        for T, c in cov_t.items():
            r[f"v@T{T}"] = vital <= c
            r[f"a@T{T}"] = req <= c
        # rank (items) and tokens at which the LAST vital item enters (I15 nonconformity score)
        last_n, last_tok = None, None
        got2 = set()
        for n, p in enumerate(ctx):
            did = self.ix.ids[p]
            got2.add(did); got2 |= self.card_cover.get(did, set())
            if vital <= got2:
                last_n, last_tok = n + 1, int(cum_tok[n])
                break
        r["r_vital"] = last_n
        r["t_vital"] = last_tok
        if t.get("forbidden"):
            fb = set(t["forbidden"])
            for k in KS:
                r[f"forbid@{k}"] = bool(fb & set(self.ix.ids[p] for p in ctx[:k]))
        return r


# ============================================================================ aggregates over distinct sets
def per_set(rows, key):
    agg = defaultdict(list)
    for r in rows:
        if r.get(key) is None:
            continue
        agg[(r.get("seed", 0), r["set_id"])].append(float(r[key]))
    return {k: float(np.mean(v)) for k, v in agg.items()}


def wilson_frac(k, n, z=1.959964):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(max(p * (1 - p), 0) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - hw), min(1.0, c + hw)


def rate(rows, key):
    ps = per_set(rows, key)
    n = len(ps)
    if not n:
        return dict(p=float("nan"), lo=float("nan"), hi=float("nan"), n=0)
    p, lo, hi = wilson_frac(sum(ps.values()), n)
    return dict(p=p, lo=lo, hi=hi, n=n)


def sign_test(rows_a, rows_b, key):
    a, b = per_set(rows_a, key), per_set(rows_b, key)
    ks = sorted(set(a) & set(b))
    d = np.array([b[k] - a[k] for k in ks])
    wins, losses = int((d > 1e-9).sum()), int((d < -1e-9).sum())
    n = wins + losses
    if n == 0:
        p = 1.0
    else:
        kk = min(wins, losses)
        p = min(1.0, 2 * sum(math.comb(n, i) for i in range(kk + 1)) / 2 ** n)
    rng = np.random.default_rng(0)
    if len(d):
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
    else:
        lo = hi = float("nan")
    return dict(b_better=wins, a_better=losses, p=p, diff=100 * float(d.mean()) if len(d) else float("nan"), lo=100 * lo, hi=100 * hi, n=len(ks))
