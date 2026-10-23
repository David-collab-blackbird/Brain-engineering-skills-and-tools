# Local Models and GPU Hosting for a Self-Hosted Memory/Retrieval "Brain" (as of 23 October 2026)

Scope note: this covers which open-weight models to use for each brain pipeline, what hardware runs them and how fast, which serving stack to use, and what GPUs cost in Australia. I ran out of web searches partway through (the shared per-turn limit), so a few items are left as Gaps instead of guessed. Every number is labelled as one of: **[vendor]** (claimed by the model maker or seller), **[independent]** (measured by a third party), **[leaderboard]** (aggregator data, often self-reported), or **[estimate]** (my own arithmetic, with the working shown). Prices are in AUD where the source gives AUD. USD→AUD conversions use the 1.42 rate from the Micron21 articles.

---

## Q1. Best open-weight LLMs by size class: quality, licences, VRAM, tokens/s, and what changed in 2026

### Takeaway
For the write-time pipelines (extraction, scribe, change planning), the best default today is a dense model of about 27B parameters: **Qwen3.8-27B** (Apache 2.0, released 14 Aug 2026, multimodal, 262K context). Its fallbacks are Qwen3.6-27B and Gemma 4 31B, both Apache 2.0. It runs at roughly 65–110 tok/s for a single request and 1,200–1,350 tok/s aggregate at 32 concurrent requests on one 32–96 GB Blackwell card. The top open models are now 1–2.4T-parameter MoEs (MiMo-V2.6-Pro, GLM-5.3, Kimi K3, DeepSeek V4.x, Qwen3.8-2.4T). Those need a node of 8 datacentre GPUs and don't fit a family/SMB server. The useful "big local" tier is MoEs of about 120–320B (Qwen3.5-122B-A10B, Qwen3.8-Flash-Next, GLM-5.3-Flash, DeepSeek V4 Flash) on 2–4 cards of 96 GB.

### Cited Findings

**What changed in 2026 (timeline)**
- Qwen3.5 (Feb 2026, Apache 2.0) shipped open weights at 397B-A17B, 122B-A10B, 35B-A3B, 27B dense, 9B, 4B, 2B and 0.8B, with 254K context extensible to 1M. Alibaba reported that the 122B and 27B beat GPT-5-mini on most language and vision benchmarks, and that the 9B beat gpt-oss-120b on most language benchmarks other than reasoning and coding **[vendor]** — [DeepLearning.AI The Batch](https://www.deeplearning.ai/the-batch/alibabas-latest-flagship-models-are-open-weights-moe-performers-in-sizes-from-less-than-1b-parameters)
- Gemma 4 (2 Apr 2026) moved to an **Apache 2.0** licence, replacing Google's custom Gemma licence. Sizes: E2B and E4B (text, image, audio), 26B-A4B MoE (3.8B active) and 31B dense (text, image, up to 60 s of video), with 256K context on the larger models. Gemma 4 12B followed on 3 Jun 2026 — [Wikipedia: Gemma](https://en.wikipedia.org/wiki/Gemma_(language_model)); [DataNorth](https://datanorth.ai/news/google-releases-gemma-4-open-models)
- Gemma 4 31B vendor scores: MMLU-Pro 85.2, GPQA 84.3, LiveCodeBench v6 80.0, MMMU-Pro 76.9; it ranked third among open models on the Arena text leaderboard (~1452). All variants support function calling, structured JSON output and system instructions **[vendor]** — [DataNorth](https://datanorth.ai/news/google-releases-gemma-4-open-models)
- Qwen3.6-27B (21 Apr 2026) and Qwen3.6-35B-A3B (16 Apr 2026) are both Apache 2.0 with 262K context — [llm-stats](https://llm-stats.com/models/compare/qwen3.6-27b-vs-qwen3.6-35b-a3b). Qwen3.6-27B vendor table: MMLU-Pro 86.2, GPQA-D 87.8, MMMU 82.9, OCRBench 89.4, Video-MME (with subtitles) 87.7. On the same table Claude 4.5 Opus scores MMLU-Pro 89.5, GPQA 87.0, MMMU 80.7 and Video-MME 77.7 **[vendor]** — [HF Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B)
- Qwen3.6-35B-A3B architecture: 256 experts, 8 routed plus 1 shared active, a Gated DeltaNet/Gated Attention hybrid (3:1), and multi-token prediction (MTP). Vendor scores: MMLU-Pro 85.2, GPQA 86.0, TAU3-Bench 67.2 (Qwen3.5-27B 68.4, Gemma4-31B 67.5) **[vendor]** — [HF Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)
- DeepSeek V4 (MIT licence) comes as V4 Pro (1.6T total, 49B active) and V4 Flash (284B total, 13B active). Flash has 1M context and native FP4 (experts) + FP8 mixed weights, and runs on vLLM and SGLang. V4-Flash Max vendor scores: MMLU-Pro 86.2, GPQA-D 88.1, SWE-bench Verified 79.0 **[vendor]** — [HF DeepSeek-V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash); [BenchLM](https://benchlm.ai/best/open-source). Lambda says V4 Pro deploys on a single HGX B200 node and that cost to serve is ">10x lower" than V3.2 thanks to compressed sparse attention — [Lambda](https://lambda.ai/blog/deepseek-v4-the-most-expected-open-source-model). *Release-date conflict:* Artificial Analysis (30 Apr 2026) says V4 Pro launched the previous week; Lambda's post gives 22 May 2026, which is probably its own deployment date — [Artificial Analysis](https://artificialanalysis.ai/articles/recent-open-weights-model-launches)
- DeepSeek V4 Flash Vision Exp (305B, MIT licence) published open weights on 31 Aug 2026, about 168 GB — [RuntimeWire](https://runtimewire.com/article/deepseek-publishes-v4-flash-vision-open-weights)
- Qwen3.8 (Aug 2026): open weights for **Qwen3.8-27B** (14 Aug, Apache 2.0), **Qwen3.8-Flash-Next** (26 Aug, Qwen Community License 1.0) and **Qwen3.8-2.4T-A95B** (12 Aug, Qwen licence; providers above US$50M revenue need a commercial licence) — [Wikipedia: Qwen](https://en.wikipedia.org/wiki/Qwen)
- Qwen3.8-27B specs: 27B dense (28B with the vision encoder), 64 layers, 48 Gated DeltaNet plus 16 full-attention layers, 262K native context (1M with YaRN), image and video input. Vendor scores (Qwen3.6-27B in brackets): IFBench 79.5 (69.1), GPQA-D 89.2 (87.8), OSWorld-Verified 84.3 (63.9), OmniDocBench 1.5 91.1 (89.4) **[vendor]** — [OrcaRouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-benchmarks); [HF Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- Qwen3.8-27B thinks by default. Thinking can be turned off per request with `enable_thinking: False`, and `reasoning_effort` accepts xhigh (default), medium or low. Recommended non-thinking sampling: temperature 0.7, top_p 0.8, top_k 20, presence_penalty 1.5. Recommended servers: SGLang, vLLM, TokenSpeed — [HF Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- Independent arena results: Qwen3.8-27B ranks #9 overall on Code Arena WebDev (1595), the only model of its size in the top 10 — [OrcaRouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-benchmarks). Artificial Analysis Intelligence Index v4.3.2 scores: Qwen3.8-27B 33.70, 2.4T-A95B 39.89, hosted Qwen3.8-Max(0902) 45.42 **[leaderboard]** — [Codersera](https://codersera.com/blog/qwen-3-8-model-lineup-2026)
- Qwen3.8-Flash-Next is about 125B main MoE parameters (6B active, 512 experts) plus a 51B N-gram embedding table that "can be offloaded to system RAM" and a 4B MTP head. Vendor scores: IFBench 81.3, GPQA-D 91.7, SWE-bench Pro 62.5 **[vendor]**. Alibaba describes it as a preview of the Qwen4 architecture — [eesel](https://www.eesel.ai/blog/qwen38-flash-next); [DataNorth](https://datanorth.ai/news/alibaba-releases-qwen3-8-flash-next). Its licence adds conditions for "certain large products, model-as-a-service businesses and AI work assistants". **That last clause matters for a brain plus assistant and needs legal review** — [DataNorth](https://datanorth.ai/news/alibaba-releases-qwen3-8-flash-next)
- *Conflict on Qwen3.8-Flash-Next's Artificial Analysis score:* eesel reports 56 (#5 of 111), while a row-by-row audit of AA shows 39.8 — [eesel](https://www.eesel.ai/blog/qwen38-flash-next); [DEV audit](https://dev.to/ward_ed_6b5e6aa8ded94a987/best-open-weight-llm-in-october-2026-auditing-two-leaderboards-row-by-row-1b64). They probably refer to different index versions. Treat as unresolved.
- Late-Oct 2026 BenchLM open-weight top 10 (overall score): MiMo-V2.6-Pro 73.7 (1020B/42B, MIT), Qwen3.8 Max 69.7, Step 5 Preview 69.7 (600B/27B), Ling 3.1 Flash 68.1 (560B/25B, MIT), GLM-5.3 67.9 (753B/40B, GLM community licence), DeepSeek V4.1 Flash 1017 65.7 (552B/16B, MIT), MiMo-V2.6-Flash 64.6 (309B/15B, MIT), dots3-note 64.2 (280B/16B, Apache), DeepSeek V4 Pro 0813 63.2, Qwen3.8-Flash-Next 62.8. The best model under 130B is **Qwen3.8-27B at #15 (59.6)**. Gemma 4 26B-A4B ranks #44, Gemma 4 31B #57, gpt-oss-120b #61, Mistral Small 4 (119B/6.5B, Apache) #65 and Llama 4 Scout #90 **[leaderboard]** — [BenchLM open-source](https://benchlm.ai/best/open-source). (The catalogue lists "Kimi K2.5 120B dense", which looks like a catalogue error.)
- The audit warns that the top nine open models' ranges all overlap, so rank 1 is "not statistically resolved". Rank agreement between BenchLM and AA is only τ=0.61, and the two disagree about which models count as open (Kimi K3, Qwen3.8 Max) — [DEV audit](https://dev.to/ward_ed_6b5e6aa8ded94a987/best-open-weight-llm-in-october-2026-auditing-two-leaderboards-row-by-row-1b64)
- gpt-oss-120b: 117B total, 5.1B active, MXFP4 MoE weights, fits a single 80 GB GPU, Apache 2.0, native function calling and Structured Outputs, three reasoning-effort levels — [HF gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b)
- NVIDIA Nemotron 3.5 Super VL (120B-A12B) and Nemotron 3.5 Bolt (74B-A9B) are under OpenMDW-1.1, and Meta's "Muse Spark Open" (816B/42B) is under a Muse community licence **[leaderboard]** — [BenchLM open-source](https://benchlm.ai/best/open-source)
- Mistral Large 4 entered API preview on 6 Oct 2026, with weights announced for late October (not verified as released) — [Javadex](https://www.javadex.es/blog/mejores-modelos-ia-octubre-2026-ranking-comparativa-mensual)

**VRAM (weights only, before KV cache and activations)**

| Model | BF16 | FP8 | ~4-bit | Source / basis |
|---|---|---|---|---|
| Qwen3.8-27B | ~55.6 GB (51.05 GB measured in SGLang) | ~28 GB [estimate] | Q4_K_M ~18 GB; W4A16 AutoRound 19 GB; NVFP4 21.9 GB | [OrcaRouter](https://www.orcarouter.ai/blog/qwen-3-8-27b-benchmarks), [HF discussion](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/160), [Codersera](https://codersera.com/blog/qwen-3-8-model-lineup-2026), [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide), [ComputingForGeeks](https://computingforgeeks.com/tensorrt-llm-vs-vllm/) |
| Qwen3.6-35B-A3B | ~70 GB [estimate] | 35 GB (official FP8) | ~20 GB [estimate] | [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide) |
| Gemma 4 31B | ~62 GB [estimate: 30.7B × 2 bytes] | ~31 GB [estimate] | ~17–19 GB [estimate] | DataNorth says "40GB+" — [DataNorth](https://datanorth.ai/news/google-releases-gemma-4-open-models) |
| Gemma 4 26B-A4B | ~52 GB [estimate] | — | "~24 GB" | [DataNorth](https://datanorth.ai/news/google-releases-gemma-4-open-models) |
| gpt-oss-120b | n/a (MXFP4 native) | — | fits 80 GB GPU | [HF](https://huggingface.co/openai/gpt-oss-120b) |
| Qwen3.5-122B-A10B | ~244 GB [estimate] | ~122 GB [estimate] | ~65 GB [estimate] | ran at 4-bit on a 128 GB M5 Max — [Implicator](https://www.implicator.ai/apple-mac-studio-m5-ultra-prompt-processing/) |
| Qwen3.8-Flash-Next | HF repo ~360 GB | ~180 GB [estimate] | every 4-bit build ≥93.7 GB; 1-bit 72.5 GB; N-gram table belongs in system RAM | [DataNorth](https://datanorth.ai/news/alibaba-releases-qwen3-8-flash-next), [HF discussion](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/29) |
| DeepSeek V4 Flash (Vision Exp) | — | native FP4+FP8 ~168 GB | GGUF Q4/Q8 ~155–162 GB; lightest ~82–97 GB | [RuntimeWire](https://runtimewire.com/article/deepseek-publishes-v4-flash-vision-open-weights), [LocalClaw](https://localclaw.io/hardware/mac-studio-m3-ultra-512gb) |

**Measured throughput (27B class; the main write-gate workhorse)**

| Hardware / stack | Model / precision | 1 request | Concurrency results | Prefill / TTFT | Source |
|---|---|---|---|---|---|
| RTX PRO 6000 Server Ed., vLLM 0.27.1, FP8 KV, MTP-3 | Qwen3.8-27B W4A16 | 106 tok/s | 8 → 636 tok/s total; 32 → 1,342 tok/s total (45 per request) | ~5,070 tok/s at ~22–25K prompt; 99 s TTFT at 256K; cached 200K prompt TTFT 2.4 s | [ParalonCloud, 28 Sep 2026](https://paraloncloud.com/resources/rtx-pro-6000-vs-2x-rtx-4090-qwen3-8-27b) **[independent]** |
| Same test, 2× RTX 4090 (TP2) | same | 94 tok/s | 8 → 381; 32 → 435 | ~3× slower prefill | same |
| RTX 5090, vLLM 0.31.0 | Qwen3.8-27B NVFP4 | 65.6 tok/s (68.5 decode) | 8 → 440; 16 → 778; 32 → 1,195 (BF16 KV) | TTFT 177 ms on a 474-token prompt; cold start 718 s (FlashInfer JIT) | [ComputingForGeeks, 13 Oct 2026](https://computingforgeeks.com/tensorrt-llm-vs-vllm/) **[independent]** |
| RTX 5090, TensorRT-LLM 1.3.0rc29, FP8 KV | same | 70.6 tok/s | 32 → 1,361 (14% ahead of the best vLLM run) | TTFT 123 ms | same |
| RTX PRO 6000, SGLang, BF16 + EAGLE-3 | Qwen3.8-27B BF16 | 77–80 tok/s | not measured | weights 51 GB; total ~78 GB including KV | [HF discussion #160](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/160) **[independent, community]** |
| RTX PRO 6000, vLLM, no MTP | Qwen3.6-27B FP8 | 46.1 tok/s (1K) to 30.4 (256K) | peak 189 tok/s at 5 concurrent | prefill up to 9,854 tok/s (8K); TTFT 170 ms at 1K, 70 s at 256K | [Millstone AI, 27 May 2026](https://www.millstoneai.com/inference-benchmark/qwen3-6-27b-fp8-1x-rtx-pro-6000-blackwell) **[independent]** |
| RTX PRO 6000, vLLM 0.23/0.24, MTP-3 | Qwen3.6-27B FP8 vs NVFP4 | 84.7 vs 77.1 tok/s | 16 → 963 (FP8) vs 892 (NVFP4) | prefill ~7,000 vs ~5,700 tok/s | [HF nvidia/Qwen3.6-27B-NVFP4 #8](https://huggingface.co/nvidia/Qwen3.6-27B-NVFP4/discussions/8) **[independent, community]** |
| RTX PRO 6000, vLLM nightly, MTP-3 | 27B INT4 / 35B-A3B FP8 | 100 / 170 tok/s (flashinfer + FP8 KV) | two replicas reached 234 tok/s total at C=4 | — | [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide) **[independent, community]** |
| Radeon AI PRO R9700 32 GB, llama.cpp Vulkan | Qwen3.8-27B | 51.8 tok/s | — | — | [OrcaRouter citing AMD](https://www.orcarouter.ai/blog/qwen-3-8-27b-benchmarks) **[vendor]** |
| Ryzen AI Max+ 395 (Strix Halo) | Qwen3.8-27B | 24.5 tok/s | — | — | same **[vendor]** |

- MTP (multi-token-prediction speculative decoding) is the single biggest speed lever. Without it the 27B runs at 24 tok/s (eager mode) or 75 tok/s (CUDA graphs); with MTP n=3 and FP8 KV it reaches 100 tok/s (mean acceptance length 3.19). Speeds under 50 tok/s usually mean MTP isn't active — [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide)
- On a 96 GB PRO 6000, NVFP4 (W4A16) is **not** faster than FP8. FP8 decodes 8–12% faster and quality is effectively tied; NVFP4's benefit is memory. Note that NVFP4 never finished a simple function within a 16K-token thinking budget in one test — [HF #8](https://huggingface.co/nvidia/Qwen3.6-27B-NVFP4/discussions/8)

### Inferences
- **Default write-gate LLM:** Qwen3.8-27B in **non-thinking or low-effort mode** for extraction and the scribe, with medium effort for change planning. It is Apache 2.0, natively multimodal (so it can also serve as the VLM captioner), has a hybrid DeltaNet design that keeps KV small for long contexts, and supports MTP. Hold Qwen3.6-27B and Gemma 4 31B (both Apache 2.0) as A/B challengers on the brain's own golden set. Gemma 4 31B is the strongest non-Chinese option, which matters if provenance becomes a governance question.
- The 120–320B MoE class (Qwen3.5-122B-A10B Apache; GLM-5.3-Flash 320B/18B MIT; DeepSeek V4 Flash 284B/13B MIT; Qwen3.8-Flash-Next under a restricted licence) is the realistic "large local" tier for hard change-planning conflicts and a private assistant. It needs about 120–200 GB of VRAM at FP8/FP4, which means 2× RTX PRO 6000 or 2× H200 NVL.
- Frontier-scale open models (1T+) are not a sensible self-hosting target for this workload. Use the hosted versions only if their licences and data policies fit.

### Gaps
- No IFEval, BFCL or long-context (RULER/MRCR) numbers were published for Qwen3.8-27B, Qwen3.6, Gemma 4 or DeepSeek V4 Flash. Only IFBench is reported.
- I didn't verify whether GLM-5.3-Flash or Mistral Large 4 weights are downloadable today, or their exact licence text.
- I found no measured tok/s for DeepSeek V4 Flash or Qwen3.8-Flash-Next on 2× PRO 6000 or H200, apart from a community 1-bit/CPU-offload test of Flash-Next: 52 tok/s with one RTX 5090 plus system RAM, unverified — [HF discussion #29](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/discussions/29).

---

## Q2. How close do the best local models get to frontier hosted models on extraction and structured output?

### Takeaway
On **grounded JSON extraction from text**, the gap is essentially gone. In the 2026 Structured Output Benchmark, GLM-4.7 and Qwen3.5-35B match or beat GPT-5.4 and Claude Sonnet 4.6 on value accuracy. On **general intelligence and hard reasoning**, the gap is real and re-widened after the September 2026 frontier releases. Top open is about 12 points behind on the AA index (46 vs 58), and the 27B class is about 24 points behind. **Extraction from audio-derived text is hard for every model** (best value accuracy about 24%). Very wide schemas break everything, including frontier models. So the brain's design (narrow typed schemas, one record type per call, evidence spans) matters more than which model is used.

### Cited Findings
- **Structured Output Benchmark (SOB)** (arXiv 2604.25359, 2026) measured 21 models on schema-valid, context-grounded JSON from text (5,000 HotpotQA records), images (209 OCR'd docs) and audio (115 AMI meeting transcripts). Overall / value accuracy: GPT-5.4 0.870/0.798; **GLM-4.7 0.861/0.804**; **Qwen3.5-35B 0.861/0.801**; Gemini-2.5-Flash 0.860/0.796; Qwen3-235B 0.857/0.786; Claude-Sonnet-4.6 0.854/0.779; Gemma-3-27B 0.847/0.777; Gemma-4-31B 0.833/0.778; Gemini-3-Flash-Preview 0.833/0.773; GPT-OSS-20B 0.732/0.667. JSON pass rate is about 0.94–0.99 for almost every model, so value accuracy is the real differentiator. On text the best open model (GLM-4.7, 0.830) leads GPT-5.4 (0.825). On images Gemma-4-31B leads (0.672). On **audio transcripts the best value accuracy is 0.237** (Gemini 2.5 Flash, closed) against 0.219 for the best open model **[independent, academic]** — [arXiv 2604.25359](https://arxiv.org/html/2604.25359v1)
- **LLMStructBench** (arXiv 2602.14743; 995 cases across 5 business extraction use cases): Gemma3-27B ties GPT-4o (composite 0.74), and 12–27B open models come within about 0.02 of GPT-4o. The authors conclude "choosing the right prompting strategy is more important than … model size", and wrong values are the dominant error **[independent, academic]** — [arXiv 2602.14743](https://arxiv.org/html/2602.14743v1)
- **ExtractBench** (arXiv 2602.12247) tested closed models only (Gemini 3 Pro/Flash, GPT-5/5.2, Claude Sonnet/Opus 4.5) on 35 PDFs with 12–369-field schemas. Only 51% of outputs were valid JSON, the aggregate pass rate was 4.6%, and the 369-field schema produced 0% valid output for every model. Breadth of the schema and output volume predict failure better than page count. **Provider constrained-decoding modes cut validity from 51% to 37%** **[independent, academic]** — [arXiv 2602.12247](https://arxiv.org/html/2602.12247v2)
- A practitioner study estimates the quality cost of structured-output modes from H1 2026 customer workloads (not a controlled benchmark): OpenAI strict 0–3% on easy prompts and 10–15% on hard ones; Anthropic tool use 0–2% and 4–8%; Gemini responseSchema 0–3% and 8–12%; Outlines-style local grammar 5–20% depending on the base model, with weak models "collapsing to the most likely schema-legal continuation" — [FutureAGI](https://futureagi.com/blog/evaluating-llm-structured-output-modes-2026/)
- XGrammar-2 reaches 100% schema accuracy on the BFCL-V3 simple and parallel subsets across four models, with accuracy gains that are largest on smaller models **[vendor/project]** — [MLC blog, 4 May 2026](https://blog.mlc.ai/2026/05/04/xgrammar-2-fast-customizable-structured-generation)
- **General intelligence gap.** On the AA Intelligence Index v4.3.2 (read 17 Oct 2026): Claude Opus 5.5 (max) 58, Claude Sonnet 5.5 56, GPT-6 Astra 53, Gemini 4 Argon 53. The top open model is MiMo-V2.6-Pro at 46 **[leaderboard]** — [DevelopersDigest AA snapshot](https://www.developersdigest.tech/benchmarks/artificial-analysis). Other open scores: GLM-5.3 45, Kimi K3 44, DeepSeek V4.1 Flash 39, Qwen3.8-27B 34; the closed small model Claude Haiku 5.5 scores 43 — [Javadex](https://www.javadex.es/blog/mejores-modelos-ia-octubre-2026-ranking-comparativa-mensual). *Conflict:* the DEV audit gives DeepSeek V4.1 Flash 1017 an AA score of 45.1, not 39 — [DEV audit](https://dev.to/ward_ed_6b5e6aa8ded94a987/best-open-weight-llm-in-october-2026-auditing-two-leaderboards-row-by-row-1b64)
- In April 2026 the gap was only 3–6 points (Kimi K2.6 and MiMo V2.5 Pro at 54 vs GPT-5.5 at 60). The **AA Omniscience** (knowledge/hallucination) gap was much larger: DeepSeek V4 Pro −10, Kimi K2.6 +6, against GPT-5.5 +20, Claude Opus 4.7 +26 and Gemini 3.1 Pro +33 — [Artificial Analysis, 30 Apr 2026](https://artificialanalysis.ai/articles/recent-open-weights-model-launches)
- FutureSearch (Jul 2026) estimates open models have lagged the frontier by about 4 months (about 8 ECI points) since Jan 2026. A CAISI/NIST evaluation estimated an **8-month lag** for DeepSeek V4 Pro on less public benchmarks — [FutureSearch](https://futuresearch.ai/app/p/a/open-weight-llm-overtaking-closed-weight)
- Instruction following (IFBench): Qwen3.8-27B 79.5 and Qwen3.8-Flash-Next 81.3 (vendor), against GPT-5.4 79.4 (provisional) on BenchLM's IFBench board. IFEval entries: Qwen3.5-27B 95%, GPT-5.4 96% (provisional). There are no Claude rows on that board **[leaderboard, mixed provenance]** — [BenchLM instruction-following](https://benchlm.ai/instruction-following)
- BFCL v4 on BenchLM (20 Oct 2026) is 24 of 25 provider self-reports, and none of Claude, GPT-5.x or Gemini 3 appear, so it can't be used for an open-vs-frontier comparison — [BenchLM BFCL v4](https://benchlm.ai/benchmarks/bfclV4)

### Inferences
- For pipelines (a) extraction and (b) scribe, a well-prompted local 27–35B model with xgrammar-constrained JSON should land within a few points of frontier APIs on field accuracy, **provided each call uses a narrow schema** (one typed record type, under about 30 fields) and keeps the model's reasoning separate from the constrained output. A practical pattern is unconstrained "think" first, then a constrained JSON pass, or Structural Tags that allow a free reasoning channel.
- Meeting transcripts are the weak spot for everyone. The SOB audio value accuracy of about 0.22–0.24 says that diarised, speaker-attributed transcripts plus chunk-level extraction (not whole-meeting extraction) are needed, along with a stronger model or a hosted model for decisions and commitments drawn from meetings.
- **Where hosted APIs are clearly better:** (1) change-time planning on ambiguous or conflicting facts and entity merges, which leans on reasoning and calibration, where the gap is 12–24 AA points plus the hallucination gap; (2) LLM-as-judge for the golden-set evaluation; (3) the hardest meeting-transcript extraction. Per the project's existing agreement, member health data stays local, so those pipelines must run on the local model regardless.

### Gaps
- No public extraction benchmark yet includes Qwen3.8-27B, Qwen3.6-27B, DeepSeek V4 Flash or Claude 4.x/5.x side by side. SOB's open models are one generation behind (GLM-4.7, Qwen3.5-35B).
- No benchmark specific to entity linking or change planning was found. This must be measured on the brain's own golden set (brainbench).

---

## Q3. Embedders, rerankers, multimodal embedders, VLM/OCR, ASR and diarisation

### Takeaway
- **Text embedding:** Qwen3-Embedding-8B (Apache 2.0) remains the safe default. Microsoft **harrier-oss-v1-27b** (MIT, Mar 2026) now leads MTEB-multilingual retrieval but costs about 54 GB.
- **Multimodal embedding:** Qwen3-VL-Embedding-8B (Apache 2.0) is the default for text, image, video and screenshots in one vector space.
- **Visual-document late interaction:** EVIE-8B / nemotron-colembed-vl-8b-v2 / colqwen3.5-4.5B.
- **Reranking:** Qwen3-Reranker-4B (Apache 2.0) is the best quality-per-latency choice. Use Qwen3-VL-Reranker-8B for visual items.
- **OCR:** PaddleOCR-VL-1.6 (0.9B) tops OmniDocBench v1.6, ahead of Gemini 3 Pro.
- **ASR:** Qwen3-ASR-1.7B plus Qwen3-ForcedAligner (Apache 2.0) gives word timestamps in 52 languages. Parakeet-TDT-0.6B-v3 or Canary-Qwen-2.5B are the English-centric alternatives.
- **Diarisation:** pyannote community-1 (11.1% DER on VoxConverse).

All of these fit on one 96 GB card next to a 27B LLM.

### Cited Findings

**Text embedders**
- Qwen3-Embedding (HF card): MMTEB mean/retrieval for 0.6B 64.33/64.64, **4B 69.45/69.60, 8B 70.58/70.88**. MTEB-English v2 mean/retrieval for 4B 74.60/68.46 and 8B 75.22/69.44. 32K context, MRL dimensions 32–4096, Apache 2.0. Serve with vLLM ≥0.8.5 (`task="embed"`) or TEI 1.7.2+ **[vendor]** — [HF Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B). (One secondary source calls the licence "Tongyi Qianwen custom", which contradicts the HF card's Apache-2.0 — [Presenc](https://presenc.ai/research/best-open-weight-embedding-models-2026).)
- MTEB snapshot as of 26 Sep 2026: **harrier-oss-v1-27b** is #1 on Multilingual v2 (mean 0.7427, **retrieval 0.7827**, MIT, 5,376 dims, 32K). KaLM-Embedding-Gemma3-12B is #2 (custom licence), llama-embed-nemotron-8b #3 (non-commercial), Qwen3-Embedding-8B #4 (mean 0.7058, retrieval 0.7088) and Octen-Embedding-8B #7 (Apache, derived from Qwen3-Embedding-8B, RTEB #3). **Nemotron-3-Embed-8B** (16 Jul 2026, OpenMDW-1.1) is RTEB #2. jina-embeddings-v5-text-small is CC BY-NC (non-commercial) **[leaderboard]** — [Maximem, 27 Sep 2026](https://www.maximem.ai/blog/best-embedding-models-2026)
- harrier-oss-v1-27b card: 27B, MTEB v2 multilingual 74.3, 94 languages, MIT, queries need a one-sentence instruction, TEI tag. Weights are about 54 GB at BF16 [estimate] — [HF harrier-oss-v1-27b](https://huggingface.co/microsoft/harrier-oss-v1-27b)
- jina-embeddings-v5-text (19 Feb 2026): small (677M, MMTEB 67.0) and nano (239M, 65.5), both **CC BY-NC 4.0** — [Jina](https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings)

**Multimodal and visual-document retrieval**
- **Qwen3-VL-Embedding-8B** (Jan 2026, Apache 2.0): embeds text, images, screenshots, video and mixed inputs; dims 64–4096 (MRL), 32K context, 30+ languages. MMEB-V2 77.9 (image 80.1, video 66.1, VisDoc 83.3); MMTEB 67.88 (retrieval 69.41). Supports vLLM (`runner="pooling"`) and SGLang **[vendor]** — [HF Qwen3-VL-Embedding-8B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B); [arXiv 2601.04720](https://arxiv.org/pdf/2601.04720)
- **Qwen3-VL-Reranker-8B / 2B**: ViDoRe v3 66.7 and 60.8; visual-doc average 80.3 and 76.7 **[vendor]** — [arXiv 2601.04720](https://arxiv.org/pdf/2601.04720)
- ViDoRe v3 (nDCG@10, snapshot 20 Apr 2026): nemotron-colembed-vl-8b-v2 63.42; tomoro-colqwen3-embed-8b 61.59; nemotron-colembed-vl-4b-v2 61.54; **colqwen3.5-4.5B-v3 61.46 (Apache 2.0, 128-dimension multi-vector)**; jina-embeddings-v4 57.52 **[leaderboard]** — [HF colqwen3.5-4.5B-v3](https://huggingface.co/athrael-soju/colqwen3.5-4.5B-v3)
- **Tencent EVIE-8B** (4 Sep 2026, Apache 2.0, Qwen3.5-9B backbone, late interaction, 4096 dims per token): ViDoRe v3 66.75 and JinaVDR 83.30. **Vendor-reported, no paper, not reproduced** — [OrcaRouter](https://www.orcarouter.ai/blog/evie-8b-quiet-release)

**Rerankers**
- Qwen3-Reranker (HF card; MTEB-R / CMTEB-R / MMTEB-R / MLDR): **0.6B** 65.80/71.31/66.36/67.28; **4B** 69.76/75.94/72.74/69.97; **8B** 69.02/77.45/72.94/70.19. For comparison, bge-reranker-v2-m3 scores 57.03/72.16/58.36/59.51. 32K context, Apache 2.0 **[vendor]** — [HF Qwen3-Reranker-8B](https://huggingface.co/Qwen/Qwen3-Reranker-8B)
- Latency on L40S (batch 32, 512-token pairs): Qwen3-Reranker-8B ~38 ms/pair (~26 pairs/s; ~3.8 s for 100 pairs); bge-reranker-v2-m3 ~12 ms/pair (~83 pairs/s) **[secondary, May 2026]** — [Presenc rerankers](https://presenc.ai/research/best-open-weight-reranker-models-2026); [LLMs Blog](https://www.llms.blog/posts/reranking-engines-in-production-rag-comparing-bge-reranker-qwen3-reranker-cohere-rerank-jina-colbert-and-flashrank-architecture-latency-quality-and-self-hosted-economics)
- jina-reranker-v3 (0.6B, 131K context, BEIR 61.94) is **CC BY-NC 4.0** — [Jina](https://jina.ai/models/jina-reranker-v3/). mxbai-rerank-large-v2 (Apache, ~1.5–2B): BEIR 57.49 on its own evaluation, 0.89 s latency on A100 — [HF mxbai](https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2)

**VLMs for captioning, OCR and video**
- Qwen3-VL (Nov 2025, 2B–235B). For example, Qwen3-VL-8B Instruct scores OCRBench 896, DocVQA 96.1, Video-MME 71.4, and the 32B scores Video-MME 76.6. Text timestamps are attached to video frames to support grounding and dense captioning **[vendor]** — [Qwen3-VL Tech Report](https://arxiv.org/pdf/2511.21631)
- Qwen3.8-27B vision (vendor): OmniDocBench 1.5 91.1 vs Claude Opus 4.6 Max 86.6; RealWorldQA 85.9 vs 73.9; CharXiv-RQ 83.7 vs 66.0. ParseBench mean 70.79 (FP8 checkpoint) **[vendor]** — [HF Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B)
- **PaddleOCR-VL-1.6 (0.9B)**: OmniDocBench v1.6 overall 96.33, against MinerU2.5 93.04, Gemini 3 Pro 92.91, dots.ocr 90.77, DeepSeek-OCR 2 90.25, Qwen3-VL-235B 89.78 and GPT-5.2 86.59 **[vendor paper, 2 Jun 2026]** — [arXiv 2606.03264](https://arxiv.org/pdf/2606.03264)
- olmOCR-Bench (updated 21 May 2026): infinity-parser2-pro 87.6, chandra-2 85.9, dots.mocr 83.9, LightOnOCR-2-1B 83.2, olmocr-2-7b 82.4, paddleocr-vl 80.0, Qwen3-VL-4B 79.2, mistral-ocr-3 78.0, deepseek-ocr-2 76.3, gemini-flash-2 63.8 **[leaderboard]** — [CodeSOTA](https://www.codesota.com/ocr/benchmark/olmocr-bench)
- Gemma 4 runs video natively up to 60 s on the 26B/31B models. A secondary source reports Gemma 4 12B at about 250 tok/s on an RTX 4090 — [DataNorth](https://datanorth.ai/news/google-releases-gemma-4-open-models); [AIMadeTools](https://www.aimadetools.com/blog/best-multimodal-models-run-locally-2026/) (the latter's "Gemma 4 27B" naming conflicts with official sizes, so treat it with caution).

**ASR and diarisation**
- Open ASR Leaderboard average WER (sampled 6 May 2026): granite-speech-4.1-2b 5.33; cohere-transcribe-03-2026 5.42; granite-4.0-1b-speech 5.52; canary-qwen-2.5b 5.63; **Qwen3-ASR-1.7B 5.76**; parakeet-tdt-0.6b-v2 6.05; parakeet-tdt-0.6b-v3 6.32; Qwen3-ASR-0.6B 6.42; Voxtral-Small-24B 6.62 **[leaderboard]** — [BenchmarkList Open ASR](https://benchmarklist.com/benchmarks/open_asr_leaderboard/). Whisper large-v3 scores 7.44 — [NYU RITS](https://rits.shanghai.nyu.edu/ai/cohere-transcribe-2b-open-source-asr-model-takes-1-on-leaderboard/)
- Cohere Transcribe (26 Mar 2026, 2B, Apache 2.0, 14 languages) has **no timestamps, no diarisation and no language auto-detection** — [NYU RITS](https://rits.shanghai.nyu.edu/ai/cohere-transcribe-2b-open-source-asr-model-takes-1-on-leaderboard/)
- **Qwen3-ASR** (Jan 2026, Apache 2.0) covers 52 languages and dialects. The 0.6B model reaches **2,000 s of audio per second** (RTF 0.064) at 128 concurrency on vLLM. **Qwen3-ForcedAligner-0.6B** gives timestamps in 11 languages with 32.4 ms average shift (67–77% better than NFA and other aligners), handles inputs up to 300 s, and processes about 1,000 s of audio per second. Streaming is supported. Maximum ASR input is 20 min **[vendor paper]** — [arXiv 2601.21337](https://arxiv.org/html/2601.21337)
- Parakeet-TDT-0.6B-v3: 25 European languages with auto language detection, word-level timestamps, up to 3 h of audio, ~2.5 GB VRAM, CC-BY-4.0 — [Mixpeek](https://www.mixpeek.com/model/nvidia/parakeet-tdt-0.6b-v3). Canary-Qwen-2.5B: English only, RTFx 418, CC-BY-4.0. Whisper large-v3-turbo: 809M, 99+ languages, MIT, ~6 GB — [Northflank](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)
- pyannote **community-1** (open) scores 11.1% DER on VoxConverse; **precision-2** (proprietary) scores 8.8%. With Baseten's optimisations (mixed precision, index clustering), community-1 diarises **20 h of audio in about 2 min on one RTX PRO 6000** (not stock pyannote) **[vendor/partner, 9 Sep 2026]** — [Baseten](https://www.baseten.co/blog/how-baseten-makes-pyannotes-diarization-models-96x-faster/). NeMo Sortformer is capped at 4 speakers; pyannote has no ceiling — [pyannoteAI](https://www.pyannote.ai/blog/pyannote-vs.-nvidia-nemo-diarization-accuracy-setup-and-production-readiness)

**Embedding throughput**
- Runpod (Sep 2026), single run per cell: for **Qwen3-Embedding-8B, vLLM is 2.9× faster than TEI**, and for 0.6B it is 2.6× faster. bge-m3 on 512-token passages with TEI: L40S ~277 texts/s, H100 ~1,240 texts/s **[independent]** — [Runpod](https://www.runpod.io/blog/gpu-embedding-workloads-benchmark)

### Inferences
- **Recommended local retrieval stack:**
  - Qwen3-Embedding-8B for text, with MRL truncated to 1024–2048 dims for index size.
  - Qwen3-VL-Embedding-8B for images, video and screenshots. It can replace the text embedder entirely, since its MMTEB retrieval of 69.41 is only about 1.5 points below Qwen3-Embedding-8B, which simplifies to one vector space.
  - Qwen3-Reranker-4B for text, since 4B ≈ 8B on MTEB-R/MMTEB-R at about half the compute.
  - Qwen3-VL-Reranker-8B for visual candidates.
  - Optionally a ColQwen-style multi-vector index for scanned documents.
- Run a harrier-27B A/B test only on a card with spare headroom (Tier 3). Its +7 retrieval points on MMTEB-multi are a leaderboard figure and need checking on brainbench.
- **ASR pipeline:**
  1. Qwen3-ASR-1.7B (or Parakeet-v3 / Canary-Qwen for English-only) → text.
  2. Qwen3-ForcedAligner → word timestamps.
  3. pyannote community-1 → speaker turns.
  4. Merge turns and words by timestamp, then do chunk-level extraction.

  Avoid Cohere Transcribe for this pipeline because it has no timestamps.
- OCR: route scanned documents and PDFs through PaddleOCR-VL-1.6 (0.9B, cheap). Route photos, whiteboards and screenshots through Qwen3.8-27B for captions with OCR. This avoids loading a second large VLM.

### Gaps
- I found no measured Qwen3-Embedding-8B or Qwen3-Reranker-4B throughput on an RTX PRO 6000 or 5090. Tier estimates below use first-principles arithmetic.
- No Australian-English ASR benchmark was found. WER on Australian accents must be measured locally.
- I couldn't confirm whether granite-speech-4.1-2b (top WER) produces timestamps.
- No speed figure was found for **stock** (unoptimised) pyannote community-1.
- No newer open reranker releases from 2026 were verified (zerank-2 open weights, Nemotron reranker, Qwen3.5/3.8-Reranker).

---

## Q4. Serving stacks

### Takeaway
Use **vLLM** as the primary engine for the LLM, the embedder, the VLM-embedder and ASR. It has the broadest model coverage, pooling/embedding support, MTP, and xgrammar/guidance structured outputs. **SGLang** is the alternative when structured-output-heavy or prefix-sharing workloads dominate. TensorRT-LLM gains 7–14% but costs operational complexity. TEI is fine for small BERT-class models but is about 3× slower than vLLM for Qwen3-Embedding-8B. llama.cpp/Ollama only make sense on Mac or Strix Halo boxes or for single-user use.

### Cited Findings
- vLLM's default structured-output backend is xgrammar, with guidance/llguidance as an alternative. JSON Schema compiles and decodes faster than complex EBNF — [vLLM forum](https://discuss.vllm.ai/t/as-of-july-2026-what-are-some-general-tips-in-improving-the-speed-of-guided-decoding-in-vllm/2845)
- **XGrammar-2** (4 May 2026) adds Structural Tags for reasoning channels, tool calls and the Harmony format, plus cross-grammar caching, up to 80× faster compilation from 10 to 500 tools, and overlap with speculative decoding. It is integrated into vLLM, SGLang, TensorRT-LLM and MLC-LLM, with built-in formats for DeepSeek V4, Qwen 3.6 and GPT-OSS — [MLC](https://blog.mlc.ai/2026/05/04/xgrammar-2-fast-customizable-structured-generation)
- SGLang measured about 16,200 tok/s against vLLM's 12,500 on H100 (Llama 3.1 8B) and has the fastest structured output via xgrammar. vLLM has the broadest model and hardware set (text, VLM, audio, embedding, omni). TGI "has entered maintenance mode" (Apr 2026) **[secondary]** — [Fish Audio](https://fish.audio/blog/open-source-llm-inference-engines-2026/)
- Qwen's recommended versions for Qwen3.6: SGLang ≥0.5.10 or vLLM ≥0.19.0, with `--reasoning-parser qwen3` and `--tool-call-parser qwen3_coder`. MTP is supported in both — [HF Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B)
- **TensorRT-LLM vs vLLM on an RTX 5090** (Qwen3.8-27B NVFP4, Oct 2026). TRT-LLM with FP8 KV was 14% ahead at 32 concurrent and 7% ahead for one user. At default settings vLLM was 57% faster at 32 concurrent, because TRT-LLM ran out of KV. TRT-LLM's text-only mode failed with a loader bug, and SM120 lacks W4A16 INT4 kernels. FP8 KV *hurt* vLLM on this hybrid model by shrinking the request pool. vLLM's cold start was 718 s because of FlashInfer JIT; keep the compile cache on a persistent volume — [ComputingForGeeks](https://computingforgeeks.com/tensorrt-llm-vs-vllm/)
- Blackwell SM120 gotchas: the PyPI CUDA 13 fragments are not enough for FlashInfer JIT, so install the full CUDA 13 toolkit. Start GPU instances one after another to avoid torch.compile contention. Use `--language-model-only` to save ~2 GB when vision isn't needed. One vLLM instance per GPU with `--max-num-seqs 8`; avoid tensor parallelism over PCIe — [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide)
- TEI supports Qwen3 and Gemma3 embedding architectures. Blackwell sm_120 uses the `120-1.9` image tag (experimental). Batching is token-based (`--max-batch-tokens`, default 16384). There is no mention of Qwen3-Reranker support — [TEI README](https://cdn.jsdelivr.net/gh/huggingface/text-embeddings-inference@main/README.md)
- Qwen3-ASR benchmarks were run on vLLM v0.14.0 — [arXiv 2601.21337](https://arxiv.org/html/2601.21337). Qwen3-VL-Embedding supports vLLM pooling and SGLang `is_embedding` — [HF](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B)
- On Strix Halo, use llama.cpp with the Vulkan (RADV) backend for generation and ROCm for long-context prompt processing. Ollama "has historically underused unified memory" — [Codersera Strix Halo](https://codersera.com/blog/amd-strix-halo-ryzen-ai-max-local-llm-setup-2026/)

### Inferences
- **Multi-model on one GPU:** run separate vLLM processes, each with `--gpu-memory-utilization` set to its share:
  - LLM ~0.55
  - embedder ~0.18
  - reranker ~0.10
  - ASR+aligner ~0.06
  - OCR ~0.03

  Put a small router (for example LiteLLM, or the builder's own FastAPI gateway) in front with priority queues, so interactive queries pre-empt batch ingest. Alternatively, run ingest overnight and keep daytime capacity for queries.
- Pin specific vLLM versions in Docker images (Blackwell regressions are common) and keep the FlashInfer/torch.compile caches on persistent volumes.
- Use `response_format: json_schema` (xgrammar) for every extraction call, with schemas kept flat and enums small. For thinking models, use Structural Tags or a two-pass approach so reasoning isn't forced through the grammar.

### Gaps
- No official vLLM documentation was fetched on co-locating several engines on one GPU (memory-fraction semantics, or MIG on the RTX PRO 6000).
- No head-to-head of TEI, Infinity and vLLM was found for Qwen3-Reranker serving.

---

## Q5. GPU options and costs in Australia

### Takeaway
GPU prices rose sharply through 2026. The RTX PRO 6000 Blackwell 96 GB went from about US$8.5K at launch to a **US$16K list price (Aug 2026)**. In Australia it sells for about **A$20–32K** (3-month median A$25,100), and AU retail RTX 5090s run **A$5.4–7.4K**. A rented single PRO 6000 in Melbourne (Micron21 mCloud) costs **A$3,030/month ex GST**. Hyperscalers sell H200 in Sydney only as 8-GPU nodes (US$63–123/h). Australian sovereign neoclouds (Firmus/Sustainable Metal Cloud, Sharon AI, ResetData) are quote-only. Mac Studio M5 Ultra, DGX Spark and Strix Halo are cheaper per GB of memory, but their prefill and multi-user batching are far weaker than a discrete Blackwell card's. That matters because the brain's write gate is prefill-heavy.

### Cited Findings

**Workstation and server cards (buy)**
- **RTX PRO 6000 Blackwell 96 GB.** Prices: A$16,340 ex GST at Computer Orbit (Workstation Edition, out of stock, undated) — [Computer Orbit](https://au.computerorbit.com/products/nvidia-rtx-pro-6000-max-q-blackwell-workstation-edition-96gb-professional-graphics-card-retail-copy); Amazon AU A$31,859 for the PNY Max-Q (22 Oct 2026), with a 12-month low of A$19,794 and a 3-month median of A$25,100 — [GPUPrix AU](https://gpuprix.com/australia/gpus/rtx-pro-6000-blackwell). NVIDIA US list price was US$16,000 on 12 Aug 2026, up from ~US$8,565 at launch and US$13,250 in June 2026 — [LetsDataScience](https://letsdatascience.com/news/nvidia-raises-rtx-pro-6000-blackwell-price-again-6d1ae9ff)
- RTX PRO 6000 spec: 1,792 GB/s rated bandwidth — [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide). The Server Edition measured 1,468 GB/s and 311.6 TFLOPS FP16 (cuBLAS) at 600 W — [ParalonCloud](https://paraloncloud.com/resources/rtx-pro-6000-vs-2x-rtx-4090-qwen3-8-27b)
- **RTX 5090 32 GB**: AU launch price A$4,039. Retailer lows A$5,399–5,799, with a new-unit tracker at A$7,399 (3 Sep 2026) — [Tech Insider AU](https://tech-insider.org/au/?p=1377). In March 2026 entry cards were ~A$5,999 and stock was "effectively scarce" — [Glukhov](https://www.glukhov.org/hardware/gpu/nvidia-rtx-5080-rtx-5090-prices-march-2026/)
- **H200 NVL 141 GB** (PCIe): eBay average of the lowest listings was US$41,352 in Sep 2026 and US$46,804 in Oct 2026 (≈A$59–66K at 1.42) — [GPUPoet](https://gpupoet.com/gpu/learn/price/september-2026/nvidia-h200-nvl)
- A single RTX PRO 6000 beat both 4× RTX 4090 and 4× RTX 5090 on a 30B MoE under load (Sep 2025) — [CloudRift](https://www.cloudrift.ai/blog/benchmarking-gpu-servers-for-llm-inference)

**Unified-memory alternatives**
- **Mac Studio M5 Ultra** (announced 25 Aug 2026; shipping from 22 Sep; 512 GB configuration late Oct): from **A$9,499**, +A$6,000 for 256 GB; 512 GB not yet priced (the article's author estimates ~A$40K). M5 Max starts at A$4,299. Bandwidth is 1.2 TB/s on the Ultra and 614 GB/s on the Max — [Man of Many](https://manofmany.com/tech/mac-studio-m5-max-m5-ultra); [Implicator](https://www.implicator.ai/apple-mac-studio-m5-ultra-prompt-processing/)
- M5 Max (128 GB) on Qwen3.5-122B-A10B 4-bit: 881–1,068 tok/s prompt processing and 55–66 tok/s generation. The RTX PRO 6000 was 2.3–3.5× faster at prompt processing and 50–65% faster at generation. Apple claims M5 Ultra prompt processing is up to 4× the M3 Ultra's; there is no independent M5 Ultra benchmark yet — [Implicator](https://www.implicator.ai/apple-mac-studio-m5-ultra-prompt-processing/)
- **DGX Spark / GB10 (128 GB)** in Australia: A$6,249 (ASUS GX10, Centrecom) to A$7,999 (MSI EdgeXpert), Jan 2026 — [Glukhov](https://glukhov.org/hardware/ai/dgx-spark-pricing-in-australia/). EXO Labs found DGX Spark 3.8× faster than M3 Ultra at prompt processing but M3 Ultra 3.4× faster at generation — [Implicator](https://www.implicator.ai/apple-mac-studio-m5-ultra-prompt-processing/)
- **Strix Halo** (Ryzen AI Max+ 395, 128 GB, ~215 GB/s measured): gpt-oss-120b at ~53 tok/s generation and ~120 tok/s prompt processing; Qwen3-30B-A3B at 86 tok/s generation and 1,142 tok/s prompt processing — [strix-halo-llm-perf](https://github.com/visorcraft/strix-halo-llm-perf). Dense 70B runs at about 5 tok/s. Boxes cost roughly US$1,700–2,200 — [Codersera](https://codersera.com/blog/amd-strix-halo-ryzen-ai-max-local-llm-setup-2026/). AMD's Ryzen AI Halo mini PC is US$3,999 — [Phoronix](https://www.phoronix.com/review/amd-ryzen-ai-halo/3)

**Australian cloud (rent)**
- **Micron21 mCloud (Melbourne, Tier IV, Australian-owned; vendor's own article):** RTX PRO 6000 at **A$3,030/month** for a full instance (12 vCPU, 64 GB RAM, 500 GB NVMe) ex GST, or A$2,550 GPU-only (A$3.54/h); 2 cards A$5,860/month, 4 cards A$11,520. Overseas comparisons: Vast.ai US$1.42/h, RunPod US$2.09/h, AWS g7e.2xlarge US$3.36/h (region not stated), GCP g4 US$4.50/h — [Micron21 RTX PRO 6000, 8 Jul 2026](https://www.micron21.com/blog/nvidia-rtx-pro-6000-cloud-pricing-in-australia-2026-mcloud-vs-aws-azure-google-and-neoclouds)
- **Micron21 H200**: A$4,380/month per card ex GST on a 12-month term (≈A$6.08/h). **AWS p5e (Sydney)**: 8×H200 only, US$63.28/h per node. **Azure ND H200 v5 (Australia East)**: 8-GPU only, US$122.96/h. **GCP A3 Ultra (australia-southeast)**: about 15% above the US rate of US$86.76/h. **Firmus (Sustainable Metal Cloud), Sharon AI (in NEXTDC Melbourne/Sydney), ResetData (1,024 H200s in Melbourne), Vault Cloud, Scaile, Macquarie**: quote only — [Micron21 H200, 7 Jul 2026](https://www.micron21.com/blog/nvidia-h200-cloud-pricing-in-australia-2026-mcloud-vs-aws-azure-google-cloud-and-neoclouds)
- AWS **g7e** (RTX PRO Server 6000 96 GB; g7e.4xlarge = 16 vCPU, 128 GiB, US$3.9982/h in US regions) and **g6e** (L40S 48 GB; g6e.xlarge US$1.861/h on demand in US-East, US$1.172/h with a 1-year reservation) are listed as available in **Sydney (ap-southeast-2) and Melbourne (ap-southeast-4)**. The Sydney and Melbourne prices were behind a paywall — [CloudPrice g7e](https://cloudprice.net/aws/ec2/instances/g7e.4xlarge); [CloudPrice g6e](https://cloudprice.net/aws/ec2/instances/g6e.2xlarge); [Vantage g6e](https://instances.vantage.sh/aws/ec2/g6e.xlarge)

**Colocation**
- NEXTDC (Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra, Darwin) offers rack densities up to 150 kW (600 kW custom) with rear-door and direct-to-chip liquid cooling. Pricing is by quote only — [NEXTDC](https://www.nextdc.com/blog/why-leading-gpu-cloud-providers-choose-nextdc-in-australia)

### Inferences
- **Buy vs rent, recommended tier [estimate]:** an RTX PRO 6000 at about A$25K (3-month median) plus a host build of about A$10–15K [estimate] comes to about A$35–40K. At mCloud's A$3,030/month, breakeven is about 12–13 months, before power, colocation and staff time. For a system meant to run for years, buying wins after year one. Renting mCloud for the first 2–3 months is a sensible way to validate model choices before buying.
- Hyperscaler Australian GPU capacity is the wrong shape for this workload: 8-GPU H200 nodes cost A$65K+ per month at the article's conversion. Use hyperscalers only for burst re-indexing, if at all.
- Mac M5 Ultra 512 GB (~A$40K estimated) could hold 300B+ MoEs for a private single-user assistant, but it is a poor write-gate server. Prompt processing is 2–3.5× slower than a PRO 6000 (based on M5 Max data), and MLX batching for multi-user serving is weaker. DGX Spark and Strix Halo are good dev or second-tier boxes, not the primary server.

### Gaps
- I couldn't retrieve exact AWS Sydney/Melbourne hourly prices for g6e or g7e, Azure NC RTX 6000 v6 Australian pricing, or GCP G4 Australian pricing.
- No published colocation price per kW or per rack-unit was found for NEXTDC, Equinix SY or Firmus.
- No AU retail price was found for L40S, H100 PCIe, B200 or MI300X cards. AU server integrator quotes are needed.
- The RTX 5090 AU price for October 2026 specifically is unverified; the latest datapoint is 3 Sep 2026.

---

## Q6. Sizing: three tiers, with throughput arithmetic and query latency budgets

### Takeaway
**[All numbers in this section are estimates built from the measured anchors above; the working is shown.]**
- **Starter (2× RTX 5090):** about 10–12 h for 10k items, about 4–5 days for 100k items.
- **Recommended (1× RTX PRO 6000 96 GB):** about 4–7 h for 10k items, about 2–3 days for 100k items, with every model co-resident.
- **Ambitious (2–4× RTX PRO 6000, or 2× H200 NVL):** about 2–3.5 h for 10k items, about 1–1.5 days for 100k items, plus a 120–320B MoE for hard planning and the private assistant.

Retrieval-only query latency should be about 0.5–1.2 s at p50 on the recommended tier.

### Per-item write-gate token budget (assumptions, non-thinking mode)
| Stage | Input tokens | Output tokens | Notes |
|---|---|---|---|
| (a) Extraction (typed records + entity mentions) | 3,000 (1,500 system/schema prefix, cacheable + 1,500 item) | 600 | JSON via xgrammar |
| (b) Scribe entry (words used, aliases, anticipated questions) | 2,000 | 400 | |
| (c) Change planning vs existing records | 3,000 (new facts + top-k existing) | 300 | |
| **Total per item** | **8,000** (~3,000 cacheable via prefix cache → ~5,000 effective prefill) | **1,300** | With thinking on, output is ×3–5 |

### Anchor rates (measured)
- PRO 6000, Qwen3.8-27B W4A16 + MTP: decode 1,342 tok/s total at 32 concurrent; prefill ~5,000 tok/s at 22K prompts and up to ~9,850 tok/s at 8K (Qwen3.6-27B FP8) — [ParalonCloud](https://paraloncloud.com/resources/rtx-pro-6000-vs-2x-rtx-4090-qwen3-8-27b); [Millstone](https://www.millstoneai.com/inference-benchmark/qwen3-6-27b-fp8-1x-rtx-pro-6000-blackwell)
- RTX 5090, Qwen3.8-27B NVFP4: 440 tok/s at 8 concurrent, 1,195 at 32 — [ComputingForGeeks](https://computingforgeeks.com/tensorrt-llm-vs-vllm/). On a 32 GB card, KV room is about 6–8 GB after the 21.9 GB of weights. At about 134 KB/token FP8 KV — [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide) — an 8K-token request needs about 1.1 GB, so realistic concurrency is about 6–8 [estimate].

### Arithmetic: LLM stages
- **Recommended (PRO 6000):** prefill 5,000 effective tokens ÷ ~5,000–7,000 tok/s = 0.7–1.0 s per item. Decode 1,300 tokens ÷ ~1,000–1,340 tok/s aggregate = 1.0–1.3 s per item (aggregate GPU time). Serial sum ≈ **1.7–2.3 s per item**, or ~2.5 s with co-resident models taking compute. → **~1,400–2,100 items/h**.
  - 10k items: **~4.8–7 h**.
  - 100k items: **~48–70 h (2–3 days)**.
  - With thinking at medium effort (output ×3 ≈ 3,900 tokens): ~4–5 s per item → 10k in ~11–14 h, 100k in ~5–6 days.
- **Starter (RTX 5090 dedicated to the LLM):** prefill ~1.0 s plus decode 1,300 ÷ ~440 tok/s ≈ 3.0 s → **~4 s per item ≈ 900 items/h**. 10k in ~11 h; 100k in ~4.6 days.
- **Ambitious (2× PRO 6000, one 27B extraction replica per card):** ~2× the recommended rate → 10k in ~2.5–3.5 h; 100k in ~24–35 h. A 3rd and 4th card hold a large MoE (for example Qwen3.5-122B-A10B FP8 at ~122 GB, or GLM-5.3-Flash / DeepSeek V4 Flash at FP4–FP8 ~150–170 GB) used only for flagged hard cases (say 5–10% of items) and the assistant.

### Arithmetic: embedding (d)
- Per item ≈ 1,500 tokens to embed (scribe entry ~500 plus item chunks ~1,000). 100k items = 150M tokens; 10k = 15M.
- Qwen3-Embedding-8B forward pass ≈ 2 × 8e9 = 16 GFLOP/token. PRO 6000 ~311 TFLOPS FP16 measured × ~40% utilisation ≈ 125 TFLOPS → **~7,800 tok/s**. So 100k items takes ~5.3 h and 10k ~32 min. The 4B model is ~2× faster. This assumes vLLM (2.9× faster than TEI for this model per [Runpod](https://www.runpod.io/blog/gpu-embedding-workloads-benchmark)).
- RTX 5090: similar order of compute [assumption, uncited] → ~5–6 h for 100k on the 8B. Use 4B in the starter tier for ~2.5–3 h.

### Arithmetic: media (f, g)
Assume 10% of items are images and 2,000 hours of meeting audio within 100k items.
- **Images via Qwen3.8-27B:** ~1,500 input tokens (image) plus 250 output → ~0.3 s prefill plus ~0.25 s decode at batch ≈ 0.55 s per image → 10k images ≈ 1.5 h. OCR documents through PaddleOCR-VL-1.6 (0.9B) should be much faster (throughput not published; gap).
- **ASR:** Qwen3-ASR-0.6B at 2,000× real time (vendor, vLLM, 128 concurrency). The 1.7B model is assumed to be ~3× slower, ~600×, so 2,000 h of audio takes ~3.3 h. The aligner at ~1,000× adds ~2 h. Diarisation with optimised pyannote at ~560× (20 h in 128 s) adds ~3.6 h; stock pyannote speed is unknown (gap). Media total ≈ **10 GPU-hours** per 2,000 h of audio.

### Query-time latency budget (recommended tier, retrieval only)
| Step | Budget | Basis |
|---|---|---|
| Query embedding (8B, ~30 tokens) | 20–50 ms | short-input forward pass [estimate] |
| ANN + BM25 + graph lookups (100k items, 1–3 vectors each) | 10–50 ms | typical HNSW on ≤1M vectors [estimate] |
| Rerank top-40 with Qwen3-Reranker-4B on ~250-token scribe entries (10K tokens × 8 GFLOP ≈ 80 TFLOP) | 0.3–0.8 s | compute-bound arithmetic; scaled from the L40S 8B figure of ~38 ms/pair at 512 tokens — [Presenc](https://presenc.ai/research/best-open-weight-reranker-models-2026) |
| **Retrieval total** | **~0.4–1.0 s p50; target <1.5 s p95** | |
| Optional local answer synthesis (Qwen3.8-27B, 2–4K context, 300 tokens) | TTFT 0.2–0.8 s + 300 ÷ 80–100 tok/s ≈ 3–4 s | 170 ms TTFT at 1K, 0.8 s at 8K — [Millstone](https://www.millstoneai.com/inference-benchmark/qwen3-6-27b-fp8-1x-rtx-pro-6000-blackwell); ~80–106 tok/s single stream |

### Tier definitions

| | **Starter** | **Recommended** | **Ambitious** |
|---|---|---|---|
| Hardware | 2× RTX 5090 32 GB in a workstation (cards ≈ A$11–15K at A$5.4–7.4K each); or 1× 5090 with model swapping | 1× RTX PRO 6000 96 GB (≈A$20–32K; median A$25.1K) + 256 GB RAM host; or mCloud rental A$3,030/month | 2–4× RTX PRO 6000 (≈A$50–100K cards) in a 4U server at NEXTDC colocation; or mCloud 4-card A$11,520/month; or 2× H200 NVL (~US$83–94K) |
| Extraction / scribe / planning LLM | Qwen3.8-27B NVFP4 (GPU0) | Qwen3.8-27B FP8 (~28 GB) or W4A16 (19 GB) + MTP | Qwen3.8-27B FP8 replica per card + large MoE (Qwen3.5-122B-A10B FP8 / DeepSeek V4 Flash / GLM-5.3-Flash) for hard cases and the assistant |
| Embedder | Qwen3-Embedding-4B or Qwen3-VL-Embedding-2B (GPU1) | Qwen3-VL-Embedding-8B (+ optionally Qwen3-Embedding-8B) | + harrier-oss-v1-27b A/B; ColQwen/EVIE multi-vector for documents |
| Reranker | Qwen3-Reranker-0.6B/4B | Qwen3-Reranker-4B + Qwen3-VL-Reranker-2B | Qwen3-Reranker-8B + Qwen3-VL-Reranker-8B; optional LLM listwise rerank with the MoE |
| VLM / OCR | Qwen3.8-27B (shared) + PaddleOCR-VL-1.6 | same | same + dedicated Qwen3-VL-32B or Qwen3.8-27B replica |
| ASR / diarisation | Parakeet-v3 or Qwen3-ASR-0.6B + aligner + pyannote community-1 | Qwen3-ASR-1.7B + ForcedAligner + pyannote community-1 | same, plus streaming ASR for live meetings |
| 10k items through the full gate (non-thinking) | ~11 h LLM + ~1 h embed + media | ~5–7 h + ~0.5 h + media | ~2.5–3.5 h + media |
| 100k items | ~4.6 days + ~3 h embed + ~10 h media | ~2–3 days + ~5 h + ~10 h | ~1–1.5 days + ~3 h + ~5 h |
| Retrieval latency p50 | ~0.6–1.5 s (GPU contention) | ~0.4–1.0 s | ~0.3–0.7 s |

**Recommended-tier VRAM budget [estimate]:** Qwen3.8-27B FP8 28 GB + KV/state 20 GB + Qwen3-VL-Embedding-8B 16 GB + Qwen3-Reranker-4B 8 GB + Qwen3-VL-Reranker-2B 4 GB + Qwen3-ASR-1.7B and aligner ~5 GB + pyannote ~1 GB + PaddleOCR-VL-1.6 ~2 GB ≈ **84 GB of 96 GB**. Switch the LLM to W4A16 (19 GB) to free about 9 GB for more KV or concurrency.

### Cited Findings
- 2× RTX 4090 (TP2) matched a PRO 6000 at one request (94 vs 106 tok/s) but managed only 435 vs 1,342 tok/s total at 32 concurrent, prefilled about 3× slower, and topped out at a 131K window. The authors conclude that two consumer cards are "a fair trade on cost" for one user but not for multi-user or long-context serving — [ParalonCloud](https://paraloncloud.com/resources/rtx-pro-6000-vs-2x-rtx-4090-qwen3-8-27b)
- Two replicas of one model on one 96 GB card measured 234 tok/s total at C=4, trading memory for parallelism — [vllm-blackwell-guide](https://github.com/lastloop-ai/vllm-blackwell-guide)
- On dual PRO 6000 Max-Q cards (TP=2, NVFP4 + MTP), a near-single-stream agent workload averaged 161 tok/s generation and drew 281–299 W per GPU — [Loft LLC](https://loftllc.dev/en/docs/tech/llm-research/qwen3-6-27b-nvfp4-mtp-vllm-benchmark/)

### Inferences
- The **recommended tier is a single RTX PRO 6000**. It is the smallest configuration where every pipeline model is co-resident (no swapping), 32-way batching for ingest is available, and the full 262K context is usable. It ingests 10k items overnight and 100k in a long weekend.
- The jump from Recommended to Ambitious buys mainly (1) a large-MoE "second opinion" for hard change planning and the private assistant, and (2) twice the ingest rate. It does not buy better retrieval quality, which is set by the embedder, reranker and write-gate design.
- Keep hosted frontier APIs (Claude Opus/Sonnet 5.5 tier) for the owner's non-sensitive hard cases and as the golden-set judge. Route member data only through local models.

### Gaps
- None of the tier throughputs have been measured end to end. They need confirming with a brainbench ingest run on rented hardware (for example an mCloud PRO 6000 month at A$3,030) before buying.
- Power and colocation running costs aren't priced because no AU colocation tariff was found.
- Search budget ran out before I could verify Qwen3-Reranker throughput on Blackwell, AWS Sydney g7e pricing, or the October 2026 RTX 5090 AU price.
