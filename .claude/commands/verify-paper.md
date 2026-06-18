# Verify Paper

Run a full citation, narrative, and expansion audit of the entire whitepaper by dispatching one subagent per section in parallel. Each subagent performs both verification and expansion analysis and returns structured findings. The orchestrator aggregates all findings into a corrections table. No edits are made during this command — corrections are applied afterwards using `/verify-section` and `/expand-section`.

## Usage

```
/verify-paper
```

No arguments needed.

---

## Orchestrator workflow

### Step 1 — Identify sections and build outline

1. Read `whitepaper/chapters/problem/problem.tex` and (if it exists) `whitepaper/chapters/solution/solution.tex`.
2. Extract the full list of `\subsection` and `\subsubsection` headings with their line ranges.
3. Build a **section outline** — one line per section summarizing its argument (e.g., `2.1 Land Use — cropland expansion, deforestation, habitat loss`). This outline is included in every subagent prompt for cross-section relevance scanning.

### Step 2 — Build and persist the citation map

The citation map is stored as `sources/citation_map.md`. On every run, load any existing map and update it incrementally — do not rebuild from scratch.

**2a — Load existing map (if present)**

Check whether `sources/citation_map.md` exists.
- If it does, read it. Extract the set of citation keys and filenames already recorded.
- If it does not, start with an empty map.

**2b — Diff against current state**

1. Read `whitepaper/bibliography.bib` and collect every entry's key, author surname(s), and year.
2. List all files in `sources/` (excluding `citation_map.md` and `verification_report.md`).
3. Identify what is new or changed since the last run:
   - **New citation keys**: keys in the bibliography not yet in the map.
   - **New files**: files in `sources/` not yet referenced in the map.
   - **Previously unresolved citations**: keys marked "Not found" — re-attempt if new files were added.

If none of these conditions are true, the map is current — skip to Step 3.

**2c — Pass 1: filename matching (no file reads)**

For each new or re-attempted citation key, match by comparing author surname and year against filenames. Classify each into:
- **Matched**: resolved via filename
- **Ambiguous file**: uninformative name (e.g., `main.pdf`, `paper.pdf`, arXiv ID)
- **Unresolved citation**: no file matched

**2d — Pass 2: metadata resolver subagent (only if ambiguous files remain)**

If ambiguous files exist and unresolved citations remain, spawn a single metadata resolver subagent:

> You are resolving the identity of PDF files with uninformative filenames. For each file listed below, read its first page and extract: title, author surname(s), and year of publication. Return a table and nothing else.
>
> Files to resolve:
> - `sources/[AMBIGUOUS_FILE_1]`
> - ...
>
> Return format:
> ```
> | Filename | Title (truncated) | Authors | Year |
> |---|---|---|---|
> | main.pdf | Seed industry consolidation... | Howard | 2009 |
> ```

Wait for the resolver to return, then match extracted metadata against unresolved keys.

**2e — Write the updated map**

Merge new and updated rows into the existing map and overwrite `sources/citation_map.md`.

Any key still unresolved is marked "Not found" — subagents must not verify those claims from memory.

This map is injected into every section subagent prompt. Section subagents do not perform their own file discovery.

### Step 3 — Dispatch subagents in parallel

Spawn one subagent per section using the Agent tool. All subagents are independent and must be launched in a single message (parallel dispatch). Pass each subagent a complete, self-contained prompt using the template below.

**Subagent prompt template:**

> You are performing a citation, narrative, and expansion audit of a section of an academic LaTeX whitepaper. Do not make any edits to any file. Your only job is to read, verify, and report findings.
>
> **Your section:** `[SECTION HEADING]` (lines [START]–[END] of `whitepaper/chapters/problem/problem.tex`)
>
> **Section outline** (for cross-section relevance scanning):
> ```
> [one line per section from Step 1.3]
> ```
>
> **Citation map** (do not perform your own file discovery — use this table):
>
> | Citation key | File to read |
> |---|---|
> | [KEY] | sources/[FILENAME] |
> | [KEY] | **Not available locally** |
> | ... | ... |
>
> ---
>
> **Part 1 — Read inputs**
> 1. Read lines [START]–[END] of `whitepaper/chapters/problem/problem.tex`.
> 2. Read `whitepaper/bibliography.bib` (for bibliography entry verification — do not use for file discovery).
>
> ---
>
> **Part 2 — Verification** (primary task — be thorough)
>
> For each citation key found in your section:
> 1. Look up the file in the citation map and read it from `sources/`. Also read the corresponding OCR text file in `sources/ocr/` (same stem, `.txt` extension). Use **both**: OCR text for statistics, quotes, and specific wording; PDF for figures, tables, and visual elements. **Hard rule**: all numerical claims and quoted language must be checked against the OCR text. If "Not available locally", flag and skip source verification.
> 2. Read the **complete** source, not just the abstract or cited section.
> 3. Check:
>    - **Factual accuracy**: does the statistic or claim match what the source actually says?
>    - **Temporal accuracy**: is old data presented as current?
>    - **Attribution level**: is this the primary source, or is the source citing another? Flag secondary citations.
>    - **Scope accuracy**: does the text accurately represent the source's scope and caveats?
>    - **Denominator/base consistency**: when multiple statistics from the same source are cited, verify they share the same denominator or reference base.
>    - **Caveats preservation**: are the source's own limitations, uncertainty ranges, or qualifications reflected?
>    - **Disconfirming evidence**: after finding the supporting passage, continue reading for statements that qualify, contradict, or limit the claim. Confirm absence of disconfirming evidence by reading, not by assumption.
> 4. Check the bibliography entry: author, year, title, journal, DOI — flag errors.
>
> **Part 3 — Narrative review**
>
> Review the section for structural issues:
> - **Scope relevance**: does every paragraph serve the paper's thesis — that industrial agriculture causes ecological/social harms addressable by open-source controlled-environment production? Flag content outside scope.
> - **Consecutive citations**: flag blocks citing the same source one-by-one that could be consolidated.
> - **Redundancy**: flag statistics or findings that appear to repeat content from another section.
> - **Unsupported claims**: flag specific empirical claims with no citation.
> - **Unclear terminology**: flag technical terms without definition, or defined more than once.
> - **Logical flow**: flag non-sequiturs or argumentative gaps.
>
> **Part 4 — Expansion scan** (secondary task — do not let this compromise Part 2)
>
> While reading sources for verification, also note:
> - **Target section gaps**: findings in the sources — beyond what's already cited — that would strengthen this section's argument.
> - **Cross-section relevance**: findings that could strengthen sections *other than* this one (use the section outline above to identify targets).
> - **Temporal staleness**: for sources older than 10 years, flag whether cited findings are time-sensitive (counts, rates, market shares — likely changed) or time-stable (constants, historical events, foundational theory). Flag time-sensitive findings that may need supplementing.
>
> ---
>
> **Part 5 — Return findings**
>
> Return a structured report in this exact format:
>
> ```
> SECTION: [heading]
> STATUS: [CLEAN | ISSUES FOUND]
>
> CITATION ERRORS:
> [numbered list, or "None"]
>
> BIBLIOGRAPHY ERRORS:
> [numbered list, or "None"]
>
> NARRATIVE ISSUES:
> [numbered list, or "None"]
>
> EXPANSION OPPORTUNITIES:
> [numbered list with gap description and suggested source/search direction, or "None"]
>
> CROSS-SECTION RELEVANCE:
> [numbered list: finding with locator → Section X.Y — reason, or "None"]
>
> TEMPORAL STALENESS FLAGS:
> [numbered list, or "None"]
> ```
>
> Do not make any edits. Do not propose fixes. Only report.

### Step 4 — Aggregate findings

Once all subagents have returned, compile their reports into a single master findings document saved to `sources/verification_report.md`. Structure it as:

```markdown
# Whitepaper Verification Report
Generated: [date]

## Summary
- Sections analysed: [N]
- Sections clean: [N]
- Sections with issues: [N]
- Verification items: [N citation errors / N bibliography errors / N narrative issues]
- Expansion items: [N expansion opportunities / N cross-section findings / N temporal flags]

## Findings by section

### [Section heading]
[subagent report pasted verbatim]

### [Section heading]
...
```

### Step 5 — Paper-wide narrative audit

After aggregating section-level findings, the orchestrator performs a holistic narrative review. This catches issues invisible to section subagents because they require seeing the full paper at once.

Read the complete `whitepaper/chapters/problem/problem.tex` and evaluate:

**5a — Argumentative arc**

Does the paper build a coherent, cumulative case? Each section should introduce a new dimension of the problem or deepen an earlier one. Flag any section that feels out of sequence — where a reader would need information from a later section to understand an earlier one.

**5b — Cross-section redundancy**

Identify any statistic, finding, or argument that appears in more than one section. Determine the natural home for each and flag others for `\ref{}` cross-references.

**5c — Terminology consistency**

Check that key terms are used consistently. Flag synonyms or variant phrasings for concepts already named elsewhere, or terms redefined with different scope.

**5d — Thesis connectivity**

For each section, state in one sentence how it connects to the paper's central thesis. Flag any section where this connection is absent, implicit, or requires inference the text does not support.

**5e — Scope discipline**

Flag passages that do not serve the argument: tangents into problems CEA cannot address without necessary context; extended discussion of other solutions; defensive arguments against positions the paper does not face.

**5f — Cross-section citation consistency**

Check whether any source is cited in multiple sections with inconsistent framing — e.g., a figure cited as "approximately 30%" in one section and "nearly a third" in another. Flag cases where two sections cite the same source for claims that are in tension.

**5g — Cross-section statistic consistency**

Grep the full paper for key percentages, counts, and named quantities. Flag any that appear in multiple sections with different values or different denominators.

Compile paper-wide findings into a separate section of the verification report:

```markdown
## Paper-wide narrative audit

### Argumentative arc
[findings or "No issues"]

### Cross-section redundancy
[numbered list or "None detected"]

### Terminology consistency
[numbered list or "No issues"]

### Thesis connectivity
[section-by-section one-liner, flagging weak links]

### Scope discipline
[numbered list or "No issues"]

### Cross-section citation consistency
[numbered list or "No issues"]

### Cross-section statistic consistency
[numbered list or "No issues"]
```

### Step 6 — Write corrections table

After aggregating all findings (section-level and paper-wide), write `sources/corrections.md` — a persistent checklist designed to be worked through across multiple sessions.

**Format:**

```markdown
# Corrections Table
Generated: [date]
Last updated: [date]

## Summary
- Total items: [N]
- Pending: [N] | Applied: [N] | Skipped: [N]
- Verification items: [N] (→ /verify-section)
- Expansion items: [N] (→ /expand-section)

## Section: [heading]

| # | Category | Type | Severity | Status | Summary |
|---|----------|------|----------|--------|---------|
| 1 | Citation | Verify | Major | Pending | [one-line summary] |
| 2 | Expansion | Expand | Minor | Pending | [one-line summary] |

### S[section#]-C1. [short title]
**Status:** Pending
**Category:** Citation | Bibliography | Narrative
**Type:** Verify
**Severity:** Major | Minor
**Lines:** [line numbers in problem.tex]
**Current text:**
> [exact quoted text]
**Issue:** [full description, including what the source actually says]
**Source locator:** [page/section/table reference in the source PDF]

---

### S[section#]-E1. [short title]
**Status:** Pending
**Category:** Expansion | Cross-section | Temporal
**Type:** Expand
**Lines:** [line numbers, or "New content"]
**Gap:** [one-sentence description of the argumentative gap]
**Suggested source:** [local file, search query, or named source]

---

### PW-1. [short title]
**Status:** Pending
**Category:** [from paper-wide audit]
**Type:** Verify | Expand
...
```

**Rules for the corrections table:**
- Use stable IDs: `S[section#]-C[N]` for verification items, `S[section#]-E[N]` for expansion items, `PW-[N]` for paper-wide items.
- The **Type** field indicates which command to use: `Verify` → `/verify-section`, `Expand` → `/expand-section`.
- All items start as `Pending`.
- Do NOT include proposed fixes — those are generated interactively during `/verify-section` and `/expand-section`.
- The table overview provides a scannable summary; the detailed entries contain everything needed to generate a fix later.

This file replaces `sources/verification_report.md` — do not write both.

### Step 7 — Present to user

Print the summary counts (verification items and expansion items by category and severity). List sections with pending items and their counts. Tell the user:

- Run `/verify-section [section]` to work through citation, bibliography, and narrative corrections.
- Run `/expand-section [section]` to work through expansion opportunities, cross-section findings, and temporal staleness flags.
- Recommend completing verification before expansion for each section.

---

## Hard constraints

- Subagents must not edit any file.
- All section subagents must be dispatched in a single parallel message, not sequentially.
- The orchestrator must not attempt corrections itself — its only output is the corrections table and summary.
- Subagents must not perform their own file discovery. They use only the citation map injected by the orchestrator.
- Citations marked "Not available locally" must be flagged as such — never verified from model memory.
- The corrections table (`sources/corrections.md`) is the single source of truth for outstanding work.
- Subagents must use **both** OCR text files and PDFs. All numerical claims and quoted language must be checked against the OCR text.
