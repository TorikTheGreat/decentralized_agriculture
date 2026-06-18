# Expand Section

Identify opportunities to strengthen a single LaTeX section with additional evidence, flag cross-section relevance from its sources, and propose additions one at a time for approval. This command focuses on **finding gaps and filling them** — for accuracy and correctness verification, use `/verify-section`.

## Usage

```
/expand-section <section-name-or-number> [--fresh]
```

Example: `/expand-section 2.6.1` or `/expand-section "Structural drivers"` or `/expand-section 2.6.1 --fresh`

Run this **after** `/verify-section` has been completed for the target section — expansions should build on corrected text, not text that's about to change.

---

## Phase 0 — Check for existing expansion items

Before running any analysis, check whether `sources/corrections.md` exists and contains pending expansion items (IDs matching `S*-E*`) for the target section.

- **If pending items exist AND `--fresh` was NOT passed**: skip Phase 1. Read the pending items and proceed directly to Phase 2. Present the list first, then work through them one at a time.

- **If the section has expansion entries but none are Pending** (all Applied or Skipped): it has already been fully processed. Inform the user. They can re-run with `--fresh`.

- **If the section has no expansion entries at all in corrections.md** (never analyzed): proceed to Phase 1 as if `--fresh` was passed.

- **If `sources/corrections.md` does not exist, OR `--fresh` was passed**: proceed to Phase 1. After Phase 1:
  - If `sources/corrections.md` exists, replace **all** expansion entries (`S*-E*`) for this section — regardless of current status (Pending, Applied, Skipped) — with the new findings. Preserve other sections and all verification entries. Update summary counts.
  - If it does not exist, create it with entries for this section only.

---

## Phase 1 — Analysis (automated)

### Step 0 — Ensure OCR text is available

Check that `sources/ocr/` contains `.txt` files for the sources needed by this section. If missing, run:

```
.venv/bin/python utils/extract_text.py
```

For individual files:

```
.venv/bin/python utils/extract_text.py --file sources/<filename>.pdf
```

OCR text is reliable for verifying statistics, quotes, and specific language. PDF images are unreliable for dense text and have produced confident but wrong readings. Both the orchestrator and subagents must use **both** together: OCR text for exact numbers, quotes, and wording; PDF for figures, tables, spatial layout, and visual elements.

### Step 1 — Orient

1. Read `whitepaper/chapters/problem/problem.tex` and (if it exists) `whitepaper/chapters/solution/solution.tex`.
2. Read `whitepaper/bibliography.bib`.
3. Locate the target section and extract every citation key it uses.
4. Build a **section outline** — one line per `\subsection` or `\subsubsection` summarizing its argument (e.g., `2.1 Land Use — cropland expansion, deforestation, habitat loss`). This outline is included in every subagent prompt.
5. Read `sources/citation_map.md`.
6. Build a **local source index**: for every file in `sources/` that appears in the citation map, record its citation key and a one-line topic derived from the bibliography entry's title field. This lets the orchestrator and subagents identify uncited-but-relevant sources without reading every file.

### Step 1.5 — Scout: academic landscape scan (web search)

Dispatch ONE scout subagent (subagent_type: `general-purpose`) to map the state of the academic literature for the target section's topic area. This runs in **parallel** with Step 2 (cited-source PDF scans).

The scout's purpose is to identify what's NOT in our local sources but matters — recent major work, live debates, contradictory evidence, and gaps between the section and the current state-of-the-art. Local-source-only scans are a confirmation pass; the scout is what makes the pass a real expansion.

The scout receives:

1. The **section outline** from Step 1.4 (full chapter outline so the scout knows what's covered elsewhere).
2. The **full text of the target section**.
3. The **current citation keys** used by the section.
4. Instructions to use **WebSearch and WebFetch** to identify, for the section's topic area:
   - **Recent major papers** (last 5 years preferred, peer-reviewed, high-impact journals — Nature, Science, PNAS, Nature sub-journals, specialty top-tier journals)
   - **Live debates** the section doesn't engage with (papers anchoring each side)
   - **Likely contradictory or complicating work** the section's current sources don't cite — search actively for evidence that would *complicate* the section's argument, not just confirm it
   - **Gaps between the section and the current state-of-the-art**: what does current literature emphasize that this section underweights or omits?
5. Hard rules:
   - **Verify each candidate via WebFetch on the abstract or landing page before reporting** — do NOT report titles without checking that the paper exists at that DOI/URL.
   - Never fabricate paper titles, authors, or DOIs.
   - Return a CONCISE map (under ~12 items total), not an exhaustive list.
   - Include "rejected candidates" with one-line reasons — this shows the search was thorough and helps the user trust the kept candidates.
6. Output format:
   ```
   MAJOR RECENT PAPERS:
   - [Full citation incl. DOI] — [1-sentence relevance to the section]

   LIVE DEBATES:
   - [Debate description] — [paper(s) anchoring each side, with full citations]

   CONTRADICTORY / COMPLICATING:
   - [Full citation] — [what it complicates about the section's argument; honest assessment of strength]

   GAPS BETWEEN SECTION AND CURRENT STATE-OF-THE-ART:
   - [Gap] — [where to look for sources; suggested search direction]

   REJECTED CANDIDATES:
   - [Title]: [one-line reason — too narrow, not peer-reviewed, doesn't add to argument, etc.]
   ```

### Step 2 — Scan cited source PDFs

Dispatch **one subagent per unique source file** cited in the section, running in parallel. Runs in **parallel with Step 1.5** (scout) — both are kicked off together.

Each subagent receives:

1. The **full file path** of the source PDF and the corresponding **OCR text file** in `sources/ocr/` (same stem, `.txt` extension).
2. The **section outline** from Step 1.4.
3. The **full text of the target section**.
4. Instructions to use **both** the OCR text file and the PDF together:
   - **OCR text** (via Read and Grep): use for all statistics, quotes, specific wording, and searching for passages. If the OCR text file is missing, the agent should extract it first: `.venv/bin/python utils/extract_text.py --file <pdf_path>`.
   - **PDF** (via Read): use for figures, tables, charts, spatial layout, and visual elements.
   - **Hard rule**: all numerical claims and quoted language identified for expansion must be read from the OCR text, not from PDF images of dense text.
5. Instructions to read the **complete** source — all pages/sections.
6. Instructions for three tasks, in priority order:

   **Task A — Target section gaps**: identify findings, data, or conclusions in the source — beyond what's already cited — that would strengthen the target section's argument.
   ```
   TARGET SECTION GAP:
   - [Argumentative gap in one sentence] → [Specific finding in source with locator]
   ```

   **Task B — Cross-section relevance**: identify findings that could strengthen sections *other than* the target.
   ```
   CROSS-SECTION RELEVANCE:
   - [Finding with locator] → Section X.Y — [one-line reason]
   ```

   **Task C — Temporal staleness**: if the source is older than 10 years, flag time-sensitive findings.
   ```
   TEMPORAL STALENESS:
   - [Citation key] ([year]): [finding] — TIME-SENSITIVE | TIME-STABLE. [If time-sensitive: what may have changed and suggested search direction]
   ```

   If nothing is found for a task, omit that section of the report.

### Step 2.5 — Triage gate (mandatory unless explicitly skipped)

After both Step 1.5 (scout) and Step 2 (cited-source scans) complete, present the scout's map to the user **before** launching Step 3. The user picks:

- Which scout threads warrant deep-dive web searches in Step 3
- Which uncited local sources (if any) warrant scans in Step 3

This gate is mandatory. Without it, scout findings cascade into deep-dive prompts and produce noise amplification on tangential leads. The triage gate preserves the curation that prevents the expansion pass from drifting outside scope.

If the user replies with explicit "skip the gate" or equivalent, proceed using the orchestrator's judgment — but record the gate-skip in the corrections.md note for the pass.

### Step 3 — Deep-dive: web-search subagents + uncited local sources

For each thread the user picked from the scout map, dispatch a **web-search subagent**. For each uncited local source the user picked, dispatch a **local-source subagent**. All run in parallel.

**Web-search subagent prompt template:**

Each web-search subagent receives:
1. The specific thread or gap to investigate (e.g., "post-2017 updates to global groundwater depletion figures").
2. The section outline + target section text.
3. The current citation keys (so it doesn't propose papers we already cite).
4. Instructions to use WebSearch and WebFetch to find 2-6 candidate papers.
5. Hard rules:
   - **Peer-reviewed primary sources preferred**; report secondaries only if no primary exists or if the secondary is a canonical synthesis.
   - **Verify each candidate via WebFetch on the abstract or landing page** — do not propose papers without confirming they exist at the URL.
   - Never fabricate titles, authors, or DOIs.
   - Include open-access link if available.
   - Recent (last 5 years) preferred for time-sensitive topics; older OK for foundational work.
   - Also report any paper that **contradicts** the section's framing — actively look for complicating evidence.
6. Output format:
   ```
   CANDIDATE N:
   - Citation: [full bib info]
   - DOI / URL: [link]
   - Open access: [yes / no / preprint available]
   - Summary: [1-2 sentences]
   - What it adds: [1 sentence — specific data point or framing]
   - Verification: [confirmed via abstract / landing page / which URL]

   COMPLICATING (if any):
   - [Same format, plus: "specific challenge:" line]

   REJECTED CANDIDATES (with reasons):
   - [Title]: [one-line reason]
   ```

**Local uncited source subagent prompt template:**

From the local source index (Step 1.6), identify files not cited in the target section. For sources the user picked at the gate, dispatch a subagent to:
1. Read the source (OCR + PDF).
2. Read the target section text.
3. Assess whether the source contains findings that would strengthen the target section.
4. Return relevant findings with locators, or report "no relevant content."

### Step 4 — Orchestrator synthesis

After all Phase-1 subagents return, synthesize findings from:
- Cited-source PDF scans (Step 2)
- Web-search subagents (Step 3)
- Local uncited-source scans (Step 3)
- Scout landscape map (Step 1.5) — threads NOT pursued in Step 3 are logged as future-investigation items the user can pursue later

For each gap:
- Describe the argumentative gap in one sentence.
- Identify the source/candidate and locator.
- If no source (local or web-found) fills the gap, log it as a search-direction item with concrete query suggestions.

Resolve cross-source issues that individual agents could not detect in isolation (e.g., contradictory findings across cited-source vs. web-found candidates).

### Step 5 — Compile and present

Present findings in four groups:

1. **Expansion opportunities for the target section** (with source, locator, and gap description). Distinguish:
   - Items backed by sources we have (local PDF)
   - Items backed by web-found candidates the user needs to acquire
   - Items still requiring source acquisition (no candidate found yet)
2. **Cross-section findings** (grouped by target section, for the user to pursue later)
3. **Temporal staleness flags** (from Step 2)
4. **Scout threads not pursued** (logged for future, but flagged so they're not lost)

Log all expansion items to `sources/corrections.md` under the appropriate section using the expansion ID format (e.g., `S2.3-E3`). Cross-section items are logged under their **target** section (the section that would be strengthened). Each entry must be self-contained: include the source file, finding with locator, and which expansion pass surfaced it, so a future session can act on it without additional context.

Each expansion entry uses this format:

    ### S[section#]-E[N]. [short title]
    **Status:** Pending
    **Category:** Expansion | Cross-section | Temporal
    **Type:** Expand
    **Severity:** Major | Minor
    **Lines:** [line numbers, or "New content"]
    **Gap:** [one-sentence description of the argumentative gap]
    **Suggested source:** [local file with locator, search query, or named source with DOI]
    **Source of finding:** [cross-section items only: which expansion pass surfaced this]

Include a summary table at the section level:

    | # | Category | Type | Severity | Status | Summary |
    |---|----------|------|----------|--------|---------|

---

## Phase 2 — Interactive additions (one at a time)

Work through expansion items for the **target section** first, then present cross-section findings for the user to defer or pursue.

For each item the user wants to pursue:

1. State the opportunity clearly, referencing its ID (e.g., `S2.6.1-E3`).
2. Dispatch a subagent (`general-purpose`) with:
   - The source file paths (PDF + OCR) and the specific finding with locator
   - The **full text** of the target section
   - Instructions to: check whether the finding is already covered by the section, contradicts existing content, or would genuinely strengthen the argument — and if so, propose specific text and placement. Every `\cite` in the proposed text must include a pinpoint locator: `\cite[locator]{key}`
3. **Verify pinpoint citations and self-verify proposed text against the source before presenting**:
   - Check that every `\cite` in the proposed text includes a locator: `\cite[locator]{key}`.
   - **Locator accuracy**: every page, section, figure, or table reference in the proposed text must point to content that actually supports the specific claim. Confirm via Grep on the OCR text file. Do **not** copy locators from the subagent's report without re-checking — page numbers and section numbers are easy to misattribute.
   - **No "plausibly true" content**: every term, framing, mechanism description, or quantitative claim in the proposed text must come from the cited source. Do **not** introduce textbook terminology, field-standard generalizations, or technical framings that are widely accepted but absent from the cited source. If you want to use such language: (a) cite a different source that does contain it, (b) rewrite to use the source's actual language, or (c) drop the claim. "Plausibly true based on field knowledge" is **not** sufficient — only "verified in the cited source" is.
   - If the source is new to the bibliography, draft the bib entry too.
4. Present the subagent's proposed text to the user.
5. Wait for explicit approval before applying.
6. Apply the approved edit using the Edit tool.
7. Confirm the edit was applied.
8. **Post-edit integration check**: re-read the full paragraph and verify that the addition integrates with surrounding text — no contradictions with adjacent claims, no redundancy introduced, logical flow preserved. If the edit broke something, flag it immediately as a new item.
9. Update `sources/corrections.md`: `Pending` → `Applied` or `Skipped`. Update summary counts.
10. Move to the next item.

Items the user defers are left as `Pending` for future sessions.

---

## Hard constraints

- Run `/verify-section` on the target section first. Expansions build on corrected text.
- **Always verify numerical claims and quoted language against the OCR text files** in `sources/ocr/` using Grep and Read on the `.txt` files. Use the PDF for figures, tables, and visual elements. If an OCR text file is missing, run `.venv/bin/python utils/extract_text.py --file <pdf_path>` before proceeding.
- **Web search is a default Phase-1 step, not optional.** Step 1.5 (scout) and Step 3 (deep-dive web-search subagents) must run unless the section's topic is so niche that no productive web search exists — and in that case, document why in the pass notes. Treating expansion as "what can we say with the sources we already have" is a confirmation pass, not an expansion pass.
- **Verify every web-found candidate via WebFetch** on the abstract or landing page before reporting it. Never propose a paper based on a title alone.
- Never fabricate paper titles, authors, or DOIs.
- **The Step 2.5 triage gate is mandatory** unless the user explicitly skips it. Without it, scout findings cascade into deep-dive prompts and amplify noise on tangential leads.
- **Actively search for contradictory and complicating evidence**, not just confirming evidence. A rigorous expansion identifies what would complicate the section's argument, so the user can either address it explicitly or sharpen the argument's scope to where it still holds.
- Never add content that contradicts claims already established in other sections without flagging the conflict.
- Always verify the edit was written to the file before moving on.
- Always update `sources/corrections.md` after each item is processed.
