"""H11-lite: does a visual embedding (SigLIP2-base, single vector) add anything over text twins for TEXT-BEARING
images (whiteboards, menu boards, receipts, report pages)? Pixels for photos of scenes (defects, family events,
rooms) would be meaningless here because the generator has no real images, so they are excluded.

Each OCR-bearing media item (targets and distractors) is rendered to a 448x448 PNG: the OCR text drawn on a
board/paper background with mild random rotation, font size and noise. Retrieval is restricted to the media items
the requester can see (within-media search) so the comparison isolates the media representation.
Arms: text twin full (caption+OCR+origin), text twin without OCR (caption+origin: "no OCR pipeline"),
SigLIP2 image only, and RRF fusions.
"""
from __future__ import annotations

import os
import random
import time

import numpy as np

from .common import ROOT
from .retrieval import item_text, rrf, topn

IMG_DIR = os.path.join(ROOT, "cache_v02", "h11_images")


def render(it, path, rng):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    m = it["media"]
    txt = m.get("ocr") or ""
    kind = it["type"]
    bg = (245, 245, 240) if kind == "page" else rng.choice([(250, 250, 250), (35, 45, 40)])
    fg = (20, 20, 20) if sum(bg) > 300 else (235, 235, 230)
    W = 448
    img = Image.new("RGB", (W, W), bg)
    d = ImageDraw.Draw(img)
    size = rng.randint(22, 30)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        font = ImageFont.load_default(size=size)
    lines = []
    for part in [p.strip() for p in txt.replace("  ", "|").split("|") if p.strip()]:
        words, cur = part.split(), ""
        for w_ in words:
            if d.textlength(cur + " " + w_, font=font) > W - 50:
                lines.append(cur.strip()); cur = w_
            else:
                cur += " " + w_
        lines.append(cur.strip())
    y = rng.randint(20, 60)
    for ln in lines[:12]:
        d.text((rng.randint(18, 40), y), ln, fill=fg, font=font)
        y += size + rng.randint(6, 14)
    img = img.rotate(rng.uniform(-4, 4), fillcolor=bg).filter(ImageFilter.GaussianBlur(rng.uniform(0, 0.8)))
    arr = np.array(img).astype(np.int16) + np.random.default_rng(rng.randint(0, 10**6)).integers(-12, 12, (W, W, 3))
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(path)


def run(ctx, s_text_full, s_text_noocr_fn=None):
    """ctx: Ctx for one seed. Returns rows per arm and timing."""
    import torch
    from PIL import Image
    from transformers import AutoModel, AutoProcessor
    from .ctx2 import ids_of, row
    from .experiments2 import tag
    w, b = ctx.w, ctx.b
    media = [i for i, it in enumerate(b.ix.items) if it.get("media") and (it["media"].get("ocr") or "").strip()]
    tasks = [t for t in ctx.tasks if t["cls"] == "multimodal" and all((w.by_id[r].get("media", {}).get("ocr") or "").strip() for r in t["required"])]
    os.makedirs(IMG_DIR, exist_ok=True)
    rng = random.Random(ctx.seed)
    paths = []
    for i in media:
        it = b.ix.items[i]
        p = os.path.join(IMG_DIR, f"s{ctx.seed}_{it['id']}.png")
        if not os.path.exists(p):
            render(it, p, rng)
        paths.append(p)
    hf = "google/siglip2-base-patch16-224"
    model = AutoModel.from_pretrained(hf, dtype=torch.float32).eval()
    proc = AutoProcessor.from_pretrained(hf)
    t0 = time.time()
    V = []
    with torch.inference_mode():
        for k in range(0, len(paths), 16):
            ims = [Image.open(p).convert("RGB") for p in paths[k:k + 16]]
            x = proc(images=ims, return_tensors="pt")
            v = model.get_image_features(**x)
            v = getattr(v, "pooler_output", v)
            V.append(torch.nn.functional.normalize(v, dim=-1).numpy())
    V = np.concatenate(V)
    img_secs = time.time() - t0
    t0 = time.time()
    with torch.inference_mode():
        x = proc(text=[t["query"] for t in tasks], padding="max_length", max_length=64, truncation=True, return_tensors="pt")
        q = model.get_text_features(**x)
        q = getattr(q, "pooler_output", q)
        Q = torch.nn.functional.normalize(q, dim=-1).numpy()
    txt_secs = time.time() - t0
    # text twins restricted to the media set
    mpos = np.array(media)
    noocr_txt = []
    for i in media:
        it = dict(b.ix.items[i]); md = dict(it["media"])
        it["text"] = md.get("caption", "") + " " + (md.get("transcript") or "")
        noocr_txt.append(item_text(it, True))
    E_noocr = ctx.emb[s_text_full.em.name if s_text_full.em else "bge-small"].docs(noocr_txt, f"s{ctx.seed}/h11_noocr") if s_text_full.em else None
    E_full = ctx.E[(s_text_full.em.name, "base")][mpos]
    names = ("text twin, hybrid (system first stage)", "text twin, dense (caption+OCR+origin)", "text twin without OCR, dense (caption+origin)",
             "SigLIP2 image only", "RRF(text twin without OCR, SigLIP2 image)", "RRF(text twin dense, SigLIP2 image)")
    out = {k: [] for k in names}
    for t, qv in zip(tasks, Q):
        acc = b.access(t["requester"])[mpos]
        hyb = s_text_full.fused(t["query"], t["requester"], b.access(t["requester"]))[mpos]
        dq = s_text_full.em.queries([t["query"]])[0]
        r_hyb = topn(hyb, acc & np.isfinite(hyb), 50)
        r_full = topn(E_full @ dq, acc, 50)
        r_noocr = topn(E_noocr @ dq, acc, 50)
        r_img = topn(V @ qv, acc, 50)
        lists = dict(zip(names, (r_hyb, r_full, r_noocr, r_img, topn(rrf([r_noocr, r_img], len(mpos)), acc, 50), topn(rrf([r_full, r_img], len(mpos)), acc, 50))))
        for k, rl in lists.items():
            out[k].append(row(t, [b.ids[mpos[j]] for j in rl[:10]]))
    for k in out:
        tag(out[k], seed=ctx.seed, arm=k)
    return out, dict(n_media=len(media), n_tasks=len(tasks), img_per_s=len(paths) / img_secs, txt_secs=txt_secs)
