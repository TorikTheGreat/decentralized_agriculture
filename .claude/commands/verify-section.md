# Verify Section

Systematically verify the citations and narrative of a single LaTeX section against source PDFs, then propose corrections one at a time for approval. This command focuses on **accuracy and correctness** — for expansion opportunities, use `/expand-section`.

## Usage

```
/verify-section <section-name-or-number> [--fresh]
```

Example: `/verify-section 2.6.6` or `/verify-section "Structural drivers"` or `/verify-section 2.10 --fresh`

---

## Phase 0 — Check for existing corrections

Before running any analysis, check whether `sources/corrections.md` exists and contains pending items (citation errors, bibliography errors, or narrative issues — not expansion items) for the target section.

- **If pending items exist AND `--fresh` was NOT passed**: skip Phase 1. Read the pending items and proceed directly to Phase 2. Present the list first, then work through them one at a time.

- **If the section has entries but none are Pending** (all Applied or Skipped): it has already been fully corrected. Inform the user. They can re-run with `--fresh`.

- **If the section has no entries at all in corrections.md** (never analyzed): proceed to Phase 1 as if `--fresh` was passed.

- **If `sources/corrections.md` does not exist, OR `--fresh` was passed**: proceed to Phase 1. After Phase 1:
  - If `sources/corrections.md` exists, replace **all** entries for this section — regardless of current status (Pending, Applied, Skipped) — with the new findings. Preserve entries for other sections. Update summary counts.
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

### Step 1 — Orient and build citation map

1. Read `whitepaper/chapters/problem/problem.tex`.
2. Read `whitepaper/bibliography.bib`.
3. Locate the target section and extract every citation key it uses.
4. Check whether `sources/citation_map.md` exists and read it if so.
5. For each citation key, look it up in the existing map. If all keys are resolved, skip to Step 2.
6. For any keys not in the map (or marked "Not found"):
   - List all files in `sources/` not yet in the map.
   - **Pass 1 — filename matching**: compare author surname and year from the bibliography entry against filenames.
   - **Pass 2 — metadata resolution**: for files with uninformative names (e.g., `main.pdf`, `paper.pdf`), read the first page to extract title, authors, and year, then match against unresolved keys.
7. Produce the citation map and update existing rows or append new ones to `sources/citation_map.md`:

   | Citation key | Author/year | Matched file | How matched | Status |
   |---|---|---|---|---|
   | howard2009consolidation | Howard 2009 | howard_2009_consolidation.pdf | Filename | Found |
   | somekey2020xyz | Author 2020 | — | — | **Not found** |

   Flag unresolved keys as "source not available locally" — do not verify those claims from memory.

### Step 2 — Verify each citation (delegated to subagents)

Delegate verification to **one subagent per unique source file**, running in parallel.

#### 2a. Group claims by source

For each unique source file (from the citation map), collect every claim in the section that cites it, with exact quoted text and line numbers.

#### 2b. Spawn verification subagents

For each unique source file, launch an Agent (subagent_type: `general-purpose`) with a prompt containing:

1. The **full file path** of the source PDF and the corresponding **OCR text file** in `sources/ocr/` (same stem, `.txt` extension).
2. The **exact claims** from the section that cite this source (with line numbers and surrounding sentence).
3. The **complete bibliography entry**. BibTeX entries are brace-delimited structures. Locate the `@type{key,` line with grep, then Read from that line with enough limit to capture the full entry through its closing `}`. Verify the entry ends with `}` before passing it to the subagent.
4. Instructions to use **both** the OCR text file and the PDF:
   - **OCR text** (via Read and Grep): for all statistics, quotes, specific wording. If missing, extract first: `.venv/bin/python utils/extract_text.py --file <pdf_path>`.
   - **PDF** (via Read): for figures, tables, charts, spatial layout, and visual elements.
   - **Hard rule**: all numerical claims and quoted language must be checked against the OCR text.
5. Instructions to read the **complete** source — all pages/sections, not just the abstract or introduction. Verification against partial reads is unreliable: a figure may appear only in a later section, a caveat may qualify an abstract-level claim, and the reference list is essential for identifying secondary citations.
6. Instructions to check each claim for:
   - **Factual accuracy**: does the statistic, finding, or claim match what the source actually says?
   - **Temporal accuracy**: is the data presented with the correct tense and time period? Do not present old data as current. If a source is from 2009 and the situation has materially changed since, flag it.
   - **Attribution level**: is this a primary source, or is the source citing another source? Flag secondary citations (citing B for a claim B attributes to A).
   - **Scope accuracy**: does the framing accurately represent the scope and caveats of the source finding?
   - **Denominator/base consistency**: when multiple statistics from the same source are cited, verify they share the same denominator or reference base. Numbers from different contexts within a paper can be individually accurate but misleading when combined.
   - **Caveats preservation**: check whether the source's own limitations, uncertainty ranges, or qualifications are reflected. A finding presented by the source as a lower bound, modelled estimate, or range should not appear as settled fact.
   - **Disconfirming evidence**: after locating the supporting passage, continue reading the surrounding section and actively look for statements that qualify, contradict, or limit the claim. Report any such passages. The absence of disconfirming evidence must be confirmed by reading, not assumed.
7. Instructions to check the bibliography entry: author, year, title, journal/publisher, DOI.
8. Instructions to return a **structured report** in this format for each claim:
   ```
   CLAIM: [exact text from section]
   SOURCE SAYS: [what the source actually states, with page number]
   LOCATOR: [most precise stable locator: Section/Chapter > Table/Figure > page]
   VERDICT: OK | FACTUAL ERROR | TEMPORAL ERROR | SCOPE MISMATCH | ATTRIBUTION ISSUE | CAVEATS MISSING | DISCONFIRMING EVIDENCE
   DETAIL: [explanation if not OK]
   BIB CHECK: OK | [specific error]
   SECTIONS READ: [list of all sections, pages, or page ranges consulted in the source]
   ```
   The `SECTIONS READ` field is mandatory. If it shows the agent consulted only the abstract or a single section of a multi-section source, the orchestrator must re-dispatch that agent with explicit instructions to read the missing sections before trusting its verdicts.

Launch subagents for independent sources **in parallel** (multiple Agent calls in the same message). For very large sources (>100 pages), direct the agent to the most likely relevant sections while still requiring it to check surrounding content for disconfirming evidence.

#### 2c. Collect and synthesize results

After all subagents return, collect their structured reports. Resolve any cross-source issues (e.g., claims combining figures from two sources with incompatible denominators) that individual agents could not detect in isolation.

### Step 3 — Orchestrator spot-check

For each non-OK verdict from a subagent that would drive a text change, the orchestrator must **independently verify** the subagent's key claim before accepting it. Grep the OCR text file for the specific number, phrase, or passage the subagent cites as evidence. If the grep result contradicts the subagent's report, re-read the relevant passage directly and resolve the discrepancy.

Do not propose corrections based on unverified subagent claims. This step is cheap (one grep per finding) and catches confident-but-wrong subagent readings that have occurred in past verifications.

### Step 4 — Check narrative structure

Review the section for structural issues:

- **Scope relevance**: does every paragraph serve the paper's thesis — that industrial agriculture causes ecological/social harms addressable (directly or contextually) by open-source controlled-environment production? Flag content outside this scope. Content is in scope if it (a) establishes a problem the proposed solution can address, or (b) provides necessary context for understanding why such a shift matters.
- **Consecutive citations**: if multiple consecutive sentences cite the same source, consolidate to a single cite — unless individual sentences contain independently verifiable specific claims a reader would want to check separately.
- **Redundancy**: does any claim repeat a statistic or finding from a previous section? Flag for `\ref{}` cross-reference.
- **Unsupported claims**: flag specific empirical claims (statistic, percentage, named entity) with no citation.
- **Unclear terminology**: flag technical terms introduced without definition, or defined more than once.
- **Logical flow**: flag non-sequiturs or argumentative gaps between paragraphs.

### Step 5 — Cross-section consistency check

Extract specific percentages, counts, and named quantities that are cited with a source in this section (e.g., "94%", "287 species", "50%"). Grep for each in the full `problem.tex` outside the target section. Ignore generic numbers (e.g., "two", "first") that could appear in unrelated contexts. Flag any that appear in other sections with different values, different denominators, or inconsistent framing. This catches contradictions invisible to section-level verification.

### Step 6 — Compile findings

Produce a numbered findings list in three categories:

- **Citation errors** (factual, temporal, attribution, scope)
- **Bibliography errors**
- **Narrative issues** (redundancy, flow, unsupported claims, terminology, cross-section inconsistencies)

**Every secondary citation flagged by a subagent must appear in this list as an attribution issue.** Do not filter out secondary citations based on perceived severity or "standard practice." The user decides which to pursue and which to accept — not the orchestrator.

Present this list to the user before making any changes.

Write findings to `sources/corrections.md`. Use stable IDs: `S[section#]-C[N]` for citation/bibliography errors, `S[section#]-N[N]` for narrative issues. Each entry uses this format:

    ### S[section#]-C[N]. [short title]
    **Status:** Pending
    **Category:** Citation | Bibliography | Narrative
    **Type:** Verify
    **Severity:** Major | Minor
    **Lines:** [line numbers in problem.tex]
    **Current text:**
    > [exact quoted text]
    **Issue:** [full description, including what the source actually says]
    **Source locator:** [page/section/table reference in the source PDF]

Narrative issues use the same format with the `N` prefix:

    ### S[section#]-N[N]. [short title]

Include a summary table at the section level:

    | # | Category | Type | Severity | Status | Summary |
    |---|----------|------|----------|--------|---------|

---

## Phase 2 — Correction (interactive, one at a time)

Work through citation errors, bibliography errors, and narrative issues one at a time. Skip expansion items (`S*-E*`) — those are handled by `/expand-section`.

1. State the issue clearly, referencing its ID (e.g., `S2.10-C1`).
2. Show the **current text** and the **proposed replacement**.
3. **Pinpoint citations**: every `\cite` command written or modified must include a locator: `\cite[locator]{key}`. Use the most precise stable locator (section > table/figure > page), e.g., `\cite[Section~5.5.2.5]{ipcc2019srccl}`, `\cite[Table~3]{epa2023methane}`.
4. **Self-verify the proposed text against the source before presenting it.** Apply the same standard you applied to the original claim:
   - **Locator accuracy**: every page, section, figure, or table reference in the proposed text must point to content that actually supports the specific claim. Confirm via Grep on the OCR text file. Do **not** copy locators from prior subagent reports without re-checking — page numbers and section numbers are easy to misattribute, and the previous subagent may have been working from a different version of the claim.
   - **No "plausibly true" content**: every term, framing, mechanism description, or quantitative claim in the proposed text must come from the cited source. Do **not** introduce textbook terminology, field-standard generalizations, or technical framings that are widely accepted but absent from the cited source. If you want to use such language: (a) cite a different source that does contain it, (b) rewrite to use the source's actual language, or (c) drop the claim.
   - The orchestrator's drafted text is not exempt from verification. Subagent reports describe what the source says; your replacement text must stay within those bounds. "Plausibly true based on field knowledge" is **not** sufficient — only "verified in the cited source" is.
5. Wait for explicit approval before applying.
6. Apply the approved edit using the Edit tool.
7. Confirm the edit was applied.
8. **Post-rewrite check**: if the edit was a rewrite (not just a locator addition), re-read the full paragraph and verify that adjacent citations and claims still make sense in the new context. If the rewrite broke something, flag it immediately as a new item.
9. Update the item's status in `sources/corrections.md`:
   - Approved and applied: `Pending` → `Applied`, update "Last updated" date.
   - User skips or declines: `Pending` → `Skipped`.
   - Update summary counts.
10. Move to the next issue.

Do **not** batch multiple edits. Do **not** apply any edit without explicit approval. Do **not** move to the next issue before confirming the previous edit landed.

When all items have been processed (Applied or Skipped), update the summary counts in `sources/corrections.md`.

---

## Hard constraints

- **Always verify numerical claims and quoted language against the OCR text files** using Grep and Read on `.txt` files. Use PDF for figures, tables, and visual elements. If an OCR text file is missing, run `.venv/bin/python utils/extract_text.py --file <pdf_path>` first.
- Never present old data as current.
- Never cite a secondary source when the primary is available or findable.
- Never remove a citation without replacing it with the correct source or removing the unsupported claim.
- Always verify the edit was actually written to the file before moving on.
- Always update `sources/corrections.md` after each item is processed.
