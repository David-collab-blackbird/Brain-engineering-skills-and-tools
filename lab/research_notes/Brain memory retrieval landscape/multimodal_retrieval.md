# Multimodal Retrieval for a Self-Hosted Memory/RAG "Brain" (state of the art, late 2026)

Scope: images, visual documents (PDFs, scans, slides), video, audio. Retrieval must be precise to the segment or page. Target is ≥90% Context Recall@k per query class at 10k–100k items. Research date: 2026-10-23. "Vendor" means a claim from the model's own maker. "Independent" means a third party. Leaderboard numbers change often, so each one carries its capture date where known.

---

## 1. Visual document retrieval (PDFs, scans, slides): models, ViDoRe scores, page-as-image vs parse-to-text, storage/compression

### Takeaway
Page-as-image multi-vector retrievers built on Qwen3-VL/Qwen2.5-VL now lead ViDoRe V3, the hardest and most realistic benchmark (26k pages, human-verified queries). The best is nemotron-colembed-vl-8b-v2 at 63.4–63.5 nDCG@10. Even so, the absolute numbers sit far below 90%. Two things move the score more than picking a model: a text pipeline with a strong reranker, and hybrid visual+text fusion. On V3, Jina-v4 text retrieval plus zerank-2 reached 63.6, above the best visual retriever on its own. Hybrid also beat either modality alone. The strongest open models with a commercial-safe licence are the Apache-2.0 ColQwen3.5-4.5B-v3 (61.5 on V3) and ColNomic-7B (Apache-2.0). Nemotron-colembed is CC-BY-NC, so non-commercial only. Jina-v4 uses a Qwen Research licence. Raw multi-vector storage is large, but pooling and binarisation cut it 27–32x with small measured losses.

### Cited Findings

**ViDoRe V3 benchmark design and headline results (Jan 2026, benchmark authors; independent of most models evaluated)**
- V3 contains 10 corpora (7 English, 3 French), about 26,000 pages and 3,099 human-verified queries, each in 6 languages. 8 corpora are public and 2 are private. Domains include finance, CS, energy, pharma, HR, industrial maintenance, telecom, nuclear and physics. There are 7 query types (open-ended, extractive, numerical, multi-hop, compare-contrast, boolean, enumerative) and about 12,000 hours of human annotation — [ViDoRe V3 paper, arXiv 2601.08620](https://arxiv.org/pdf/2601.08620)
- Best visual retrievers by macro nDCG@10 (Table 1): ColEmbed-3B-v2 59.8, Jina-v4 (visual) 57.6, ColNomic-7B 57.4, ColEmbed-3B 57.3, ColQwen2.5 51.9, ColPali 43.1 — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)
- Best textual retrievers ran over Markdown extracted by NeMo Retriever: Qwen3-8B 51.0, Jina-v4 (textual) 50.4, BGE-M3 41.3, BM25S 20.3. "Chunking and image descriptions did not improve results" — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)
- Rerankers: Jina-v4 textual + zerank-2 went from 50.4 to 63.6 (+13.2). Jina-v4 visual + jina-reranker-m0 went from 57.6 to 57.8 (+0.2) and hurt 4 datasets. **The text pipeline with a strong text reranker beat the best visual-only retriever** — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)
- Hybrid (F1@10 with Jina-v4): visual 27.8, textual 25.0, hybrid 30.2. Hybrid took the top 5 from each modality and deduplicated, about 7.35 pages on average. In end-to-end QA on hard queries, hybrid scored 54.7% vs 52.1% best text and 54.5% best visual. The image oracle reached 64.7% — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)
- Difficulty factors: performance fell from 76.4 nDCG with one relevant page to 39.0 with 20+ relevant pages. Mixed-content pages scored lowest (45.1) and text-only pages highest (59.3). Open-ended and multi-hop queries were the hardest. Keyword and instruction formats scored below question format. Cross-lingual retrieval was 2–3 points lower — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)
- Sub-page grounding (bounding boxes) is weak. Human inter-annotator F1 was 0.602. Qwen3-VL-30B-A3B scored F1 0.089 (0.311 on the high-agreement subset) and Gemini 3 Pro 0.065. 26–27% of human-annotated pages got no model annotation at all — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)

**ViDoRe V3 leaderboard snapshot (captured 2026-04-20; reproduced on a model card, so cross-check the live leaderboard)**
- nDCG@10 mean: nemotron-colembed-vl-8b-v2 63.42 (8.7B, 4096-d per token); tomoro-colqwen3-embed-8b 61.59 (8B, 320-d); nemotron-colembed-vl-4b-v2 61.54; colqwen3.5-4.5B-v3 61.46 (4.6B, 320-d head); tomoro-colqwen3-embed-4b 60.20; llama-nemotron-colembed-vl-3b-v2 59.79; jina-embeddings-v4 57.52 (3.9B) — [colqwen3.5-4.5B-v3 model card](https://huggingface.co/athrael-soju/colqwen3.5-4.5B-v3)
- ViDoRe V1+V2 average nDCG@5: nemotron-colembed-vl-8b-v2 84.8, nemotron-4b-v2 83.9, colqwen3.5-4.5B-v3 83.7, tomoro-colqwen3-8b 83.5. colqwen3.5 per-set scores show V1 near saturation (SynAI 100.0, SynHealth 98.9, InfoVQA 93.6) while V2 sets stay hard (ESG 58.0, Econ 59.9, BioMed 65.3) — [colqwen3.5-4.5B-v3](https://huggingface.co/athrael-soju/colqwen3.5-4.5B-v3)
- colqwen3.5-4.5B-v3 licence: Apache-2.0 — [model card](https://huggingface.co/athrael-soju/colqwen3.5-4.5B-v3)

**Individual models (vendor model cards)**
- nemotron-colembed-vl-8b-v2: licence **CC-BY-NC-4.0, "non-commercial/research use only"**. Built on Qwen3-VL-8B-Instruct, about 8.8B params, released 2026-01-26. Scores: ViDoRe V3 63.54, V1 92.65, V2 65.16. Each page uses 256 tokens per tile, up to 9 tiles (about 2,304 vectors) at 4096-d. Listed hardware is A100 40/80GB or H100 80GB with flash-attn — [NVIDIA HF card](https://huggingface.co/nvidia/nemotron-colembed-vl-8b-v2). A rough calculation from the card's specs (not stated on the card): a fully tiled page at BF16 is about 18 MB uncompressed, which is impractical at 100k pages without compression.
- jina-embeddings-v4: 3.8B params, **Qwen Research License (commercial use needs a separate licence)**. Gives a single 2048-d vector (Matryoshka down to 128) or 128-d multi-vectors. Vendor ViDoRe (V1) average: 84.11 single-vector vs 90.17 multi-vector, against 83.90 for ColPali. JinaVDR 72.19 — [Jina model page](https://jina.ai/en-US/models/jina-embeddings-v4/)
- ColNomic Embed Multimodal 7B: Apache-2.0. Vendor ViDoRe-V2 nDCG@5 table: ColNomic-7B 62.7, ColNomic-3B 61.2, T-Systems ColQwen2.5-3B 59.9, Nomic Embed Multimodal 7B (single-vector) 59.7, GME-Qwen2-7B 59.0, vdr-2b-multi-v1 58.4, **voyage-multimodal-3 55.0** — [Nomic HF card](https://huggingface.co/nomic-ai/colnomic-embed-multimodal-7b)
- Qwen3-VL-Embedding-8B (single-vector, Apache-2.0) scores 83.3 on MMEB-V2 VisDoc. GME-7B scores 79.3 and VLM2Vec-V2 69.2 — [Qwen HF card](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B)

**Page-as-image vs OCR/parse-to-text (conflicting evidence)**
- VisRAG (ICLR 2025) claims a "20–40% end-to-end performance gain over traditional text-based RAG" when pages are embedded and consumed as images — [VisRAG abstract, arXiv 2410.10594](https://arxiv.org/abs/2410.10594v2) (author claim; the abstract gives no retrieval numbers)
- Contradicting result, "Lost in OCR Translation?" (2025). On 4,196 DOE documents across four degradation levels, OCR with Llama-3.2-90B plus a Qwen text embedder reached MRR 0.485 and Recall@5 0.636. ColQwen2 reached MRR 0.247 and Recall@5 0.355, and Nougat OCR 0.286/0.377. Llama-OCR led at every degradation level, including severe (MRR 0.452 vs 0.210). On the ViDoRe DocVQA split, which ColQwen2 was fine-tuned on, ColQwen2 won (nDCG@5 0.603 vs 0.337). The authors attribute that gap to fine-tuning rather than OCR quality — [arXiv 2505.05666](https://arxiv.org/pdf/2505.05666)
- Same paper on cost: the VLM pipeline used 1.38 GB per 1,000 documents vs 9.5 GB for OCR, and OCR preprocessing took about 6 s per document. The VLM pipeline "generalized poorly to unseen data" — [arXiv 2505.05666](https://arxiv.org/pdf/2505.05666)
- ViDoRe V3 (above) supports both sides. Visual beats text at the first stage (59.8 vs 51.0), text + reranker beats visual (63.6), and hybrid beats both — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)

**Parsers / OCR quality (OmniDocBench; independent aggregator, versions not always stated)**
- OmniDocBench composite = ((1 − TextEditDist)×100 + TableTEDS + FormulaCDM)/3. Scores: GLM-OCR 94.62 (verified), PaddleOCR-VL 92.86, PaddleOCR-VL-0.9B 92.56, MinerU 2.5 90.67 (verified), Qwen3-VL-235B 89.15, dots.ocr-3B 88.41, Gemini 2.5 Pro 88.03, Mistral OCR 3 79.75. **Marker and Docling are not listed** — [CodeSOTA OmniDocBench](https://codesota.com/benchmark/omnidocbench)

**Storage and compression of multi-vector page embeddings**
- Vespa, ColPali (1,030 patch vectors × 128-d per page): binary is about 16 KB per page vs about 527 KB at float32, a 32x saving. On DocVQA, nDCG@5 was 52.4 float, 49.5 binary-Hamming MaxSim, and 51.6 binary retrieval with float rerank — [Vespa blog](https://blog.vespa.ai/scaling-colpali-to-billions/)
- Qdrant, ColPali: mean-pooling grid rows cut vectors per page from 1,030 to 38 (about 27x). Two-stage retrieval (pooled top-200, then full-resolution rerank to top-20) ran about 13x faster. NDCG@20 was 0.952 and Recall@20 0.917, measured as overlap with full ColPali on 20k+ pages and 1,000 queries. Max-pooling failed (Recall@20 0.656) — [Qdrant blog](https://qdrant.tech/blog/colpali-qdrant-optimization/)
- Answer.AI token pooling (hierarchical clustering, ColBERT text on BEIR; not ColPali): pool factor 2 cut vectors 50% and kept 100.6% of performance, factor 3 cut 66% and kept 99%, factor 4 cut 75% and kept 97% — [Answer.AI](https://answer.ai/posts/colbert-pooling.html). The colpali-engine docs describe this as applicable to ColPali, but I did not verify ColPali-specific numbers.
- MUVERA (Weaviate ≥1.31, tested on LoTTE text ColBERTv2 with about 119k docs): about 12 GB fell to under 1 GB with SQ, and import time went from about 20 minutes to 3–6 minutes. Recall drops, and recovering 90%+ needs HNSW ef ≈ 2048, which costs QPS. **Not tested with ColPali/ColQwen** — [Weaviate blog](https://weaviate.io/blog/muvera)

### Inferences
- At 10k–100k pages, the evidence points to a **two-index hybrid**. One index holds visual multi-vectors (row-pooled or binarised first stage, full-precision MaxSim rerank). The other holds parsed-text chunks with page IDs (MinerU 2.5 / PaddleOCR-VL-class parsers). Fuse them, then cross-encoder-rerank the text side. This is the only configuration in ViDoRe V3 that beat both single modalities.
- ViDoRe V3 top scores are about 60–64 nDCG@10. Reaching ≥90% Recall@k on a realistic corpus will need a large k (e.g., 20–50 candidates into a reranker) and more pages per query. Single-relevant-page queries already score 76 nDCG, while multi-page and aggregation queries collapse to about 39.
- Licence-safe self-hostable default: colqwen3.5-4.5B-v3 or tomoro-colqwen3 (check the tomoro licence) or ColNomic-7B, all Apache-2.0. Nemotron colembed is the quality ceiling but non-commercial.
- The DocDeg result suggests that for degraded scans, a strong VLM-OCR (90B-class or a dedicated OCR VLM) feeding text retrieval may beat image embeddings that were not fine-tuned on similar data. This is a key test case for the builder's own eval set.

### Gaps
- No primary-source numbers found for ColSmol, DSE, or Cohere Embed v4 on ViDoRe V2/V3. voyage-multimodal-3 appears only in Nomic's vendor V2 table (55.0); I found no V3 score for voyage-multimodal-3.5.
- No head-to-head retrieval evaluation of Docling, Marker or Unstructured vs page-image retrievers was found. ViDoRe V3 used NeMo Retriever extraction.
- MUVERA and token pooling are not measured on ColQwen-class visual embeddings in the sources found.
- Tomoro-colqwen3 licence was not verified.

---

## 2. Image retrieval: CLIP/SigLIP 2 vs MLLM-based embedders vs caption-then-embed; MMEB scores

### Takeaway
MLLM-based embedders now dominate the MMEB-V2 universal benchmark. Qwen3-VL-Embedding-8B is Apache-2.0 and scores 77.9 overall and 80.1 on images. GME-7B scores 59.1 and VLM2Vec-V2 59.2. SigLIP 2 remains the best cheap dual encoder for plain caption-style photo search: So400m reaches about 56% R@1 on COCO text→image and about 85–86% on Flickr text→image. It is weak on video and long-form clip retrieval, and CLIP-style spaces suffer a modality gap when text and images are mixed in one index.

### Cited Findings
- MMEB-V2 (vendor table on the Qwen card), overall / image / video / visdoc: Qwen3-VL-Embedding-8B 77.9/80.1/66.1/83.3; Qwen3-VL-Embedding-2B 73.4/75.0/61.1/80.2; Seed-1.6-embedding (closed) 76.9/78.0/67.7/82.2; IFM-TTE-8B 74.1; RzenEmbed-8B 72.9; Ops-MM-embedding-v1 68.9; VLM2Vec-V2-2B 59.2/64.9/34.6/69.2; GME-7B 59.1/56.0/38.4/79.3; GME-2B 55.3; VLM2Vec 47.7 — [Qwen3-VL-Embedding-8B card](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B)
- Qwen3-VL-Embedding specs: Apache-2.0, 2B and 8B sizes, up to 4096-d with MRL (64–4096), 32K context. Accepts text, images, screenshots, video and mixed inputs, 30+ languages. Instructions add 1–5%. Requires transformers ≥4.57, flash_attention_2 and vLLM support. A companion Qwen3-VL-Reranker exists. Paper Jan 2026 — [Qwen card](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B); [Alibaba Cloud blog](https://www.alibabacloud.com/blog/qwen3-vl-embedding-and-qwen3-vl-reranker-for-the-next-generation-of-multimodal-retrieval_602796)
- SigLIP 2 zero-shot R@1 (Google paper, Feb 2025), COCO T→I / Flickr T→I: B/16-224 52.1/80.7; L/16-384 55.3/85.0; So400m/14-384 55.8/85.7; So400m/16-512 56.0/85.5; g/16-384 56.1/86.0. Baselines: CLIP B/16 33.1/62.1; original SigLIP So400m/14-384 52.0/80.5. NaFlex variants handle native aspect ratio (So400m NaFlex at 576 tokens: COCO 55.9) — [SigLIP 2, arXiv 2502.14786](https://arxiv.org/pdf/2502.14786)
- Modality gap: CLIP image and text embeddings "form distinct clusters," which causes intra-modal ranking bias and failed fusion in mixed-modality search. The GR-CLIP post-hoc calibration gives up to +26% nDCG@10 over CLIP on MixBench and +4% over VLM generative embedders, at 75x less compute (NeurIPS 2025 abstract) — [Closing the Modality Gap for Mixed Modality Search](https://neurips.cc/virtual/2025/133248)
- Caption-then-embed: ViDoRe V3 found that adding image descriptions to text chunks "did not improve results" for document pages — [ViDoRe V3](https://arxiv.org/pdf/2601.08620). Ragie (vendor engineering blog) found VLM descriptions embedded as text "matched or beat" Vertex native multimodal embeddings for video at 6x lower cost, though without published numbers — [Ragie](https://www.ragie.ai/blog/how-we-built-multimodal-rag-for-audio-and-video)

### Inferences
- For a personal or enterprise photo store with text queries ("the photo where…"), Qwen3-VL-Embedding (2B for throughput, 8B for quality) in one space with text gives the best published universal scores under a permissive licence. Keep SigLIP 2 So400m as a cheap second retriever for fusion, or as a fallback on CPU or small GPUs.
- Adding VLM captions plus OCR text for each image to a BM25/text index is cheap insurance for named entities, text-in-image and dates. The evidence on its marginal value is mixed, so it needs an ablation on the builder's eval set.

### Gaps
- No independent (non-vendor) MMEB-V2 reproduction found. The Qwen table is self-reported.
- No 2025–26 controlled study found comparing caption-then-embed with native image embeddings for personal-photo retrieval at 10k+ scale.
- SigLIP 2 licence was not confirmed from the fetched page (the big_vision repo is believed to be Apache-2.0, but this is unverified here).

---

## 3. Video retrieval: segmentation, keyframes, dense captions, ASR alignment, video embedders, moment-retrieval benchmarks, granularity

### Takeaway
Segment-level video search at "find the clip where…" precision is best served by **shot/scene segmentation into roughly 15–20 s clips, each indexed several ways**: a VLM dense caption, the time-aligned ASR transcript, and a clip-level video embedding. Evidence: Ragie found 15 s best among 15/30/60 s. LoVR clips average 17.9 s. Clip-level retrieval is far easier than whole-video retrieval for MLLM embedders (GME 53.5 vs 19.9 R@1). In small independent tests, open frame-averaging models (SigLIP 2, InternVideo2) fall well behind hosted video embedders. Hosted references are Marengo 3.0 and Gemini Embedding 2, with vendor-claimed leads. Among open weights, Qwen3-VL-Embedding-8B scores 66.1 on MMEB-V2 video, close to closed Seed-1.6 at 67.7.

### Cited Findings
- **LoVR benchmark** (May 2025): 467 videos longer than 15 minutes, 40,804 clips (average 17.9 s), segmented with PySceneDetect ContentDetector τ=34, clip captions from Qwen2.5-VL-7B with VLM and human repair — [LoVR, arXiv 2505.13928](https://arxiv.org/pdf/2505.13928)
- LoVR text→clip R@1/R@10: VideoCLIP-XL-v2 55.34/84.95, GME-Qwen2-VL 53.53/82.72, VideoCLIP-XL 47.33/80.81, LanguageBind-Video 40.30/74.26, MetaCLIP-H 25.26/55.09, CLIP 18.78/46.31, SigLIP2-base 8.35/25.28. Text→full-video R@1: LanguageBind 42.61, GME 19.91. Varying sampled frames from 10 to 30 had "marginal and inconsistent" effects — [LoVR](https://arxiv.org/pdf/2505.13928)
- Independent but conflicted small benchmark (Mixpeek founder; 20 Pexels videos ≤10 s, 60 queries), nDCG@10: Gemini Embedding 2 0.769, Marengo 2.7 0.760, Mixedbread Wholembed v3 0.757, X-CLIP-B 0.470, SigLIP 2 So400m (8-frame average) 0.325, InternVideo2-6B 0.302. Averaging frame embeddings performed poorly, and temporal modelling helped. Marengo was scored on only 34 of 60 queries — [Mixpeek benchmark](https://blog.mixpeek.com/video-embedding-benchmark-2026/)
- Marengo 3.0 (TwelveLabs vendor, Nov 2025): 512-d embeddings over video, audio, image, text and composed inputs. MSR-VTT text→video 72.5 (Marengo 2.7 71.7, Amazon Nova 69.6, Vertex 59.5); MSVD 78.2; VATEX 86.4. Many benchmarks are in-house `tl-*` sets with an undisclosed competitor protocol. The Search API adds transcription and lexical hybrid on top of the embedding — [TwelveLabs blog](https://twelvelabs.io/blog/marengo-3-0)
- Gemini Embedding 2 (Google, ~Mar 2026, hosted): one space for text, image, video (≤120 s per input), audio (native, no ASR), and PDFs (≤6 pages). 3072-d with MRL. Vendor claims text/video 68.8 vs Amazon Nova 2 60.3 and voyage-multimodal-3.5 55.2 — [The Decoder](https://the-decoder.com/google-unifies-text-image-video-and-audio-in-a-single-vector-space-with-gemini-embedding-2/)
- Production design (Ragie, vendor blog): video split into **15 s non-overlapping chunks** containing the transcript (faster-whisper large-v3-turbo, word timestamps) plus a Gemini visual description for the same time span, embedded as text with start/end timestamps. 15/30/60 s were tested and "15-second chunks provided the best balance." Native Vertex multimodal embeddings were 6x more expensive, 2x slower and captured no speech. Video-level summaries came from the full video, because concatenated chunk captions were disjointed — [Ragie](https://www.ragie.ai/blog/how-we-built-multimodal-rag-for-audio-and-video)
- Moment retrieval (QVHighlights test, specialised DETR-style grounding models): Moment-DETR R1@0.5 52.89 / mAP 30.73; QD-DETR 62.40/39.86; TR-DETR 64.66/42.62; UVCOM 63.55/43.18; BAM-DETR 62.71/45.36; AMR (Oct 2025) 68.22 / R1@0.7 51.88 / mAP 48.43 — [AMR, arXiv 2510.19622](https://arxiv.org/pdf/2510.19622)
- Long-video RAG: existing VideoRAG benchmarks can often be answered without the video. CARVE (2026) picks modality and granularity per chunk with parallel retrievers and chunk-adaptive reranking, and reports beating 8 VideoRAG baselines (abstract only, no numbers) — [arXiv 2606.13141 abstract](https://papers.cool/arxiv/2606.13141)

### Inferences
- Recommended self-hosted pipeline: PySceneDetect shot detection, merged or split to about 10–20 s windows aligned to transcript sentence boundaries. For each clip, store (a) a Qwen3-VL-Embedding video embedding, (b) a Qwen2.5/3-VL dense caption including OCR'd on-screen text, (c) ASR words with timestamps, and (d) keyframe SigLIP 2 embeddings. Fuse with RRF, then rerank with Qwen3-VL-Reranker. Optionally refine timestamps inside the top clip with a moment-retrieval model.
- QVHighlights SOTA is about 68% R1@0.5. Exact sub-clip boundaries are a much harder problem than picking the right ~15 s clip, so the ≥90% target should be defined at clip level, with a tolerance window.

### Gaps
- No primary results fetched for VideoPrism or InternVideo2 on MSR-VTT. The only InternVideo2 data point is the small Mixpeek test.
- No independent reproduction of Marengo 3.0 or Gemini Embedding 2 video claims.
- No study found that directly compares fixed-window, shot-based and semantic segmentation for retrieval recall beyond Ragie's unpublished 15/30/60 s test.

---

## 4. Audio: ASR with word timestamps and diarisation; audio embeddings for non-speech

### Takeaway
Open ASR has moved past Whisper on accuracy. Average WER on the Open ASR Leaderboard: Cohere Transcribe (2B, Apache-2.0 per one secondary source) 5.42%, Canary-Qwen-2.5B 5.63%, Qwen3-ASR-1.7B 5.76%, Parakeet-TDT-0.6B-v2 about 6.05%, Whisper-large-v3 7.44%, v3-turbo 7.83%. The Parakeet/Canary families are also 10x+ faster (RTFx in the thousands). Whisper (MIT, 99+ languages) remains the multilingual default with mature word-timestamp tooling. pyannote community-1 is the open diarisation default. Its DER is meaningfully worse than the paid precision-2 (e.g., CALLHOME 26.7 vs 16.6). For non-speech sound, MLLM-based audio embedders now beat CLAP substantially.

### Cited Findings
- Open ASR Leaderboard 8-set average WER (automated secondary report, unverified): Cohere Transcribe 5.42 (Mar 2026, "2B, Apache-2.0"), Canary-Qwen-2.5B 5.63, Qwen3-ASR-1.7B 5.76, ElevenLabs Scribe v2 5.83 (closed), Phi-4-Multimodal 6.02, Parakeet-TDT-0.6B-v2 6.05, Canary-1B 6.50, Voxtral Small 24B 6.62, Parakeet-TDT-1.1B 7.02, Whisper-large-v3 7.44, Whisper-large-v3-turbo 7.83 — [Keenable ASR leaders report](https://select.keenable.ai/r/speech-recognition-accuracy-leaders-2022-2026/JbURQjlVooLQ6J10NkbRVw)
- Licences and hardware (Northflank, Jan 2026; the article has internal inconsistencies): Canary-Qwen-2.5B CC-BY-4.0, English only, RTFx 418; Granite Speech 3.3 8B Apache-2.0, 5.85% WER; Whisper-large-v3 MIT, 99+ languages, about 10 GB VRAM; v3-turbo 809M params, about 6 GB; Parakeet-TDT-1.1B CC-BY-4.0, English, about 4 GB VRAM, RTFx >2,000 — [Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)
- Throughput (Open ASR RTFx, verified rows): Parakeet TDT 0.6B v2 3,386; Parakeet TDT 0.6B v3 3,333 (2025); Parakeet-TDT-1.1B 2,391; Canary-1B-Flash 1,046; Canary-1B-v2 749; Granite 4.0 1B Speech 280; Voxtral Mini 3B 110 — [CodeSOTA Open ASR](https://www.codesota.com/benchmark/open-asr-leaderboard)
- faster-whisper large-v3-turbo in float16 is used in production with word-level timestamps, at a claimed 4x the speed of vanilla Whisper — [Ragie](https://www.ragie.ai/blog/how-we-built-multimodal-rag-for-audio-and-video)
- pyannote DER (%) for legacy 3.1 → community-1 → precision-2 (paid): AMI-IHM 18.8→17.0→12.9; CALLHOME 28.5→26.7→16.6; DIHARD3 21.4→20.2→14.7; VoxConverse 11.2→11.2→8.5; Ego4D 51.2→46.8→39.0. community-1 runs at about 31–37 s per hour of audio on an H100. Use requires accepting HF gated conditions (updated 2025-09) — [pyannote README](https://cdn.jsdelivr.net/gh/pyannote/pyannote-audio@main/README.md)
- Non-speech audio: AuroLA (Qwen2.5-Omni-7B based, 2026) text→audio R@1 is AudioCaps 46.0 vs CLAP 32.7 and CLAP-fusion 36.2, and Clotho 25.3 vs 15.6/17.2. Weights are "to be publicly released," licence not stated — [arXiv 2602.18010](https://arxiv.org/pdf/2602.18010)
- Marengo 3.0 (vendor) Clotho R@1/5/10 average is 44.2% and GTZAN mAP 75.5%, meaning hosted unified models also cover sound events — [TwelveLabs](https://twelvelabs.io/blog/marengo-3-0)

### Inferences
- Default stack: Parakeet-TDT-0.6B-v3 or Canary for English/European throughput (NeMo timestamps), with Whisper-large-v3(-turbo) via faster-whisper/WhisperX as the multilingual fallback. Run pyannote community-1 for speakers. Chunk transcripts on sentence and speaker turns of about 30–60 s, carrying word timestamps so hits can jump to the exact second.
- For non-speech sounds ("the clip with the dog barking"), CLAP is a weak baseline (about 33% R@1 on AudioCaps). MLLM audio embedders or captioning audio with an audio-LLM into text are likely better, but self-hostable open weights need checking.

### Gaps
- Could not fetch the Parakeet-TDT-0.6B-v3 HF card (URL access was blocked). Its licence, languages and timestamp details remain unverified here.
- The Cohere Transcribe licence and open-weight status come only from a secondary automated report, so they need primary verification.
- No primary source fetched for LAION-CLAP licence or for word-timestamp accuracy comparisons (Whisper vs Parakeet alignment error).

---

## 5. Unified embedding space vs per-modality indexes fused at query time

### Takeaway
Direct evidence is thin, but it consistently favours **fusion of several representations** over relying on one space. Hybrid visual+text beat either modality on ViDoRe V3. CLIP-style unified spaces have a measured modality gap that biases rankings in mixed corpora. Vendors with the strongest unified models (TwelveLabs) still add transcription and lexical search on top to reach their best scores. Newer MLLM embedders (Qwen3-VL-Embedding, Gemini Embedding 2) shrink the gap enough to make one space viable as a first stage, but no controlled study found shows a unified space beating per-modality fusion.

### Cited Findings
- On ViDoRe V3, hybrid of visual top-5 + text top-5 gave F1@10 30.2 vs 27.8 visual and 25.0 text, and the best non-oracle QA on hard queries — [ViDoRe V3](https://arxiv.org/pdf/2601.08620)
- CLIP's modality gap causes "intra-modal ranking bias and inter-modal fusion failure" in mixed-modality search. Post-hoc gap removal gives up to +26% nDCG@10 — [NeurIPS 2025, MixBench/GR-CLIP](https://neurips.cc/virtual/2025/133248)
- TwelveLabs notes its Search API adds transcription and hybrid lexical search on top of Marengo embeddings to get higher benchmark scores — [TwelveLabs](https://twelvelabs.io/blog/marengo-3-0)
- Ragie found text descriptions in a single text index matched or beat native multimodal embeddings for video, at lower cost — [Ragie](https://www.ragie.ai/blog/how-we-built-multimodal-rag-for-audio-and-video)
- Unified MLLM embedders such as Qwen3-VL-Embedding are trained across text, image, visdoc and video in one space and score high on all MMEB-V2 categories (80.1 image, 66.1 video, 83.3 visdoc) — [Qwen card](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B)

### Inferences
- Architecture recommendation: a unified MLLM space (Qwen3-VL-Embedding) for broad first-stage recall across all items, plus modality-specialist indexes (ColQwen multi-vector for pages, BM25/text over parsed text, captions and transcripts, SigLIP 2 for images). Merge with RRF or score-normalised fusion, then rerank with Qwen3-VL-Reranker and a text cross-encoder. Every unit carries `(file_id, page | t_start–t_end | bbox)` so recall is measured at segment level.
- The builder should benchmark both on its own 10k–100k mixed corpus, since no public benchmark tests mixed-corpus segment-level recall at this scale.

### Gaps
- No controlled published study found of a unified space vs per-modality fusion for text queries over a mixed images+docs+video+audio corpus at 10k–100k items.
- MixBench full numbers and model list were not available from the abstract page.

---

## 6. Open-weight / self-hostable status, licences, hardware

### Takeaway
Every modality has a strong open-weight, self-hostable option with a permissive licence. A single 24–48 GB GPU can serve the 2–4B models. The 8B embedders and nemotron need A100/H100-class cards. The top visual doc retriever (nemotron) and jina-v4 carry non-commercial or research licences.

### Cited Findings
| Component | Model | Licence | Size / hardware | Source |
|---|---|---|---|---|
| Visual doc (multi-vector) | nemotron-colembed-vl-8b-v2 | CC-BY-NC-4.0 (non-commercial) | 8.8B; A100 40/80GB or H100 | [NVIDIA](https://huggingface.co/nvidia/nemotron-colembed-vl-8b-v2) |
| Visual doc (multi-vector) | colqwen3.5-4.5B-v3 | Apache-2.0 | 4.6B; ~8.7 GB memory per leaderboard | [card](https://huggingface.co/athrael-soju/colqwen3.5-4.5B-v3) |
| Visual doc | ColNomic Embed Multimodal 7B/3B | Apache-2.0 | 7B / 3B | [Nomic](https://huggingface.co/nomic-ai/colnomic-embed-multimodal-7b) |
| Visual doc / universal | jina-embeddings-v4 | Qwen Research License (commercial licence required) | 3.8B; ~7.5 GB | [Jina](https://jina.ai/en-US/models/jina-embeddings-v4/) |
| Universal (text/image/video/doc) | Qwen3-VL-Embedding-2B/8B + Reranker | Apache-2.0 | 2B/8B; flash-attn, vLLM | [Qwen](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B) |
| Image dual encoder | SigLIP 2 (B to g) | not confirmed here | 86M to ~1B | [paper](https://arxiv.org/pdf/2502.14786) |
| ASR | Whisper large-v3 / turbo | MIT | ~10 GB / ~6 GB VRAM | [Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks) |
| ASR | Canary-Qwen-2.5B; Parakeet-TDT-1.1B | CC-BY-4.0 | ~8 GB / ~4 GB | [Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks) |
| ASR | Granite Speech 3.3 8B | Apache-2.0 | ~9B | [Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks) |
| Diarisation | pyannote community-1 | gated HF conditions | ~31–37 s per audio-hour on H100 | [pyannote](https://cdn.jsdelivr.net/gh/pyannote/pyannote-audio@main/README.md) |
| Hosted references only | Marengo 3.0, Gemini Embedding 2, voyage-multimodal-3/3.5, Cohere Embed v4 | proprietary API | — | [TwelveLabs](https://twelvelabs.io/blog/marengo-3-0), [Decoder](https://the-decoder.com/google-unifies-text-image-video-and-audio-in-a-single-vector-space-with-gemini-embedding-2/) |

### Inferences
- A storage budget calculation from the cited per-page figures: at 100k pages, binarised ColPali-style storage (~16 KB per page) is about 1.6 GB. Row-pooled to 38 vectors at float16 it would be about 1 GB. Nemotron-style 4096-d × 2,304 vectors uncompressed would be on the order of terabytes. Projection-head dimension (128–320) and pooling therefore matter more than model choice for feasibility.

### Gaps
- Exact VRAM for Qwen3-VL-Embedding inference and throughput (pages/s, video-min/s) not published on the card. The builder must measure.
- Parakeet v3 and Cohere Transcribe licences not verified from primary sources (the Parakeet card fetch was blocked).
