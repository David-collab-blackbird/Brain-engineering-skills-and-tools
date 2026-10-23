---
id: DA3-security-privacy
type: blueprint
title: "DA3: Devil's-advocate review of security, privacy and partitions"
status: draft
version: 0.5
date: 2026-10-23
author_role: engineer
supersedes: []
superseded_by: null
decisions: [ADR-001, ADR-002, ADR-003, ADR-006, ADR-007, ADR-008, ADR-009, ADR-011, ADR-013, ADR-014, ADR-015, ADR-016, ADR-018, ADR-019]
tests: []
evidence: []
sensitivity: none
---

# DA3: Devil's-advocate review of security, privacy and partitions

Status: challenge v1 (2026-10-23) · Reviewer: Claude (devil's advocate, cluster 3: hostile red-teamer, sceptical privacy regulator, pragmatic operator) · Scope: ADR-002, ADR-006, ADR-007, ADR-014, ADR-015, ADR-016, ADR-018, charter principle 13, owner proposals U5 and U6, and (because it surfaced) charter §3a "Owner sees everything".
Inputs read: charter v0.5 (§2 P13, §3, §6.2, §7, §8), hypotheses board v0.6 (B3 U4–U6, D weak spots), docs02 README and the 7 cluster ADRs (plus ADR-003, 008, 011 where they touch security), `brainbench/RESULTS.md` (E4, E5), `brainbench/data/meta.json`, `research_notes/.../infrastructure_access_privacy.md`, doc 01 §6–§7. Targeted web research for counter-evidence, incidents and Australian regulatory guidance (October 2026).

**Not legal advice.** Regulatory points are the questions a regulator or lawyer would ask. Each is tagged with how firmly the source supports it.

**Evidence tags.** OBSERVED = I read the primary source or ran it. INFERRED = reasoned from evidence. UNKNOWN = searched and not found. Strength: [P] primary or official · [I] independent research · [V] vendor · [2] secondary summary · [S] search-result title only (not fetched).

**New evidence in this review.** I ran two small experiments on BrainBench v0 (CPU only, about 70–85 s each). Scripts and results are in `challenges/da3_analysis/` (`x1_noninterference.py`, `x1b_tie_check.py`, `x2_decode_topic.py`, `x1_results.json`, `x2_results.json`). They are described in §1.

---

## 0. Bottom line

### Top five objections

1. **"Local = private" is false at the moment that matters.** The GPU host keeps *ingest* onshore. But every answer the owner, a partner or staff member gets through Claude or ChatGPT carries the *most relevant, most sensitive* slice of the brain to an offshore model:
   - That is a disclosure under APP 8 for any third party's personal information in it: staff, members, partners, suppliers.
   - Anthropic's zero-data-retention (ZDR) excludes the MCP connector (doc 01 §7).
   - In one US ruling, consumer-AI conversations were treated as disclosed to a third party and discoverable ([Heppner](https://www.proskauer.com/alert/sdny-addresses-privilege-and-work-product-implications-of-using-unsecured-public-ai-tools) [2]).

   ADR-016 solves the *volume* of disclosure but leaves the *exposure* in place. ADR-002 item 7 patches only member health data. (§2 C1)
2. **The likeliest attacker holds a valid token.** A prompt-injected AI client acting for the owner is an authorised principal whose tier is "Everything". Pre-filters, per-hop checks and OAuth audiences are all correct here, and none of them help.
   - The MCP `remember` tool also lets that client write poison into the brain at the owner's trust level. ADR-014 assigns trust by *door*, not by *content lineage*.
   - Real precedents: the Slack AI exfiltration via a public-channel injection ([PromptArmor](https://promptarmor.com/resources/data-exfiltration-from-slack-ai-via-indirect-prompt-injection) [I]), and MCP tool poisoning ([Invariant](https://invariantlabs.ai/blog/whatsapp-mcp-exploited) [S]).
   - Twelve published injection defences reporting near-zero attack success fell to adaptive attacks at above 90% ([Attacker Moves Second](https://arxiv.org/abs/2510.09023) [I]).

   (§3, §6)
3. **"Zero leakage, continuously monitored" is really "zero canary returns".** In X1, an embedding basis fitted across partitions changed **84% (258/307)** of attacker top-10 lists when 20 hidden owner notes were added, and the canary monitor raised **0 alarms in 744 probes**. In X2, an attacker decoded *which* secret topic the owner had written about in **4/6** trials at M = 20 (chance 1/6, p = 0.009).
   - PostgreSQL planner statistics have bypassed access controls in three CVEs of one class: CVE-2017-7484, [CVE-2019-10130](https://www.postgresql.org/support/security/CVE-2019-10130) and [CVE-2025-8713](https://www.postgresql.org/support/security/CVE-2025-8713). The last two explicitly bypass RLS [P].
   - ADR-006's own reference implementation (visible-set statistics over postings that carry `acl_group_id`) scans hidden postings, so its latency is a side channel on exactly the quantity E4 recovered (INFERRED).

   (§1, §4, §5)
4. **The charter contradicts itself on the owner, and the benchmark encodes the wrong side.**
   - §3a says "Owner sees Everything".
   - §3c says member data is visible "only to that member and roles explicitly granted" and "never flows into owner-tier partitions without an explicit, logged, consented export".
   - `brainbench/data/meta.json` gives `owner` and `partner_gym` standing read access to **all 12 member partitions**. Every leakage test so far certifies "0 leaks" against an access matrix in which the owner reads every member's health log. No leakage test can detect a policy error.
   - In a divorce or partnership dispute, the owner is both the system operator and a party, with standing visibility of the spouse's household data and audit trail.

   (§2 C4, §12)
5. **Deletion, revocation and "consent solves it" promise more than the mechanisms can deliver.**
   - Content already delivered to a client's memory cannot be recalled.
   - Machine unlearning is unreliable: "forgotten" knowledge rose from 21% to 83% recoverable after 4-bit quantisation ([arXiv 2410.16454](https://arxiv.org/html/2410.16454v3) [I]).
   - Crypto-shredding works only per *tenant*, while erasure requests come per *person*.
   - Business records cannot be revoked by individual contributors: a former director may inspect the books for 7 years ([s198F](https://aicd.com.au/board-of-directors/duties/fiduciary/failure-to-quote-chapter-and-verse.html) [2]).
   - Victoria's Health Records Act covers **gymnasiums** regardless of size and sets retention minimums ([health.vic.gov.au](https://health.vic.gov.au/legislation/health-records-act) [P]).
   - Legal holds forbid deletion.

   (§11, §12, §9, §2 C6)

### Verdicts

| Item | Verdict | The specific change |
|---|---|---|
| ADR-002 MCP + OAuth | Keep-with-changes | Writes from third-party clients default to T3 candidates. Per-client **egress class**. Scoped owner personas, so third-party MCP never carries "owner = everything". Move to the MCP 2026-07-28 spec (CIMD, RFC 9207 `iss`, `cacheScope: private`). Hardened tokens. Minimised audit-log content with a retention period |
| ADR-006 no cross-partition statistics | Keep-with-changes (reframe) | Restate as **noninterference**, not "no fitted statistics". Add a channel inventory: planner statistics, posting-scan timing, tie-breaks, KV/prefix and semantic caches, ANN graph structure. Use per-group postings, not filtered scans. Replace the KS latency test with a test of stated power. The text-to-SQL role gets no CREATE |
| ADR-007 pre-filter, per-hop, canaries, revocation | Keep-with-changes | Make a **twin-world noninterference CI** the certification gate. Demote canaries to a production smoke alarm, never on real people. Replace the probe schedule (O(members²)) with sampled monitoring. Add a revocation epoch and a delivered-content ledger. "Revocation" covers future retrieval only |
| ADR-014 untrusted sources | Keep-with-changes | **Lineage taint** (trust = minimum over sources, whatever the door). A high-risk attribute registry needing out-of-band verification. An MCP egress firewall for T4 text. Measure retrieval poisoning and client action, not only promotion |
| ADR-015 embeddings are PI | Keep-with-changes | Widen scope to every derived and transient representation (KV/prefix caches, logs, workspaces, adapters, crash dumps). Per-subject envelope keys for the member tenant. Confirm that crypto-shredding counts as destruction or "beyond use" under APP 11.2. Inference-server hardening |
| ADR-016 local-first GPU | Keep-with-changes | Extend "local-first" to the answer path via egress classes. Host and model supply-chain baseline. Label-recall SLO for routing. Choose colo vs AU cloud (confidential computing) by ops-burden score |
| ADR-018 evaluation | Keep-with-changes | Separate the **security assurance case** (invariants, noninterference property tests, adaptive red-team rounds) from rate statistics. Add privacy drills (erasure, revocation, APP 12 export, retention). Govern evaluation on real data: only entitled auditors, member self-audit, synthetic twins |
| Principle 13 | Keep-with-changes | **Non-parametric learning first.** Retrain, never "unlearn". Lineage manifest per model. Consent gate for sensitive and member data. A membership-inference test before any model serves anyone but the owner |
| U5 behavioural data | **Rethink** (the framing) | No standing row-level analytics. A **purpose-registered aggregate gateway** (minimum cell size plus differential privacy for anything leaving operations). No stored inferred "reasons" without consent. ADM register. Member transparency page |
| U6 shared spaces | **Rethink** (partly) | Split into three constructs: entity-owned business spaces, dual-key personal spaces with a **unilateral silent safety exit**, and time-boxed professional shares. **Sealed revocation** under legal hold |
| Charter §3a "Owner: everything" | **Rethink** | Separate owner-as-person from owner-as-operator. No standing access to member health. Break-glass with notice. Household and partner personal vaults use keys the owner does not hold |

### Most promising innovation

**Twin-world noninterference CI, plus egress classes.**
- The first replaces enumerating side channels with one testable property: change only what an identity cannot see, and nothing that identity can observe may change. It caught everything the canary missed in X1, including an implementation tie-break artefact.
- The second makes "local-first" true end to end by deciding release per (item label × client egress class).

Together they turn the two biggest open holes (unknown side channels, offshore answer path) into CI checks. Details in §13.

---

## 1. New evidence: X1 and X2 (BrainBench v0, seed data, CPU)

**Setup (X1).**
- World W is the BrainBench seed. W′ is W plus M = 20 hidden owner-partition notes on a "secret" (a refinance).
- Every non-owner identity (household, three partners, 12 members) replays up to 40 of its own task queries plus 4 probes: 307 queries in total.
- All arms **pre-filter to the requester's visible rows**. The script asserts that no hidden row is ever returned.
- Observables per query: top-10 and top-50 ID lists, and score deltas on items common to both worlds.
- The canary monitor is run on W′ using E5's protocol: "anything new about <entity>?" plus the canary's unique token, from every non-entitled identity.

| Arm | Component | Attacker top-10 lists changed | top-50 changed | max \|Δscore\| | Canary alarms |
|---|---|---|---|---|---|
| A | BM25, global statistics (E4 leak) | 1/307 | 2/307 | 0.069 | **0/744** |
| B | BM25, visible-set statistics (ADR-006 reference) | **0/307** | **0/307** | **0** | 0/744 |
| C | RRF(B, LSA fitted on **all** partitions); the sandbox default | **258/307 (84%)** | 295/307 | 0.012 | **0/744** |
| D | RRF(B, LSA fitted on public rows only: a frozen-model stand-in) | 0/307 | 1/307 | 0.004 | 0/744 |

**X1b diagnosis of the single change in D.**
- BM25 scores on visible rows were identical in W and W′.
- The query ("how could we free up Kira?") had one term in the public vocabulary, so only 38 distinct LSA scores existed across 1,476 visible rows.
- `topn` uses non-stable `argpartition` over the full-length array. Which tied item it picks therefore depends on the total row count, which includes hidden rows.

So **tie-breaking is a channel**. In a real engine the analogues are row IDs, HNSW insertion order and heap position. The ADR-006 rule ("no fitted statistic") does not cover it; a noninterference test does. (OBSERVED for the sandbox; INFERRED for real engines.)

**X2: is arm C's change decodable, or just refit noise?**
- partner_cafe plants one probe note per candidate topic (refinance, divorce, sale, illness, lawsuit, hire) in its own partition, which partners may do.
- The owner adds M hidden notes on one topic.
- The attacker guesses the topic whose probe score moved most, in the direction the model family predicts.

| M hidden | A global BM25 | B visible BM25 | C LSA on all partitions | D LSA on public only |
|---|---|---|---|---|
| 5 | 6/6 | 1/6 (constant guess) | 2/6 (n.s., p = 0.26) | 1/6 (constant guess) |
| 20 | 6/6 | 1/6 | **4/6 (p = 0.009)** | 1/6 |

Arms B and D show **zero** score change, so their "1/6" is a fixed default guess, not signal.

**What this shows.**
- (a) The canary monitor (ADR-007 item 7, I11) is blind to whole classes of side channel. It fired 0 times while global BM25 (exact leak, 6/6) and a cross-partition fitted basis (decodable, 4/6) were both active.
- (b) N3, "corpus-fitted representations are side channels", now has decoding evidence for fitted embedding bases, not just a nonzero Δ. That strengthens the principle-13 restriction.
- (c) **Active probing is the threat model.** Passive replay of the attacker's normal queries showed global BM25 changing only 1/307 lists, yet planted probes decoded the topic 12/12.

**Threats to validity.**
- LSA is a weak, linear stand-in for a fine-tuned neural model.
- The hidden notes use distinctive vocabulary, and the attacker guesses within a closed set of 6 topics.
- One seed, 12 decoding trials. Directions are informative; magnitudes are not.

Real fine-tuned embedders have more capacity to memorise, so the true risk could be higher (Secret Sharer: secrets extracted from models trained without memorisation safeguards, [arXiv 1802.08232](https://arxiv.org/abs/1802.08232) [I]; LoRA membership inference AUC 0.775 under conservative fine-tuning, [LoRA-Leak](https://arxiv.org/abs/2507.18302v1) [I]).

---

## 2. Cross-cutting objections (hidden assumptions that fail across the cluster)

### C1. "Local = private": the answer path goes offshore

- **Claim in the design.** "A local GPU host removes the overseas-disclosure question for every pipeline it runs" (ADR-016; charter §6.3).
- **Attack on it.** The pipelines are not where most exposure happens. A retrieval answer *is* the sensitive subset, selected by relevance. When the owner asks Claude Desktop (consumer or Team plan) or a partner asks ChatGPT, the brain's MCP server ships the top-k items to a US-processed model.
  - Anthropic first-party inference is `us` or `global` only. ZDR excludes the MCP connector (doc 01 §7 [P]).
  - Under APP 8 and s16C, the business remains accountable for what the overseas recipient does ([OAIC APP 8](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information) [P]).
  - Over a year, the owner's questions will touch a large share of the sensitive corpus. Ingest stays local; the crown jewels leave one answer at a time.
- **Scope of the hole.** ADR-002 item 7 restricts only *health-labelled member content*. Not covered:
  - staff records;
  - partners' personal details;
  - customer names in business partitions;
  - the owner's family health data (the owner is the data subject there, but his children are not);
  - third parties named in emails.
- **Regulator's questions.**
  - What contract gives you "effective control" over the AI client vendor?
  - Did members and staff get an APP 5 notice naming the overseas recipients?
  - Did you record the APP 8 exception you rely on?
  - The OAIC's AI guidance says not to enter personal information, "particularly sensitive information", into publicly available AI chatbots ([OAIC](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products) [P]).
- **Fix.** Egress classes (innovation 2, §13), plus an "exposure accounting" metric (§8).

### C2. "Zero leakage is testable"

- **The claim.** Leakage = 0, proven by "0 in n probes" (one-sided upper bound) plus canaries.
- **Attack on it.** Three problems:
  - 0/n bounds the leak rate *of the probe generator*, not of an adaptive attacker. Defences that reported near-zero success fell above 90% to adaptive attacks, and a 500-person human red team reached 100% ([Attacker Moves Second](https://arxiv.org/abs/2510.09023); summary in [Willison](https://simonw.substack.com/p/new-prompt-injection-papers-agents) [I]).
  - Canaries detect only *returned* items (X1: 0/744 while two leaking arms ran).
  - The leakage definition in charter §3a includes "ranking, snippets, counts or 'no results' signals". Canaries test none of these.
- **Fix.** For structural controls the right evidence is an **invariant plus property-based noninterference testing over random hidden mutations** (innovation 1), and adaptive red-team rounds. Rates belong to the retrieval standard, not to security.

### C3. "Consent solves it"

- **Consent quality.** Consent under the APPs must be informed, voluntary, current and specific; it cannot be inferred from silence, and a broad privacy-policy consent is insufficient for training uses ([OAIC APP 3](https://oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information); [OAIC gen-AI](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models) [P]).
- **Power imbalance.** Members to the gym, staff to the employer, one spouse to the other. "Voluntary" is doubtful where refusal costs service or invites conflict.
- **Fatigue.** Multi-party approvals per sharing event (U6) and one-tap promotions (ADR-014) habituate. DA2 cited approval rates rising 14.5 pp with exposure. MFA-fatigue attacks exploit the same reflex (Uber 2022, [Dark Reading](https://www.darkreading.com/cyberattacks-data-breaches/uber-breach-external-contractor-mfa-bombing-attack) [S]).
- **Consent is not a defence against breach or misuse.** APP 11 security duties and the statutory tort (intentional or reckless misuse) still apply.
- **Fix.** Use consent where it is real and rare. Default to purpose limitation, minimisation and aggregates (§11). Record every consent as an ISO/IEC TS 27560 consent record ([DPV guide](https://w3c-cg.github.io/dpv/guides/consent-27560) [P]).

### C4. "Owner sees everything"

- **The contradiction.** Charter §3a vs §3c (bottom line, objection 4).
- **Concentration risk.** One owner token (or one compromised owner client, or one staff member at the always-on PC where the owner is logged in) reaches every partition: household, three businesses, every member. "Agents inherit the access of the authenticated user, never more" (§3a). For the owner that means *everything*.
- **The benchmark mirrors the bug.** `meta.json` gives owner and partner_gym every `member/*` partition (OBSERVED).
- **Legal-entity blur.** The gym, construction company and cafe are probably separate legal entities, each a potential APP entity. Points for a lawyer to confirm:
  - A gym that provides a health service and holds health information is **not** a small business operator, whatever its turnover ([s6D(4)(b)](https://20.austlii.edu.au/au/legis/cth/consol_act/pa1988108/s6d.html) [P]).
  - A business that "discloses personal information about another individual to anyone else for a benefit, service or advantage" also loses the exemption (s6D(4)(c) [P]). U5-style sharing with "stakeholders" could pull the cafe or construction company into the Act.
  - A body related to a non-small business is not a small business (s6D(9) [P]).
  - Sharing between related bodies corporate generally excludes sensitive information (s13B; INFERRED from the ALRC summary).
  - So "one brain" spans several data controllers, and the owner's personal assistant using gym-member data is a *use outside purpose* even when the owner is a director.
- **Fix.** Innovation 4: owner personas, no standing member-health access, break-glass with notice, vaults with keys the owner does not hold.

### C5. "Append-only, keep everything" (ADR-008) vs destruction duties

- **The conflict.** Keeping superseded versions, immutable audit logs and full episode history maximises recall (E1, p = 0.003). It also maximises breach impact and discovery exposure, and it collides with APP 11.2:
  - Destroy or de-identify when no longer needed.
  - Destruction applies to "copies ... held as back-ups" (para 11.39).
  - Where irretrievable destruction is impossible, information must be put "beyond use" under four conditions (para 11.52; [OAIC ch. 11](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information) [P]).
- **Reform direction.** The tranche-2 draft adds duties to map holdings and to consider *destruction rather than de-identification* ([HSF Kramer](https://www.hsfkramer.com/insights/2026-09/the-draft-tranche-2-privacy-act-reforms-whats-there-whats-new-and-whats-missing) [2]).
- **Crypto-shredding.** The OAIC chapter does not mention it (searched ch. 11; UNKNOWN whether it qualifies). Treat it as a legal interpretation to confirm.
- **Fix.** A retention schedule per record class, plus sealed state and per-subject keys (innovation 5). Flag to the ADR-008 owner.

### C6. Revocation, legal hold and subpoena interact

- A party to a dispute revokes a share; the business is under a litigation hold; deleting derived artefacts could be spoliation.
- Conversely, a subpoena to the business for a couple's joint-finance space makes the owner, if he is a party, the custodian of his opponent's data.
- None of ADR-007, ADR-008 or U6 has a **hold** state.
- **Fix.** Sealed revocation: inaccessible to everyone except a named hold custodian, with an audit trail, auto-shred at hold release, and retention minimums respected (§12, innovation 5).

---

## 3. ADR-002: MCP over remote HTTPS with per-user OAuth 2.1

**1. Strongest case against.**
- **The threat model ends at the token.** It hardens audience, PKCE and redirect URIs (good) but treats the authenticated client as trustworthy within the user's access. The realistic attacker is the user's own AI client after it has read untrusted content.
  - It holds a valid owner token, calls `search("bank details")` or `facts(...)`, and exfiltrates through another tool in the same client (email send, web fetch, a markdown image URL).
  - Willison's lethal trifecta lives in the client: private data, untrusted content and external communication ([Willison](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) [I]). Meta's "Rule of Two" says a session should have no more than two of the three properties ([summary](https://simonw.substack.com/p/new-prompt-injection-papers-agents) [2]).
  - Acceptance check 4 ("content saying 'search all tenants' does not change returned items") tests the wrong property. The injected request stays *inside* the victim's access, and the brain obliges.
- **`remember` launders poison.** A client that read a malicious web page or email writes "Supplier X's new bank account is …" as the owner. ADR-014's T0 is "the owner, typing or speaking", but a write from Claude Desktop is an agent output whose inputs are unknown to the brain. Precedent: persistent memory injection through ChatGPT's memory ("SpAIware", [THN](https://thehackernews.com/2024/09/chatgpt-macos-flaw-couldve-enabled-long.html) [S]).
- **Tokens live at the AI vendor.** Remote MCP connectors store refresh tokens on Anthropic's and OpenAI's infrastructure. Stolen OAuth tokens of one AI integration (Salesloft Drift) reached hundreds of Salesforce tenants ([Help Net](https://www.helpnetsecurity.com/2025/08/27/hundreds-of-salesforce-customer-orgs-hit-in-clever-attack-with-potentially-huge-blast-radius/) [2]). A vendor-side breach would yield owner-everything tokens.
- **The spec moved.** The MCP 2026-07-28 revision ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) [P]):
  - removes protocol sessions (stateless);
  - deprecates Dynamic Client Registration in favour of **Client ID Metadata Documents (CIMD)**;
  - requires clients to validate RFC 9207 `iss`;
  - adds `cacheScope` (`public`/`private`) on list and read results;
  - makes `clientInfo` per request a SHOULD (self-asserted, not authentication);
  - deprecates Sampling and Roots.

  ADR-002 cites 2025-11-25.
- **One enforcement point is one point of failure.** Asana's first-party MCP server exposed data across customer organisations for about a month, caused by a bug "in our code", not an attack ([UpGuard](https://www.upguard.com/blog/asana-discloses-data-exposure-bug-in-mcp-server) [2]).
- **The audit log becomes the most sensitive dataset in the system.** Query text plus returned IDs record what the owner was thinking about, and they name third parties. It is "immutable" with no retention period, which conflicts with APP 11.2 and makes it a prime subpoena target.

**2. Attack scenarios.**
- (a) Injected email in the owner's mail MCP: the client calls brain `search` for "account numbers", then renders a link with the data in query parameters.
- (b) Vendor token theft yields owner scope: the full brain is reachable at API speed.
- (c) A staff member at the always-on PC uses the owner's logged-in assistant.
- (d) A malicious member uses ChatGPT to probe counts and "no results" differences (ADR-006).
- (e) Divorce: the spouse's household token keeps working until someone revokes it, and her ChatGPT memory retains months of brain content.
- (f) Subpoena of the audit log: every question the owner asked, with third-party names.

**3. Regulatory risk.**
- APP 8 for all third-party personal information returned to offshore clients (C1).
- APP 11: are refresh tokens held offshore "reasonable steps"?
- NDB: a stolen owner-scope token is very likely an eligible breach. Notification is "as soon as practicable", and the assessment window is 30 days ([OAIC](https://www.oaic.gov.au/privacy/notifiable-data-breaches/quick-reference-guide-for-responding-to-data-breaches) [P]). The tranche-2 draft proposes 72 hours to the OAIC.
- APP 1.2: a documented privacy risk assessment before launch. The Tribunal upheld this finding against Bunnings even while overturning the APP 3 finding ([Clayton Utz](https://www.claytonutz.com/insights/2026/february/bunnings-wins-appeal-on-facial-recognition-technology-key-takeaways-for-businesses-and-privacy-law) [2]).

**4. Operational burden.**
- An authorisation server (Australian, or identity-only), a client registry (CIMD URLs), token revocation tooling, anomaly alerts. Someone must respond at 2 am.
- Essential Eight ML1 requires MFA for online services handling sensitive data, and patches within 48 hours for critical or exploited vulnerabilities in online services ([ASD](https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/essential-eight/essential-eight-maturity-model-and-ism-mapping) [P]).

**5. Alternatives and bolder ideas.**

| Option | What it is | Wins when | Loses when |
|---|---|---|---|
| **Egress classes per client** (innovation 2) | Each OAuth client ID (CIMD-verified) gets an egress class. Each item label × class → release / pseudonymise / withhold | Always, for any client that is not onshore-controlled | Needs accurate labels (label-recall SLO) |
| **Owner personas / scoped connectors** | `owner@finance`, `owner@gym-ops`, …, each a separate OAuth client grant capped at a scope set. Owner-everything only in the first-party UI with step-up | Shrinks the blast radius of a compromised client or token by roughly 1/number of personas | Cross-domain questions need a first-party UI or an explicit multi-persona grant |
| **Third-party MCP read-only by default** | `remember` from third-party clients writes T3 candidates. Promotion in the first-party UI | Closes the laundering path | Slows owner capture; mitigate with auto-promotion for low-risk types |
| **Read budgets and step-up** | Per-token caps (items/hour, distinct sensitive items/day). Bulk or sensitive reads trigger phone approval | Makes exfiltration slow and noisy | Approval fatigue; keep thresholds high |
| **Exfiltration honeytokens** | Plant credential-like and URL honeytokens (canarytoken-style) in owner partitions. Any external use of them pages the owner | Detects a compromised *client*, which leakage canaries never see | Detects only after the fact |
| **Sender-constrained tokens** | DPoP ([RFC 9449](https://www.rfc-editor.org/rfc/rfc9449) [P]) where clients support it. Otherwise short access TTL (≤1 h) with rotating refresh | Limits stolen-token replay | Major AI clients may not support DPoP (UNKNOWN) |

**6. Verdict: Keep-with-changes.**
1. Default T3 for third-party-client writes.
2. Egress classes.
3. Scoped personas: no owner-everything over third-party MCP.
4. Adopt the 2026-07-28 spec: CIMD, `iss`, `cacheScope: private` on every result (including the scope-index resource), no reliance on `clientInfo`.
5. Token hardening and read budgets.
6. Audit log stores principal, client, item IDs and a query hash. Query text is encrypted under a separate key and expires after a set period, with legal-hold override.

**7. Decisive test and kill criterion: S1, the confused-deputy harness.**
- **Setup.** A client harness with three MCP servers: an injected mail inbox, the brain and an outbound fetch tool. 300 MemGhost and Slack-AI-style payloads. Run against owner-everything, persona and egress-class configurations.
- **Measure:**
  - sensitive items exfiltrated per run;
  - poisoned writes that become active or reach cards;
  - legitimate-write latency.
- **Kill / redesign** if any of these hold:
  - with personas plus egress classes, any health- or finance-sensitive item reaches the outbound tool through a consumer-class client in >0 of 300 runs (upper bound ≤1%);
  - T3-default writes leave >20% of legitimate owner captures unpromoted after 24 h (then auto-promote low-risk types).

---

## 4. ADR-006: no statistic fitted across partitions

**1. Strongest case against.** The principle is right but framed too narrowly. It forbids *fitted statistics* and lists the ones known today. Leaks also come from shared *state* and *implementation*:
- **Planner statistics.** PostgreSQL's planner exposed sampled values of protected rows in three CVEs of one class (the 2025 advisory calls the first two incomplete fixes):
  - CVE-2017-7484 (permissions);
  - [CVE-2019-10130](https://www.postgresql.org/support/security/CVE-2019-10130);
  - [CVE-2025-8713](https://www.postgresql.org/support/security/CVE-2025-8713), fixed in 17.6 on 2025-08-14, which covers partitioning and inheritance hierarchies [P].
  - Each required a user who can create a "leaky" operator. ADR-013's text-to-SQL route makes the brain *generate* SQL from user requests. If its role can CREATE, the class becomes reachable by prompt (INFERRED).
  - A separate flaw applied the wrong role's policy when a plan was reused across `SET ROLE` ([CVE-2024-10976](https://www.postgresql.org/support/security/CVE-2024-10976) [P]).
  - Referential-integrity checks (unique, FK) always bypass RLS and are documented "covert channels" ([PG docs](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) [P]). A uniqueness error on an alias or `supersession_key` reveals a hidden row's existence.
- **Posting-scan timing.** Option (a), "per request over the visible set, cheap if postings carry `acl_group_id`", scans *all* postings of a term and filters them. Latency then scales with the total document frequency including hidden rows. That is exactly E4's quantity, moved from the score to the clock (INFERRED; not measured).
  - Item 8 ("exact scans over the permitted set satisfy timing by construction") is true only if storage is *physically* per group.
  - Acceptance check 2 (KS p > 0.01 over 1,000 trials) has unstated power. An attacker who averages 10⁵ queries detects far smaller shifts than a 1,000-trial KS test can.
- **Tie-breaks and ordering.** X1b: the only change in the "clean" arm came from tie selection that depends on total row count. Analogues include heap order, row IDs and ANN graph structure built over all partitions.
- **LLM serving caches.** Prefix-cache timing in vLLM, SGLang and TGI leaks other tenants' templated prompts:
  - PROMPTPEEK reports 99–100% attack success on SGLang ([NDSS](https://ndss-symposium.org/ndss-paper/i-know-what-you-asked-prompt-leakage-via-kv-cache-sharing-in-multi-tenant-llm-serving) [I]).
  - InputSnatch-style field extraction reaches 62% for disease fields under realistic limits; cached vs cold time-to-first-token on vLLM 0.26 was 32.8 ms vs 149.6 ms ([arXiv 2608.09225](https://arxiv.org/pdf/2608.09225) [I, single-author preprint]).
  - vLLM supports a per-request `cache_salt` "to prevent timing-based attacks" ([vLLM docs](https://docs.vllm.ai/en/stable/design/v1/prefix_caching.html) [P]).
  - The brain's local LLM (path B, scribe, query rewrite) will serve several principals from one cache.
- **Fitted models.** X1/X2: a basis fitted across partitions changed 84% of attacker lists and leaked a decodable topic. Item 5 already bans this. The evidence now supports the ban rather than extrapolating it.

**2. Attack scenarios.**
- A partner plants probe notes to track the owner's activity on "sale", "illness" or "divorce" (X2).
- A member times "no results" responses for a rival's name.
- A text-to-SQL prompt induces a CREATE FUNCTION.
- A uniqueness collision when a partner adds an alias already used in an owner partition.
- Prefix-cache timing on the shared local LLM recovers another user's templated extraction prompt (member name plus injury field).

**3. Regulatory risk.**
- A side-channel inference of a secret (illness, separation plans) by a partner is an unauthorised disclosure in substance (APP 6, APP 11).
- A regulator would ask how you would ever *detect* it, since NDB assessment needs awareness.
- If a partner exploits it deliberately, the statutory tort's misuse limb applies to the partner. The business's exposure is APP 11.

**4. Operational burden.**
- Per-group physical indexes multiply storage and maintenance.
- Postgres minor-version patching within Essential Eight windows.
- vLLM cache-salt plumbing.
- A noninterference CI job (cheap on synthetic twins).

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| Noninterference oracle (innovation 1) in place of a channel list | Always. Catches unknown channels like the X1b tie-break | Cannot test production-only effects (real timing) without a powered timing harness |
| Per-ACL-group physical postings and vectors; multi-group merge by RRF (ADR-006 option b) | Kills scan-timing and planner-statistics channels by construction | Up to G× index copies for owner requests (G = groups); test latency in E12 |
| Constant-work scans (pad to fixed work per term) | Small corpora | Wasteful at 100k+ |
| App and text-to-SQL roles: no CREATE on any schema, no direct SQL, AST-whitelisted views; `ANALYZE` stats only on non-retrievable tables or behind `leakproof` operators | Closes the CVE class even before patches | Restricts aggregation expressiveness |
| `cache_salt` = HMAC(principal) on every LLM request; no semantic caches | Closes the KV/prefix channel at roughly a cache-hit-rate cost | Boundary salting (keeps about 92.8% of the benefit) is not yet available (paper, extrapolated) |

**6. Verdict: Keep-with-changes (reframe).**
- New wording: "Any change confined to rows a principal cannot see must leave every observable of that principal unchanged: IDs, order, scores and bands, counts, snippets, errors, and the latency distribution at the stated test power."
- Keep the fitted-component inventory and add a **channel inventory**:
  - planner statistics;
  - integrity-constraint errors;
  - posting-scan timing;
  - tie-break order;
  - KV/prefix and semantic caches;
  - ANN graph build;
  - GPU memory (LeftoverLocals did not affect NVIDIA, [Trail of Bits](https://blog.trailofbits.com/2024/01/16/leftoverlocals-listening-to-llm-responses-through-leaked-gpu-local-memory/) [I], but re-check for any non-NVIDIA accelerator).
- Choose option (b), per-group postings, unless E12 shows (a) passes a powered timing test.

**7. Decisive test and kill: S2, the twin-world noninterference suite.**
- **Setup.** X1 generalised. For every non-owner identity, generate W′ by random hidden mutations: insert, edit, delete or revoke 1–50 rows, including rows that collide on aliases and keys. Replay 1,000 queries plus adversarial probes.
- **Requirements:**
  - identical outputs and error codes;
  - for timing, a two-sample test powered to detect a 1% median shift at α = 0.01 (state the sample size), run co-located.
- **Kill criterion (for a component, not the principle).** A component that cannot pass without more than 2× p95 latency is restricted to single-group use.

---

## 5. ADR-007: access pre-filter, per-hop checks, fail-closed, canaries, revocation SLA

**1. Strongest case against.**
- **Canaries measure the wrong thing as a certification.** X1: 0/744 alarms while two leaking arms ran. E5's "never fired in a safe configuration" is true but says nothing about unsafe configurations of the side-channel kind. Canaries are a *smoke alarm* for return-path bugs, not evidence of zero.
- **Canaries in production are fabricated personal information about real people.** BrainBench canaries read "internal note regarding Hugo Brennan, Jordan Pike", anchored to real members and staff so that bridges leak them (OBSERVED in `items.jsonl`). In production that is a false record about a real, identifiable individual.
  - It is personal information "whether or not it is true" ([OAIC](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models) [P]).
  - That raises APP 10 (accuracy) and APP 12 problems: does a member's access request return it?
  - Canaries also occupy k for entitled users unless special-cased. A special case (`is_canary`) creates a path a leak could also take, silently skipping the very items meant to reveal it.
- **The probe schedule does not scale.** At ≥1 probe per (non-entitled identity, partition) pair per hour, a member tenant of M members has M(M−1) pairs:
  - M = 500 → 249,500 full retrievals/hour, about 69/s;
  - M = 2,000 → about 4.0M/hour, about 1,111/s, times every door.

  Sampled monitoring is mandatory. If a bug affects a fraction f of pairs, s random probes per hour detect it with probability 1 − (1 − f)^s: f = 1%, s = 300 → 95% per hour.
- **Revocation covers future retrieval only.** Content already delivered to a client (ChatGPT memory, Claude Projects, exported notes, screenshots) is outside the brain. "Invisible in every channel within 15 min" overstates. In partnership dissolution or separation (U6), months of brain-derived context remain in the ex-party's assistant.
- **Time-of-check vs time-of-use.** The visible set is resolved "once per request". Aggregation and RLM workspaces (ADR-013) may run for minutes, and a revocation mid-run is not honoured.
- **Derived-artefact intersection is correct, but it multiplies cards.** In the owner tier (sees all), cards fuse member health with household and business data. Through C4, the "correct" intersection for the owner is the leak.

**2. Attack scenarios.**
- An insider who knows the canary format filters canaries out of exfiltrated data.
- A revoked partner keeps querying a cached packet during an aggregation job.
- A malicious member is a probe target at scale: with 500 members, hourly per-pair probing is impossible, so leaks between members go unmonitored.
- After dissolution, the ex-partner's client memory still answers questions about the business.

**3. Regulatory risk.**
- APP 10 and APP 12 for canaries on real people.
- APP 11 "reasonable steps" for detection. A regulator will ask what the monitor *cannot* see.
- For dissolution: can you show the OAIC or a court exactly what was delivered to whom? The audit log supports this only if it records delivered *content versions*, not just IDs.

**4. Operational burden.**
- Canary maintenance, alert triage, sampling design.
- A revocation runbook per connector.

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| **Shadow-twin monitoring**: run canaries and noninterference on a synthetic replica with the same topology, code and configuration | Always for CI and certification. No fabricated records on real people | Misses data-dependent production bugs; keep a few production canaries on *synthetic entities only* |
| **Production canaries on synthetic, non-person entities** (fictional supplier, fictional property) anchored by edges to real shared entities | Smoke alarm for return-path bugs | Weaker bridge coverage than person-anchored canaries |
| **Revocation epoch**: every long job re-checks a monotonically increasing epoch at each batch boundary and aborts on change | Closes the time-of-check gap | Slightly more DB load |
| **Delivered-content ledger**: per response, item IDs plus content version hashes plus egress class | Dissolution, NDB scoping, subpoena response | Sensitive itself; same retention rules as the audit log |
| **Per-recipient fingerprints (traitor tracing)**: tiny per-principal paraphrase variants or honeytoken facts in delivered packets | Tracing leaked screenshots or exports to a recipient | Imperfect; affects answer text |

**6. Verdict: Keep-with-changes.**
- Pre-filter, per-hop checks, fail-closed and derived intersection stay unchanged.
- Certification evidence moves from canary rates to S2 noninterference plus adaptive red-team rounds (§9).
- Canaries: shadow twin for CI; production canaries only on synthetic entities; sampled schedule with stated detection probability.
- Add the revocation epoch and the delivered-content ledger.
- Reword the SLA as "future retrieval invisible within …".

**7. Decisive test and kill: S3, the monitor sensitivity matrix.**
- **Setup.** Inject 10 bug classes into a test build:
  1. seed-only hop;
  2. global IDF;
  3. cache keyed on query text;
  4. snippet from a hidden source;
  5. count before filter;
  6. tie-break by global row order;
  7. stale revocation cache;
  8. derived-card widening;
  9. shared KV cache across principals;
  10. semantic cache.
- **Measure** detection by (a) the canary monitor and (b) S2.
- **Kill.** If canaries detect <50% of classes, they are formally demoted from "hard-constraint evidence" in charter §8. X1 already shows 0/2 for classes 2 and a fitted-model analogue.

---

## 6. ADR-014: untrusted sources, provenance and quarantine

**1. Strongest case against.**
- **Trust is assigned by door, not by content lineage.** Most poison arrives through a trusted door:
  - the owner forwards a supplier's "new bank details" email;
  - he dictates what a caller said;
  - he pastes a WhatsApp message;
  - his AI client, having read a malicious page, calls `remember`.

  Each is T0 or T1 by door and T4 by content. Payment-redirection scams cost Australians A$166.8M in 2025 (NASC data via [Eftsure](https://www.eftsure.com/blog/industry-news/$167m-lost-in-2025-why-bec-scams-keep-costing-australians/) [2]). This exact attack class targets a multi-business owner with suppliers.
- **Corroboration is gameable.** Rule (b), "a T0–T2 source matching the same key and value", is satisfied by an attacker who sends the same false value through two channels, or by the owner re-stating what the email said. Corroboration must come from an *independent* channel: a callback to a number on file, or a value in the accounting system of record.
- **Members are T1**, so attacker-controlled text inside their own partition is trusted. That is fine for their own partition. But any member text that flows into gym-side artefacts (coach notes, U5 analytics, aggregate cards) is externally authored.
- **The brain becomes stored-XSS for AI clients.** ADR-014 protects the brain's *memory integrity*: no promotion without a trusted act. But T4 text is still retrievable "as quoted source content, labelled unverified", and it is returned months later to the owner's client, which has tools. The label is a prompt-level signal.
  - Spotlighting cut attack success from above 50% to below 2% on GPT models ([Microsoft](https://arxiv.org/abs/2403.14720) [I]), but adaptive attacks bypass most such defences (C2).
  - Slack AI showed retrieval plus a rendered link is enough to exfiltrate.
- **Retrieval poisoning needs no promotion.** PoisonedRAG reached about 90% success with 5 planted texts (doc 01). The scribe's searchable entry (ADR-011) may index the attacker's chosen vocabulary from a T4 email, making it rank for "Talbot bank account". The client then reads "unverified" text and acts on it.
- **Derived text inherits ACL but not trust.** Contextual headers, captions and summaries built by a reader from T4 content are tagged T3 ("agent-inferred from T0–T2") unless lineage taint is explicit.
- **The measurement is too narrow.** "Served as trusted memory ≤1%" ignores (i) attacker text in top-k for a targeted query and (ii) the client *acting* on it.

**2. Attack scenarios.**
- **Invoice redirection:** the supplier's mailbox is compromised; the owner forwards the email; the AI client calls `remember`; a card shows the new BSB.
- **Approval-flood attack:** 30 benign candidates, then one malicious one, approved by habit.
- **Member injection:** a member writes instructions into their training notes; the coach's AI assistant reads the member record and exfiltrates other members' data through the coach's tools.

**3. Regulatory risk.**
- APP 10 (accuracy) and APP 11 (unauthorised modification).
- Health-safety risk if a poisoned injury or medical record drives a training plan.
- If any poisoned value drives a member-affecting decision by program (pricing, eligibility), it falls under ADM disclosure from 10 Dec 2026 ([Corrs](https://corrs.com.au/insights/automated-decision-making-preparing-for-the-new-transparency-obligation) [2]).

**4. Operational burden.**
- Review queue (shared with ADR-009 and ADR-011).
- Corroboration rules.
- Out-of-band verification workflow for high-risk changes, which is a phone call.

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| **Lineage taint** (innovation 3): trust = min over content lineage; forwarded or pasted content keeps T4; MCP third-party-client writes are T3 | Always | Requires span-level provenance at ingest (ADR-011 already keeps source spans) |
| **High-risk attribute registry**: payee and bank details, addresses for delivery or refund, emails used for password reset, medical flags. Change needs out-of-band verification whatever the trust level | Payment redirection, account takeover | A little friction on rare changes |
| **MCP egress firewall for T4**: never return URLs, markdown images, HTML or imperative sentences from T4; return a quarantined *handle* and a neutral summary; full text only via explicit `fetch` with a warning frame | Cuts the client-side exfiltration path | Some legitimate uses (a link in a supplier email) need one extra step |
| **Dual-LLM / CaMeL** for any brain pipeline that reads T4 *and* has tool or write access. CaMeL solved 77% of AgentDojo tasks with provable security vs 84% undefended ([arXiv](https://arxiv.org/abs/2503.18813) [I]) | Future agentic brain features | Extra engineering; ADR-001 already forbids agent loops, so it is rarely needed |
| Exclude T4 from default retrieval; opt in per request | If retrieval-poisoning success stays >5% | Loses email recall |

**6. Verdict: Keep-with-changes.**
- Add lineage taint, the high-risk attribute registry, independent-channel corroboration and the MCP egress firewall.
- Widen the H18 metric to three outcomes: promoted; in top-k for a targeted query; client action in a harness.

**7. Decisive test and kill: S4, extending H18.**
- **Arms:** three attack paths (direct T4 ingest; laundered through owner forward or MCP `remember`; retrieval poisoning aimed at a named query) × the three outcomes above. At least 299 payloads per path.
- **Kill / redesign** if any of these hold:
  - laundered-path promotion >1% with taint on;
  - targeted top-k inclusion >5% (then T4 leaves default retrieval);
  - client action >0 of 299 with the egress firewall in the S1 harness.

---

## 7. ADR-015: embeddings are personal information

**1. Strongest case against.**
- **Right premise, wrong perimeter.** Vectors are plaintext-equivalent (ZSInvert 82–92%, Vec2Text 89% of names; doc 01). But per-tenant encryption *at rest* protects against disk and backup theft, and the likeliest compromise is the *running* server, where keys and plaintext are in memory:
  - 175,000 publicly reachable Ollama hosts and 12,269 with no authentication;
  - Ollama CVE-2026-7482 heap leak (CVSS 9.1) exposing prompts and keys ([CSA](https://labs.cloudsecurityalliance.org/research-rb/csa-research-note-self-hosted-ai-infrastructure-exposure-202/) [2]);
  - NVIDIA Container Toolkit escape to host root from a three-line Dockerfile ([CVE-2025-23266](https://wiz.io/blog/nvidia-ai-vulnerability-cve-2025-23266-nvidiascape) [V]);
  - 100+ malicious models on Hugging Face ([THN](https://thehackernews.com/2024/03/over-100-malicious-aiml-models-found-on.html) [S]).
- **More personal information lives outside the vector table than in it.** KV and prefix caches, LLM request logs, RLM workspaces, crash dumps, swap, audit-log query text, eval sets, adapters. ADR-015 lists caches and adapters for label inheritance but specifies no mechanism.
- **Crypto-shredding is per tenant; erasure is per person.** The owner tenant holds many people's data (staff, partners, children, suppliers), and member erasure requests come one member at a time. A tenant key cannot shred one person. Backups keep the person readable under the tenant key.
- **Postgres has no upstream TDE.** Per-tablespace keys mean Percona's `pg_tde`, which "requires its patches" and ships with Percona Distribution 17+ ([docs](https://docs.percona.com/pg-tde/) [V]). That is a distribution lock-in decision hidden inside a privacy ADR.
- **APP 11.2 does not mention crypto-shredding.** Searched ch. 11: destruction means "can no longer be retrieved", including backups (UNKNOWN whether key destruction qualifies).
- **"Sensitive categories off by default" contradicts the gym's core data.** Health is the product. Opt-in per item is unworkable consent UX.

**2. Attack scenarios.**
- A container escape via a poisoned model image dumps decrypted vectors and the KV cache.
- Backup theft from off-site storage: tenant key in the same cloud account.
- Weight exfiltration of a fine-tuned adapter, which is data by principle 13.
- Infostealer on the owner's always-on PC reads local caches, cf. Windows Recall snapshots grabbed by "TotalRecall" ([Malwarebytes](https://www.malwarebytes.com/blog/news/2024/06/microsoft-recall-snapshots-can-be-easily-grabbed-with-totalrecall-tool) [S]).

**3. Regulatory risk.**
- APP 11.1 security of all holdings.
- APP 11.2 destruction across backups.
- NDB: whether "encrypted data stolen, key safe" counts as remedial action that avoids serious harm turns on key custody.
- Victoria HPP retention for health information (§11) may *forbid* shredding a member's health data on request.

**4. Operational burden.**
- KMS or HSM in Australia (AWS KMS Sydney is simplest), key rotation, backup re-encryption.
- A per-subject key hierarchy (if adopted).
- An inference-server hardening baseline and patch cadence.

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| **Per-subject envelope keys** (innovation 5): each member's rows encrypted with a member DEK wrapped by the tenant KEK; shredding the DEK erases the member, backups included | Member tenant (clean per-person partitions). Exact search over a member's own set is tiny, so decrypting per request is cheap | Owner tenant, where items mix several people; use per-item keys for sensitive items only |
| **Confidential computing on the GPU host**: H100 CC overhead mostly <5%, about 7% worst case on an 8B model ([arXiv 2409.03992](https://arxiv.org/html/2409.03992v2) [I]) | AU cloud GPU: protects against the cloud operator and co-tenants | Owned hardware with physical access: TEE.fail breaks TDX, SEV-SNP and NVIDIA CC attestation with a <$1k DDR5 interposer, and vendors call physical attacks out of scope ([THN](https://thehackernews.com/2025/10/new-teefail-side-channel-attack.html) [2]) |
| `cache_salt` = HMAC(principal); no semantic caches; no persistent request logs on the GPU host; tmpfs plus no swap | Always | Small throughput cost |
| Model supply chain: safetensors only, no `trust_remote_code`, hash-pinned weights, offline model mirror | Always | Slower model adoption |

**6. Verdict: Keep-with-changes.**
- Retitle: "Derived and transient representations are personal information".
- Per-subject keys for the member tenant.
- Legal confirmation of crypto-shredding vs "beyond use".
- An explicit hardening baseline:
  - inference behind an authenticating proxy;
  - bind to localhost or private interfaces;
  - Essential Eight patch windows;
  - pinned and patched vLLM, Ollama and container toolkit.
- Choose the Postgres distribution (Percona `pg_tde`) or volume-level encryption per tenant explicitly in ADR-003.

**7. Decisive test and kill: S5, the erasure drill (with H22).**
- **Setup.** Erase member X, then verify:
  - (a) no live retrieval through any door;
  - (b) restoring the last 35 days of backups yields no readable X content;
  - (c) no X in KV or semantic caches, request logs, audit-log query text, RLM workspaces or eval sets;
  - (d) the APP 12 export before erasure was complete.
- **Kill.** If per-subject DEKs raise member-request p95 by more than 2×, fall back to per-tenant keys plus scheduled backup re-write.

---

## 8. ADR-016: local-first GPU hosting (owner-confirmed)

**1. Strongest case against.**
- **C1 (answer path offshore).**
- **A single self-managed GPU box is a soft, high-value target.**
  - Exposed AI infrastructure is endemic, with about 35,000 attack sessions against exposed AI endpoints over December 2025 to January 2026 ([CSA](https://labs.cloudsecurityalliance.org/research-rb/csa-research-note-self-hosted-ai-infrastructure-exposure-202/) [2]).
  - Small businesses patch slowly, and the host runs a deep, fast-moving stack: kernel, NVIDIA driver, CUDA, container toolkit, vLLM, model weights from the internet.
  - The host also holds decryption keys in memory and, under principle 13, sensitive adapters.
- **Label-routed hosting is only as good as label recall.** Hosted APIs are allowed for owner, household and partner partitions, but a biz/gym incident log mentioning a member's knee injury is health information in a partner partition. If the labeller misses it, it goes to a hosted API. No SLO is set for sensitivity-detection recall.
- **Location options trade different risks:**
  - home or office: staff and physical access, burglary, power;
  - colo: colo staff, physical attacks (TEE.fail);
  - AU cloud GPU: shared responsibility and operator access (mitigated by CC), uncertain capacity in Sydney (W2: unchecked).
- **"Hosted where clearly better" will drift.** Every quality gap pushes another pipeline offshore. There is no budget or ceiling on hosted exposure.

**2. Attack scenarios.**
- An internet-exposed vLLM port.
- A malicious model or container image.
- Physical theft of the box (keys on disk?).
- A mislabelled health item routed to a hosted API.
- A staff member with physical access to the office server.

**3. Regulatory risk.**
- APP 11 reasonable steps: is a self-managed GPU host with no 24/7 monitoring "reasonable" for health information?
- APP 8 via label errors.
- Doc 01 notes partner partitions contain staff and customer personal information: legal review required.
- The NDB scheme makes small health-adjacent breaches reportable. Health providers were the top NDB sector in 2025, 225 of 1,205 ([OAIC](https://www.oaic.gov.au/news/media-centre/data-breach-notifications-increase-to-all-time-high-in-2025,-new-ndb-stats-show) [P]).

**4. Operational burden (INFERRED estimate).**
- Weekly patch review, monthly driver and stack updates, quarterly restore drills, alert response.
- Roughly 4–8 h/month of competent operations, or a managed service contract.
- The owner's current build stalled for lack of builder capacity (ADR-019); operations capacity is the same scarce resource.

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| **AU cloud GPU with confidential computing** | Ops burden of the hardware layer; protection against the operator; easier off-site backups | Capacity and price in Sydney/Melbourne (W2) |
| **Egress classes on the answer path** (innovation 2), with an onshore default assistant (first-party UI backed by Bedrock AU) for sensitive classes | Makes local-first true end to end | Users who insist on ChatGPT get pseudonymised or withheld content |
| **Pseudonymisation at egress** for consumer clients: stable tokens for third-party names, rehydrated in the first-party UI only | Third-party personal information in owner questions | The client cannot reason about the real-world identity; fine for most analysis |
| **Hosted-exposure budget**: cap on items/month and distinct individuals/month leaving through hosted pipelines, reported monthly | Prevents drift | Needs instrumentation |

**6. Verdict: Keep-with-changes.**
- Keep local embedding and reranking (sound).
- Add egress classes, label-recall SLO (sensitive-detection recall ≥99% on a gold set, or route conservatively), host and supply-chain baseline, hosted-exposure budget.
- Choose the location by an ops-burden score, not cost alone.

**7. Decisive test and kill: S6, exposure accounting.**
- **Setup.** Replay a simulated month of owner, partner and staff queries through each door.
- **Measure:**
  - share of sensitive-labelled items, and distinct third-party individuals, that leave Australia through (a) internal pipelines and (b) client answers;
  - label recall on a seeded "hidden health in business partition" set.
- **Kill.** If (b) exceeds 10% of sensitive items per month, the claim "local-first removes the overseas-disclosure question" is withdrawn from charter §6.3, and egress classes become mandatory.

---

## 9. ADR-018: evaluation and certification (security and privacy aspects)

**1. Strongest case against.**
- **One-sided bounds on hard constraints assume i.i.d. probes from a fixed generator** (C2). Structural controls deserve *assurance*: invariants, static checks, noninterference property tests. Adaptive red-team rounds measure the rest.
- **The certification standard has no privacy metrics.** None of these is measured:
  - egress exposure;
  - purpose compliance;
  - retention compliance;
  - erasure completeness;
  - consent-revocation propagation;
  - APP 12 export completeness;
  - ADM register coverage.

  A system could certify at 90% CR with zero leakage and still breach APP 6, APP 8 and APP 11.2 daily.
- **Evaluation on real data is itself a privacy event.**
  - Production coverage sampling (I4) and the three-group audit put humans in front of real requests and random never-retrieved private items.
  - Using personal information for evaluation is a use (APP 6).
  - An auditor reviewing member requests sees member health data, which conflicts with §3c.
  - LLM judges on real data, if hosted, are APP 8 events.
- **Red-team sets go stale.** The certification set is protected from tuning code but not from attackers who study the live system.

**2. Attack scenarios.**
- An attacker designs probes outside the red-team generator's distribution.
- A labelling contractor exfiltrates real items from the audit queue.

**3. Regulatory risk.**
- APP 6 for evaluation uses.
- APP 1.2 for documented risk assessment.
- APP 8 for hosted judges.

**4. Operational burden.**
- Adaptive red-team rounds (internal Claude agent plus a paid human round before member go-live).
- Privacy drills quarterly.

**5. Alternatives.**
- **Assurance case** in three parts: (i) invariants checked statically (`VisibleSet` argument lint, no-CREATE lint); (ii) S2 property tests; (iii) adaptive red-team rounds with the design docs disclosed (Kerckhoffs' principle) and a query budget.
- **Privacy drill suite:** S5 erasure; S8 revocation and dissolution; APP 12 export diff; retention sweep; ADM register check.
- **Evaluation governance:**
  - member data audited only by the member (self-audit prompts: "was this what you needed?") or on synthetic twins;
  - owner-tier data audited by the owner;
  - judges local only for sensitive labels.

**6. Verdict: Keep-with-changes.** Keep the CR certification unchanged; add the assurance case and privacy drills as separate gates.

**7. Decisive test and kill: S7, an adaptive red-team round.**
- **Setup.** Red team (Claude agent plus at least one human) with the full design docs and 10k queries per identity.
- **Success** = any S2 violation, hidden content, or poisoned promotion.
- **Kill.** If the round finds any leak class missing from the static suite, withdraw the "≤1%" wording from docs until the suite is extended and re-run.

---

## 10. Principle 13: models trained on brain data inherit access labels

**1. Strongest case against.**
- **The rule is correct and guts the benefit.** A model trained on owner-tier data may serve only the owner. Per-partition adapters face tiny data: partner_cafe has about 1.2k items in BrainBench. ADR-006 already expects only +1–2 pp from fine-tuning. Expected value: small gain, for one user, at large compliance cost.
- **"Honour deletion by retraining or dropping the adapter" is the only honest option**, because unlearning fails:
  - 21% of "forgotten" knowledge was retained in full precision and 83% after 4-bit quantisation ([arXiv 2410.16454](https://arxiv.org/html/2410.16454v3) [I]);
  - LoRA models stay vulnerable to membership inference, AUC 0.775 ([LoRA-Leak](https://arxiv.org/abs/2507.18302v1) [I]).

  Retraining needs a training-set lineage manifest and a retrain pipeline per deletion. For owner-tier models trained on staff and partner messages, every staff deletion means a retrain. Sharded training (SISA, [arXiv 1912.03817](https://arxiv.org/abs/1912.03817) [I]) bounds the cost.
- **Purpose (APP 6).** OAIC guidance:
  - training on held personal information needs consent or a reasonable expectation;
  - "should not rely on a broad consent";
  - "seek consent ... and/or offer ... opting-out";
  - sensitive information "generally requires consent";
  - "de-identifying personal information is a use ... for a secondary purpose" ([OAIC](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models) [P]).

  Training an extractor on member health logs needs express consent. Training on the owner's inbox uses third parties' messages without their consent.
- **Weights are data.** Memorisation (Secret Sharer) makes weights and adapters personal-information holdings: in scope for breach, backup, retention, erasure and APP 12. Weight exfiltration is a data breach.
- **Membership inference is a side channel.** Even with serving restricted, any model reachable by a non-entitled principal answers "was this text in training?" (ADR-006).

**2. Attack scenarios.**
- A partner queries a reranker fine-tuned on owner data to test hypotheses ("was 'sell the cafe' in training?").
- A stolen adapter.
- A member's erasure request when their data trained a shared extractor.

**3. Regulatory risk.**
- APP 6 and APP 3.3 (sensitive information).
- APP 11.2 destruction, which the model must honour.
- APP 12: do inferences or "model knowledge" fall within access? (UNKNOWN; OAIC treats inferred information as personal information.)
- ADM disclosure if a trained model drives member-affecting decisions.

**4. Operational burden.**
- Lineage manifests, retrain pipelines, a consent registry, MIA testing per release.

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| **Non-parametric learning first**: learn by writing data (aliases, U2b vocabulary, hard-negative lists, per-scope boosts). Deletion = delete rows; ACL = row ACL | Almost always at this scale | Cannot learn deep semantic shifts |
| **Per-principal linear query adapters**: a d×d transform on query embeddings trained from that principal's feedback ([Chroma](https://www.trychroma.com/research/embedding-adapters) [V]). Low capacity to memorise; drop on revocation | Owner, or any heavy single user | Gains unproven on our data |
| Train only on **synthetic twins** generated from schemas | Extractors and linkers (N4) | Domain shift |
| **DP fine-tuning** for anything shared across principals | Large shared corpora | Tiny partitions: utility collapses |
| SISA shards per partition | Exact unlearning by retraining one shard | More training runs |

**6. Verdict: Keep-with-changes.** Add to principle 13:
- (a) non-parametric first;
- (b) retrain, never "unlearn";
- (c) a lineage manifest per artefact, CI-checked (extends ADR-006 acceptance check 4);
- (d) express consent for sensitive or member data in training;
- (e) MIA from a non-entitled identity before any model serves beyond the owner.

**7. Decisive test and kill: S9, completing W11.**
- **Setup.** On the same correction stream, compare (i) U2b non-parametric vocabulary, (ii) a per-owner linear query adapter, (iii) a LoRA-fine-tuned embedder.
- **Measure** CR@10 per class and MIA AUC from a partner identity (LoRA-Leak-style reference attack).
- **Kill parametric internal learning** if its gain over (i) is <2 pp on every class, or if MIA AUC >0.6 from a non-entitled identity.

---

## 11. U5: behavioural, app-usage and purchasing data for in-house use (owner's proposal)

The owner credits this as U5. The aim (a better app, informed teams) is legitimate. The attack is on the framing "store it locally, then use it in-house".

**1. Strongest case against.**
- **Collection.**
  - APP 3 allows only what is *reasonably necessary* for the business's functions. "The reasons behind" purchases are *inferences*, and the OAIC treats inferred information as personal information.
  - The Tribunal in Bunnings held that "the threshold for 'collection' ... is a low one", covering even transient processing ([Clayton Utz](https://www.claytonutz.com/insights/2026/february/bunnings-wins-appeal-on-facial-recognition-technology-key-takeaways-for-businesses-and-privacy-law) [2]).
  - Training logs, injuries and body metrics are health information, which needs consent (APP 3.3).
- **State law reaches the gym regardless of size.** Victoria's Health Records Act applies to private organisations holding health information, and the Health Department lists "gymnasiums" by name; it "applies regardless of the size of the business" ([health.vic.gov.au](https://health.vic.gov.au/legislation/health-records-act) [P]). It also carries HPP retention and business-closure duties ([HCC](https://hcc.vic.gov.au/providers/health-records-providers) [P]). NSW has a parallel act (HRIP Act; the IPC page was blocked, so UNKNOWN detail).
- **Use and disclosure.**
  - Founders and teams for service delivery and product improvement may sit within reasonable expectations if notified (APP 5, APP 6).
  - "Stakeholders" (investors, partners in other businesses) is *disclosure*.
  - Upsell is direct marketing (APP 7).
  - The tranche-2 draft would replace much of APPs 3, 4 and 6 with a "fair and reasonable" test and regulate "trading" in personal information ([HSF Kramer](https://www.hsfkramer.com/insights/2026-09/the-draft-tranche-2-privacy-act-reforms-whats-there-whats-new-and-whats-missing) [2]).
- **ADM.** From 10 Dec 2026, if a program using behavioural data makes or substantially informs decisions that could significantly affect members, the privacy policy must describe it. Examples: churn-risk interventions, eligibility for offers. "Targeted ... differential pricing" is a named example ([Corrs](https://corrs.com.au/insights/automated-decision-making-preparing-for-the-new-transparency-obligation) [2]).
- **Re-identification at small scale is trivial.** Four spatiotemporal points uniquely identified 90% of 1.1M card holders, and coarsening "provide[s] little anonymity" ([de Montjoye](https://dspace.mit.edu/handle/1721.1/96321) [I]).
  - In a gym of a few hundred members, staff *know* the 5 am regulars. "De-identified" check-in plus purchase data is identified data to an insider.
  - The OAIC found that unit-level de-identification "is very difficult", and found APP 6 and APP 11 breaches where reversible encryption was used ([MBS/PBS](https://www.oaic.gov.au/privacy/privacy-assessments-and-decisions/privacy-decisions/investigation-reports/mbspbs-data-publication) [P]).
  - Aggregates leak too: the Strava heatmap revealed military bases ([Help Net](https://www.helpnetsecurity.com/2018/01/29/strava-user-heatmap-reveals-patterns-of-life-in-western-military-bases/) [S]).
- **Safety.** Check-in times are a location pattern. An abusive ex who works at, or partners in, the gym can track a victim. The tranche-2 draft proposes making precise geolocation sensitive information.
- **Breach magnitude.** Basic-Fit (2026): about 200k to 1M members' names, addresses, dates of birth and bank details ([Help Net](https://www.helpnetsecurity.com/2026/04/14/basic-fit-data-breach/) [2]). Holding behavioural and health profiles raises the "serious harm" assessment for any breach.
- **Staff data.** If U5 includes staff app usage, NSW requires 14 days' written notice for computer surveillance ([Sprintlaw summary](https://sprintlaw.com.au/articles/workplace-surveillance-act-2005-nsw-explained/) [2]).
- **Tort.** Employee snooping is classic misuse of information. The business may be vicariously liable. Damages are capped at the greater of $478,550 or the defamation non-economic cap, and exemplary damages are available ([Corrs](https://corrs.com.au/insights/the-new-statutory-tort-for-serious-invasions-of-privacy-and-its-implications-for-business) [2]).

**2. Attack scenarios.**
- A staff member looks up an ex-partner's attendance.
- A "stakeholder" deck includes a cohort of three members, so they are identifiable.
- A breach of the behavioural store.
- An analyst links cafe purchases to gym health data.
- A member's APP 12 request asks for "everything you inferred about me".

**3. Regulatory risk.** APPs 3, 5, 6, 7, 11, 12 and 13 (correction of inferences), the Victoria HRA, the ADM register and the tort. A regulator's first question: "What specific business question needs row-level behavioural data, and why couldn't an aggregate answer it?"

**4. Operational burden.**
- Purpose tags enforced in code; consent tiers; transparency page.
- APP 12 exports that include inferences.
- Retention schedules.
- An aggregate gateway with a privacy budget.

**5. Alternatives.**

| Option | Wins when | Loses when |
|---|---|---|
| **Purpose-registered aggregate gateway**: each in-house question registered with a purpose and an approved query; outputs only above a minimum cell size (k ≥ 10); DP noise for anything leaving operations (stakeholders). ABS TableBuilder's cell perturbation is a production precedent connected to DP ([arXiv 2303.13771](https://arxiv.org/pdf/2303.13771) [I]); [OpenDP](https://opendp.org/tools) [P] for tooling | Coarse KPIs: attendance by hour band, churn by plan, feature adoption | Fine cuts on a few hundred members: noise and suppression destroy utility |
| **Row-level for service delivery only** (the member's coach, front desk), purpose-logged | Operations | n/a |
| **Consented research panel**: members opt in to richer tracking for perks; ISO 27560 consent records | Product discovery | Selection bias |
| **Member-held vault** (Solid pods; Flanders' Athumi runs Solid in production, [Inrupt](https://inrupt.com/case-study/flanders-strengthens-trusted-data-economy) [V]) | Trust, portability, per-person erasure | Operational complexity; overkill at stage 2 |
| **Synthetic data for stakeholders and teams** | Decks, investor updates | Not for operational decisions |

**6. Verdict: Rethink the framing; keep the capability with changes.**
- Behavioural records live in the member tenant with **purpose tags**. Service delivery is row-level and logged.
- **In-house analytics only through the purpose-registered aggregate gateway.**
- No stored inferred "reasons" unless the member stated them or consented.
- An ADM register before 10 Dec 2026.
- A member-facing "what we hold, what we inferred, why, who saw it" page, modelled on My Health Record's access history and alerts ([MHR](https://www.myhealthrecord.gov.au/for-you-your-family/howtos/who-can-access-your-record) [P]).

**7. Decisive test and kill: S10, the owner's own question in the hypotheses board, made concrete.**
- **Setup.** The owner and founders write 30–50 real in-house questions. For each, compare the decision reached from (a) the aggregate gateway (k ≥ 10, quarterly DP budget ε = 1–3 for external outputs) vs (b) row-level data.
- **Measure:**
  - share answered with the *same decision*;
  - a **staff-knowledge re-identification red team** on gateway outputs: can a staff member who knows members identify any individual's behaviour?
- **Kill / redesign:**
  - <70% decision-equivalent → add a consented panel for the gap questions;
  - any successful re-identification at k ≥ 10 → raise thresholds or drop the dimension.

---

## 12. U6: consented shared spaces with multi-party approval (owner's proposal)

**1. Strongest case against.** The design ("view with a consent ledger, never a copy; contributions owned by contributors; revocation removes the view and derived artefacts") treats three different relationships as one:
- **Business spaces are company records, not contributor property.**
  - A partnership decision citing both partners' inputs belongs to the business entity (the controller).
  - Contributor revocation would delete the remaining partner's decision history and break record-keeping duties.
  - A *former* director may still inspect the books for 7 years for possible legal proceedings ([s198F](https://aicd.com.au/board-of-directors/duties/fiduciary/failure-to-quote-chapter-and-verse.html) [2]).
  - Exit should mean *loss of access plus an agreed export*, not deletion.
- **Couple's joint finance is a coercive-control vector.**
  - "Both must accept" protects creation. But an abuser can pressure acceptance, and once shared, spending visibility is a tool of financial abuse.
  - NSW's coercive-control offence is in force; BOCSAR has published monitoring since July 2024 ([BOCSAR](https://bocsar.nsw.gov.au/research-evaluations/2024/Coercive_control_monitoring_preliminary_report_Jul_2024.html) [S]). See also [eSafety on "technological tethers"](https://esafety.gov.au/newsroom/blogs/calling-out-technological-tethers-in-coercive-control) [S].
  - Precedent: Australia's Consumer Data Right joint accounts.
    - Any holder can move to "non-disclosure" at any time (rule 4A.7).
    - The other holders *must* be notified (4A.7(3)).
    - The data holder is shielded from liability where it acts to prevent "physical, psychological or financial harm or abuse" (4A.15) ([DSB CX](https://cx.dsb.gov.au/consent-management/consent-management-data-holder/account-permissions/joint-account-disclosure-option-management-service/cx-guidelines); [4A.15](https://cx.cds.gov.au/overview/cx-checklist/cx-guidelines/02-vulnerable-consumers) [P]).
  - Lesson: **exit must be unilateral, and in a safety case silent or delayed**, like Apple's Safety Check emergency reset ([MacStories](https://www.macstories.net/news/safety-check-lets-victims-of-domestic-or-intimate-partner-violence-reset-privacy-settings/) [S]).
- **Member–trainer shares cross a controller boundary when the PT is a contractor.**
  - Disclosure goes to a separate business, and a departing PT may take client data.
  - Trainer notes are the gym's records (or the PT's, by contract). The member can access them (APP 12; Vic HPP).
  - Grants should be **time-boxed** and expire on trainer departure.
- **The owner is both operator and party.** In the owner's own separation or partnership dispute, he controls the system holding the other party's data and audit trail, with "Everything" access (C4). No consent ledger fixes a custodian conflict.
- **Revocation vs legal hold** (C6), and **delivered content cannot be recalled** (§5).
- **Consent fatigue** for every share event.

**2. Attack scenarios.**
- Separation: the spouse revokes; the owner, as operator, still reads her data through owner tier or backups.
- Contested partnership exit under litigation hold: revocation deletes derived decision records, which is spoliation.
- A trainer leaves for a competitor with exports of member programs.
- An abuser coerces a joint-space acceptance.
- A subpoena to the business for joint-space content in the owner's own family-law matter.

**3. Regulatory risk.**
- APP 6 (disclosure to a contractor PT).
- APP 11 and APP 12.
- The tort (misuse by an ex-partner).
- Family-law and court process.
- Victoria HPP 10 notice duties if a health-service business closes or is sold ([HCC](https://hcc.vic.gov.au/providers/health-records-providers) [P]).

**4. Operational burden.**
- A consent-ledger UI; safety-exit support; hold custodian role; export tooling for exits; contract templates (partnership, PT).

**5. Alternatives.** Split U6 into three constructs:

| Construct | Ownership | Creation | Exit | Hold |
|---|---|---|---|---|
| **Business space** | Entity (controller); role grants | Owner or entity admin grants | Access ends at once; agreed export per partnership agreement; records retained under company duties | Normal records hold |
| **Personal joint space** (couple) | Contributor-owned items; jointly-authored items dual-owned | Both accept (CDR-style co-approval) | **Unilateral**, any time; "safety exit" withdraws all shares and delays or neutralises the notification | **Sealed**: invisible to both parties; custodian-only access under hold; auto-shred at release |
| **Professional share** (member–trainer) | Member's data stays member's; trainer notes owned by the gym | Member grants, scoped and **time-boxed** (e.g. 90 days, renewable) | Member revokes, or the grant auto-expires on trainer departure | Gym record retention (HPP) |

Also:
- Household and partner *personal* vaults are encrypted with keys the owner does not hold, such as passkey-derived keys (innovation 4).
- Every grant is an ISO 27560 consent record in a tamper-evident ledger.

**6. Verdict: Rethink (partly).** The owner's core idea of consented, revocable, multi-party grants survives for personal spaces. Business spaces and professional shares need different ownership and exit rules. Safety exit and sealed revocation are mandatory.

**7. Decisive test and kill: S8, the dissolution suite in BrainBench.**
- **Six scenarios:**
  1. amicable partner exit;
  2. contested exit under hold;
  3. couple separation with the safety flag;
  4. trainer departure;
  5. member revokes PT;
  6. subpoena where the owner is a party.
- **Measure:**
  - residual visibility to the revoked party across all channels (must be 0 within the SLA);
  - wrongful loss of records the remaining controller must keep (must be 0);
  - notifications sent in safety mode (must be 0 or delayed);
  - owner-identity access to the spouse's vault (must be 0).
- **Kill.** Any scenario that needs manual database surgery means the model is incomplete.

---

## 13. Innovations that emerged from attacking the design (up to 5)

1. **Twin-world noninterference CI ("shadow twin").** Replace "list every side channel" with one property, checked on synthetic replicas:
   - For every identity, mutate only what it cannot see (insert, edit, delete or revoke hidden rows, including alias and key collisions). Require every observable to be identical: IDs, order, score bands, counts, snippets, errors, and latency at stated power.
   - Evidence: in X1 it flagged global BM25 and cross-partition fitting where canaries raised 0/744, and it caught an implementation tie-break artefact no rule anticipated.
   - It runs without fabricated records on real people, so it can gate every merge.
   - Builder note: it is a ~200-line harness over the existing service layer, reusing BrainBench worlds. Tests S2 and S3.
2. **Egress classes (destination-aware release).**
   - Bind each OAuth client ID (CIMD-verified under MCP 2026-07-28) to an egress class: `onshore-controlled` (first-party UI on Bedrock AU or the local LLM), `offshore-ZDR-contracted`, `offshore-consumer`.
   - Release policy = f(item sensitivity label, third-party-personal-information flag, egress class) → release / pseudonymise / withhold-with-pointer.
   - This generalises ADR-002 item 7, makes ADR-016's "local-first" true on the answer path, and gives APP 8 an enforceable control.
   - Pair with **exfiltration honeytokens**, which detect a compromised client, the one attacker the brain otherwise cannot see. Tests S1 and S6.
3. **Lineage taint plus an MCP egress firewall.**
   - Trust = minimum over content lineage, not the door. Forwarded or pasted content stays T4; third-party-client writes are T3.
   - High-risk attributes (payee, bank details, reset emails, medical flags) need out-of-band verification.
   - T4 text leaves the brain only as neutralised snippets: no URLs, images, markup or imperatives. Full text only via an explicit fetch.
   - This closes the laundering path and stops the brain acting as stored-XSS for AI clients. Tests S4.
4. **Least-privilege owner: personas, break-glass and vaults with keys the owner does not hold.**
   - Split the owner into scoped personas for third-party clients; owner-everything only in the first-party UI with step-up.
   - Member health reachable only through a business role with purpose logging and a **break-glass that notifies the member** (My Health Record-style access history).
   - Household and partner personal vaults encrypted under keys the owner never holds.
   - This resolves the charter §3a vs §3c contradiction, shrinks the blast radius of the most dangerous token, and removes the operator-as-party conflict in disputes. Tests S1 and S8.
5. **Per-subject envelope keys plus a "sealed" state.** Each member (and each sensitive owner-tier item) gets its own data key. The lifecycle has four states, active → sealed → shredded (or retained under a statutory minimum):
   - "Sealed" = inaccessible to all principals except a hold custodian, with audit.
   - It reconciles APP 11.2 destruction (including backups), Victoria HPP retention minimums, legal holds, U6 revocation and ADR-008's append-only history in one state machine.
   - Tests S5 and S8.

---

## 14. Proposed updates for the board and ADRs (for the caller to apply)

**New hypotheses for doc 06, section D or a new section S:**

| ID | Hypothesis | Where | Kill / decision |
|---|---|---|---|
| S1 | Personas + egress classes + T3-default writes cut confused-deputy exfiltration to 0/300 | S (harness with Claude as client) | >0 sensitive exfiltrations, or >20% legitimate writes stuck after 24 h |
| S2 | A twin-world noninterference suite detects every injected leak class; per-group postings pass the powered timing test | S / B (timing) | Component restricted to single-group use if it fails at <2× p95 |
| S3 | Canaries detect ≥50% of 10 injected leak classes | S | <50% → demote canaries in charter §8 (X1: 0/2 so far) |
| S4 | Lineage taint + egress firewall: laundered promotion ≤1%, targeted top-k ≤5%, client action 0/299 | S | Exceed → T4 out of default retrieval |
| S5 | Erasure drill passes across live data, backups, caches, logs and eval sets; per-subject keys cost <2× p95 | B | Fall back to tenant keys plus backup re-write |
| S6 | Client-answer egress is <10% of sensitive items per month without egress classes | S | ≥10% → egress classes mandatory; amend charter §6.3 |
| S7 | An adaptive red-team round finds no leak class outside the static suite | S / B | Any new class → withdraw "≤1%" wording |
| S8 | The six dissolution scenarios pass with zero residual visibility, zero wrongful loss, zero unsafe notifications | S | Manual DB surgery needed → model incomplete |
| S9 (W11) | Parametric internal learning beats non-parametric by ≥2 pp with MIA AUC ≤0.6 | S+ | Otherwise non-parametric only |
| S10 (U5) | The aggregate gateway answers ≥70% of real in-house questions with the same decision; no staff-knowledge re-identification at k ≥ 10 | S + owner input | <70% → consented panel |

**ADR edits (summary):**
- ADR-002: items 1, 4 and 6 as in §3.6; cite the 2026-07-28 spec.
- ADR-006: reframe the rule (§4.6); the KS test → a powered test; option (b) default; a no-CREATE text-to-SQL role.
- ADR-007: canaries → smoke alarm on synthetic entities; sampled schedule; revocation epoch; delivered-content ledger; SLA wording.
- ADR-014: lineage taint; attribute registry; independent-channel corroboration; egress firewall; widened H18 metric.
- ADR-015: retitle and widen scope; per-subject keys; legal check; hardening baseline; TDE decision moves to ADR-003.
- ADR-016: egress classes; label-recall SLO; hosted-exposure budget; location by ops score.
- ADR-018: assurance case; privacy drills; evaluation governance.
- ADR-008 (outside cluster, flagged): retention schedule and sealed state vs "keep everything".
- Charter:
  - §3a owner tier → personas plus break-glass; resolve the §3c conflict;
  - P13 additions (§10.6);
  - §6.3 "removes the overseas-disclosure question" pending S6;
  - §8 leakage evidence = S2 + S7, with canaries as a monitor.
- BrainBench: change `meta.json` so owner and partner_gym do **not** have standing `member/*` access (coach-scoped grants instead), then re-run E5 and the canary monitor against the corrected policy.

**Legal review items to add (not legal advice; questions for counsel):**
1. Which business entities are APP entities? Small-business status of the cafe and construction company under s6D(4)(c) and s6D(9) if data is shared across them.
2. Is the gym a "health service provider"? Does the Victoria or NSW health records law apply, and with what retention minimums?
3. Does crypto-shredding satisfy APP 11.2 destruction or "beyond use"?
4. Is returning third-party personal information to offshore consumer AI clients a disclosure, and what notice or contract is needed?
5. Ownership of shared-space records on partner exit; PT contractor data terms.
6. ADM register scope for U5 by 10 Dec 2026.

---

## 15. Checklist closure and threats to validity

| Question | Status |
|---|---|
| Strongest case and hidden assumptions per item | Answered (§2–§12) |
| Attack scenarios: insider, client, member, breakup, subpoena, GPU breach, backup, weights, side channels | Answered. Timing channel INFERRED, not measured |
| Australian regulatory risks: APPs 3, 5, 6, 8, 11, 12, 13; health; ADM; tort; NDB | Answered as questions for counsel. Victoria HRA confirmed; NSW HRIP detail UNKNOWN (page blocked); s13B INFERRED from the ALRC summary |
| Operational burden | Answered qualitatively. GPU ops hours INFERRED estimate |
| Alternatives and when each wins | Answered |
| Verdicts and decisive tests | Answered (S1–S10) |
| Evidence from our system | X1 and X2 (sandbox, lexical, one seed). Directional only |

**Threats to validity.**
- X1 and X2 use LSA as a stand-in for fitted neural models, distinctive secret vocabulary, a closed set of 6 topics, one seed, and 12 decoding trials.
- The canary-scaling arithmetic assumes ADR-007's per-pair hourly schedule literally.
- Several incident sources are secondary or search-level and are tagged.
- Tranche-2 content is from law-firm summaries of an exposure draft with no commencement date.
- Bounded negative searches: OAIC ch. 11 on encryption/crypto-shredding (not found); the OAIC gen-AI guidance on unlearning (first 100k characters read; not found).
- DPoP support in major AI clients: UNKNOWN (not searched in depth).

---

## Sources

Project files: `00-charter.md`, `06-hypotheses-board.md`, `docs02/ADR-002, -003, -006, -007, -008, -011, -014, -015, -016, -018`, `brainbench/RESULTS.md` (E4, E5), `brainbench/data/meta.json`, `brainbench/data/items.jsonl`, `challenges/da3_analysis/*`.

- MCP spec 2026-07-28 changelog: https://modelcontextprotocol.io/specification/2026-07-28/changelog
- Asana MCP exposure: https://www.upguard.com/blog/asana-discloses-data-exposure-bug-in-mcp-server
- Slack AI exfiltration (PromptArmor): https://promptarmor.com/resources/data-exfiltration-from-slack-ai-via-indirect-prompt-injection
- Invariant Labs WhatsApp MCP: https://invariantlabs.ai/blog/whatsapp-mcp-exploited
- SpAIware (ChatGPT memory): https://thehackernews.com/2024/09/chatgpt-macos-flaw-couldve-enabled-long.html
- Lethal trifecta: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- Rule of Two / Attacker Moves Second summary: https://simonw.substack.com/p/new-prompt-injection-papers-agents ; paper: https://arxiv.org/abs/2510.09023
- CaMeL: https://arxiv.org/abs/2503.18813
- Spotlighting: https://arxiv.org/abs/2403.14720
- Salesloft Drift OAuth theft: https://www.helpnetsecurity.com/2025/08/27/hundreds-of-salesforce-customer-orgs-hit-in-clever-attack-with-potentially-huge-blast-radius/
- RFC 9449 DPoP: https://www.rfc-editor.org/rfc/rfc9449
- KV-cache timing governance: https://arxiv.org/pdf/2608.09225 ; PROMPTPEEK (NDSS): https://ndss-symposium.org/ndss-paper/i-know-what-you-asked-prompt-leakage-via-kv-cache-sharing-in-multi-tenant-llm-serving
- vLLM prefix caching / cache_salt: https://docs.vllm.ai/en/stable/design/v1/prefix_caching.html
- PostgreSQL CVE-2019-10130: https://www.postgresql.org/support/security/CVE-2019-10130 ; CVE-2025-8713: https://www.postgresql.org/support/security/CVE-2025-8713 ; CVE-2024-10976: https://www.postgresql.org/support/security/CVE-2024-10976 ; RLS docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Percona pg_tde: https://docs.percona.com/pg-tde/
- TEE.fail: https://thehackernews.com/2025/10/new-teefail-side-channel-attack.html
- H100 confidential computing overhead: https://arxiv.org/html/2409.03992v2
- Exposed self-hosted AI (CSA): https://labs.cloudsecurityalliance.org/research-rb/csa-research-note-self-hosted-ai-infrastructure-exposure-202/
- NVIDIAScape CVE-2025-23266: https://wiz.io/blog/nvidia-ai-vulnerability-cve-2025-23266-nvidiascape
- LeftoverLocals: https://blog.trailofbits.com/2024/01/16/leftoverlocals-listening-to-llm-responses-through-leaked-gpu-local-memory/
- Malicious HF models: https://thehackernews.com/2024/03/over-100-malicious-aiml-models-found-on.html
- TotalRecall (Windows Recall): https://www.malwarebytes.com/blog/news/2024/06/microsoft-recall-snapshots-can-be-easily-grabbed-with-totalrecall-tool
- Unlearning vs quantisation: https://arxiv.org/html/2410.16454v3
- LoRA-Leak: https://arxiv.org/abs/2507.18302v1
- Secret Sharer: https://arxiv.org/abs/1802.08232
- SISA unlearning: https://arxiv.org/abs/1912.03817
- Chroma embedding adapters: https://www.trychroma.com/research/embedding-adapters
- OAIC gen-AI training guidance: https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models
- OAIC commercial AI products guidance: https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products
- OAIC APP 3: https://oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information
- OAIC APP 8: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information
- OAIC APP 11: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information
- OAIC APP 12 access: https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/handling-personal-information/dealing-with-requests-for-access-to-personal-information
- OAIC NDB quick reference: https://www.oaic.gov.au/privacy/notifiable-data-breaches/quick-reference-guide-for-responding-to-data-breaches
- OAIC NDB statistics 2025: https://www.oaic.gov.au/news/media-centre/data-breach-notifications-increase-to-all-time-high-in-2025,-new-ndb-stats-show
- OAIC statutory tort: https://www.oaic.gov.au/privacy/your-privacy-rights/more-privacy-rights/statutory-tort-for-serious-invasions-of-privacy ; Corrs: https://corrs.com.au/insights/the-new-statutory-tort-for-serious-invasions-of-privacy-and-its-implications-for-business
- ADM transparency (Corrs): https://corrs.com.au/insights/automated-decision-making-preparing-for-the-new-transparency-obligation
- Tranche-2 draft (HSF Kramer): https://www.hsfkramer.com/insights/2026-09/the-draft-tranche-2-privacy-act-reforms-whats-there-whats-new-and-whats-missing
- Privacy Act s6D: https://20.austlii.edu.au/au/legis/cth/consol_act/pa1988108/s6d.html
- Victoria Health Records Act: https://health.vic.gov.au/legislation/health-records-act ; HCC providers: https://hcc.vic.gov.au/providers/health-records-providers
- Bunnings ART decision (Clayton Utz): https://www.claytonutz.com/insights/2026/february/bunnings-wins-appeal-on-facial-recognition-technology-key-takeaways-for-businesses-and-privacy-law
- OAIC MBS/PBS investigation: https://www.oaic.gov.au/privacy/privacy-assessments-and-decisions/privacy-decisions/investigation-reports/mbspbs-data-publication
- Unique in the shopping mall: https://dspace.mit.edu/handle/1721.1/96321
- Strava heatmap: https://www.helpnetsecurity.com/2018/01/29/strava-user-heatmap-reveals-patterns-of-life-in-western-military-bases/
- Basic-Fit breach: https://www.helpnetsecurity.com/2026/04/14/basic-fit-data-breach/
- Payment redirection losses 2025: https://www.eftsure.com/blog/industry-news/$167m-lost-in-2025-why-bec-scams-keep-costing-australians/
- Uber MFA fatigue: https://www.darkreading.com/cyberattacks-data-breaches/uber-breach-external-contractor-mfa-bombing-attack
- CDR joint accounts (DSB CX): https://cx.dsb.gov.au/consent-management/consent-management-data-holder/account-permissions/joint-account-disclosure-option-management-service/cx-guidelines ; rule 4A.15: https://cx.cds.gov.au/overview/cx-checklist/cx-guidelines/02-vulnerable-consumers
- Apple Safety Check: https://www.macstories.net/news/safety-check-lets-victims-of-domestic-or-intimate-partner-violence-reset-privacy-settings/
- BOCSAR coercive control monitoring: https://bocsar.nsw.gov.au/research-evaluations/2024/Coercive_control_monitoring_preliminary_report_Jul_2024.html ; eSafety: https://esafety.gov.au/newsroom/blogs/calling-out-technological-tethers-in-coercive-control
- Former director access s198F (AICD): https://aicd.com.au/board-of-directors/duties/fiduciary/failure-to-quote-chapter-and-verse.html
- ISO/IEC TS 27560 via DPV: https://w3c-cg.github.io/dpv/guides/consent-27560
- Flanders Athumi / Solid: https://inrupt.com/case-study/flanders-strengthens-trusted-data-economy
- OpenDP: https://opendp.org/tools ; ABS perturbation and DP: https://arxiv.org/pdf/2303.13771
- US v. Heppner (Proskauer): https://www.proskauer.com/alert/sdny-addresses-privilege-and-work-product-implications-of-using-unsecured-public-ai-tools
- ASD Essential Eight: https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/essential-eight/essential-eight-maturity-model-and-ism-mapping
- NSW workplace surveillance (summary): https://sprintlaw.com.au/articles/workplace-surveillance-act-2005-nsw-explained/
- My Health Record access history: https://www.myhealthrecord.gov.au/for-you-your-family/howtos/who-can-access-your-record
