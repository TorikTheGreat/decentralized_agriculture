# Vibe Research: A workflow for AI-assisted academic writing

This document describes a workflow for producing a research-backed academic document — a whitepaper, policy brief, literature review, or similar — using Claude Code as a collaborative research and writing assistant. The process is designed to keep the human in control of argument and judgment while delegating the mechanical work of sourcing, drafting, and verification to the model.

The workflow has four phases. Each builds on the previous one.

---

## Phase 1 — Brief the model on your argument

Before asking Claude to write anything, give it a complete picture of what you already know and what you want to say. This is the most important step. The quality of the output depends almost entirely on the quality of this brief.

A good brief includes:

- **Your understanding of the problem**: what is the phenomenon, why does it matter, what is the mechanism you believe is at work?
- **Your proposed solution or thesis**: what argument does the document need to make?
- **Research you have already done**: papers you've read, statistics you trust, claims you want to anchor the document to.
- **Your sources**: actual PDFs or links, not just titles. Place them in a dedicated directory (e.g., `temp_sources/`) so Claude can read them.
- **The structure you want**: a section outline or table of contents. Claude will follow your architecture, not invent its own.

The model is not a research director — you are. The brief is where you exercise that role. Claude's job from this point on is to operationalise your argument, not to choose one.

---

## Phase 2 — Full document generation pass

With the brief and structure in place, ask Claude to do a single full pass of the entire document. In this pass it should:

- Follow your narrative structure section by section.
- Find supporting sources for each claim — either from the materials you provided or by searching the web.
- Fill in gaps in sections where your manual research was incomplete.
- Write in a consistent register appropriate for the document type.

This produces a complete first draft with citations. It will contain errors — temporal inaccuracies, secondary citations used as primary sources, claims slightly misrepresented in framing. That is expected and handled in Phase 3. The goal of Phase 2 is a complete, citable skeleton, not a finished document.

**Practical note:** For a long document, ask Claude to work section by section so you can monitor the output and redirect if a section goes off-narrative before it has propagated through the rest of the document.

---

## Phase 3 — Supervised section-by-section verification

This is the core quality control phase. Each section is verified against its source PDFs, and every proposed correction is presented to you for approval before it is applied to the file.

Run this using the `/verify-section` command (see `.claude/commands/verify-section.md`):

```
/verify-section "Section name or number"
```

For each section, Claude runs two sub-phases:

### Analysis (automated)

Claude reads the section, reads every cited source, and checks:

- **Factual accuracy**: does each statistic or claim match what the source actually says?
- **Temporal accuracy**: is old data presented as current? A source from 2009 cannot be cited as evidence of the present situation if the field has changed.
- **Attribution level**: is this a primary source, or is the source itself citing someone else? Citation laundering — citing B for a claim B attributes to A — is flagged and corrected.
- **Scope accuracy**: does the text accurately represent the caveats and scope of the finding?
- **Bibliography entries**: author, year, journal, DOI — all verified.
- **Narrative structure**: consecutive citations to the same source, redundant statistics already covered in an earlier section, unsupported empirical claims, undefined terminology, argumentative gaps.
- **Expansion opportunities**: spots where the argument is thin or relies on a single source, with suggestions for what additional research would strengthen it. Suggestions follow a strict priority order: local uncited sources first, then search queries, then named canonical sources only when confident. The model never fabricates a paper title.

The analysis phase produces a numbered findings list in four categories: Citation errors, Bibliography errors, Narrative issues, Expansion opportunities.

### Correction (interactive)

Claude works through the first three categories one item at a time:

1. States the issue.
2. Shows current text and proposed replacement.
3. Waits for your approval.
4. Applies the edit and confirms it landed before moving on.

Expansion opportunities are presented separately at the end, as a list for you to act on at your discretion.

**Why the approval loop matters:** Each correction changes the document. Some corrections involve judgment calls — a source may be outdated but the best available; a claim may be imprecise but deliberately so for readability. The loop ensures those decisions stay with you.

---

## Phase 4 — Autonomous full-paper audit

Once you have verified the sections you were most uncertain about, run a full-paper audit using the `/verify-paper` command (see `.claude/commands/verify-paper.md`):

```
/verify-paper
```

This command works differently from `/verify-section`. Rather than running interactively, it:

1. Reads the full document and identifies every section with its line range.
2. Dispatches one independent subagent per section **in parallel** — each subagent has its own context window and runs the full analysis protocol against its assigned section simultaneously.
3. Aggregates all findings into a single verification report saved to `temp_sources/verification_report.md`.
4. Presents you with a summary of which sections are clean and which have issues.

You then run `/verify-section` on each section that has issues to apply corrections interactively.

### Why subagents instead of a single long session?

A long document verified in a single session will eventually exhaust the model's context window — older sections get compressed out of working memory before the session ends, and the quality of analysis degrades. Subagents solve this by giving each section its own isolated context: the subagent for section 2.3 has no knowledge of and no interference from section 2.7. The orchestrating session only ever handles the aggregated summary, which is small.

The tradeoff is that subagents cannot catch cross-section issues on their own — they can only flag that a claim "appears to repeat something from an earlier section," not confirm it definitively. Cross-section redundancy review still benefits from a human pass after the automated audit.

---

## File structure

```
.claude/
  commands/
    verify-section.md     # Interactive single-section verification skill
    verify-paper.md       # Parallel full-paper audit skill

temp_sources/             # Source PDFs for citation verification
  [author_year_keyword.pdf]
  ...
  verification_report.md  # Generated by /verify-paper

whitepaper/
  bibliography.bib
  chapters/
    ...
```

---

## Principles behind the workflow

**The model drafts; you judge.** Claude handles the mechanical work — finding sources, checking claims, proposing edits. You decide what the argument is, whether a correction is right, and when to expand a section. The workflow is designed so that no change to the document happens without your explicit approval.

**Verification is not optional.** LLM-generated citations are frequently wrong in subtle ways: slightly misrepresented statistics, secondary sources used as primary, data presented without its original caveats. The verification phase is not a polish step — it is the step that makes the document academically defensible.

**Source grounding over model memory.** At every stage, Claude is asked to work from files you have provided rather than from its training knowledge. This is especially important for citation suggestions: the model is instructed to suggest search directions rather than paper titles when it cannot ground a suggestion in a local file or a verifiable canonical source. A search direction is always honest; a hallucinated citation is always a liability.

**Skills preserve the workflow across sessions.** The `/verify-section` and `/verify-paper` commands are saved as project-level skill files. Starting a new Claude Code session in this project gives you the full workflow immediately, without needing to re-explain the process in every conversation.
