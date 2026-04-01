---
name: vibecheck
description: Scan codebase for AI-generated code patterns (vibecode, AI slop, pseudocode, visual slop) using atom-based detection rules.
---

<!-- All your slop are belong to us -->

# vibecheck

Scan the current codebase for AI-generated code. You ARE the scanner — use your Grep tool to run the detection rules directly. No external dependencies needed.

## When to Activate

- User says "vibecheck", "slop check", "check for AI code", "is this vibecoded"
- Before merging a PR with AI-assisted code
- When reviewing unfamiliar code
- As part of `/review` Step 0 (vibecode detection)

## How to Run

### Step 1: Load the rules

Read `atoms.toml` to get the named building blocks. Read `rules.toml` to get the detection stanzas. Expand `{ATOM_NAME}` references in each rule's `pattern` field by substituting the atom's regex value.

### Step 2: Determine scope

- If the user specified files or a directory, scan that
- If running on a PR/diff, scan only changed files (`git diff --name-only`)
- Otherwise, scan the current working directory

### Step 3: Run rules via Grep

For each rule in `rules.toml`:

1. Expand the pattern by replacing `{ATOM}` references with values from `atoms.toml`
2. Run the expanded regex using your **Grep tool** with the rule's `files` glob
3. Collect matches with file path + line number + content

**Co-occurrence rules** (`mode = "co-occurrence"`): Count matches per file. Only report files where the count meets the `threshold`. A single "robust" in a comment is noise. Three banned words in one file is signal.

**Two-pass rules** (`two_pass = true`): The grep finds candidates. You then read the surrounding context (2-3 lines) and use judgment to confirm or dismiss. Do NOT report two-pass candidates without checking context.

### Step 4: Report findings

Group by severity. For each finding, report:

```
[SEVERITY] RULE_ID — Rule name
  file:line
  matching content (trimmed)
  notes (if relevant)
```

**Severity tiers:**
- **Critical** — blocks merge (phantom deps, hardcoded secrets, SQL injection)
- **High** — fix before deploy (phantom symbols, force unwrap, mock returns)
- **Medium** — fix this sprint (AI slop language, MARK saturation, restatement docs)
- **Low** — log it (section dividers, glassmorphism, bubbly radius)

### Step 5: Verdict

End with a one-line pass/fail:

- **PASS** — 0 critical, 0 high findings
- **FAIL** — any critical or high findings present

Include counts: `vibecheck: FAIL — 2 critical, 5 high, 12 medium, 3 low`

## Rule Categories

| Category | What It Catches | Atom Examples Used |
|----------|----------------|--------------------|
| `security` | Secrets, injection, RCE, XSS, disabled TLS | `{SECRET_ASSIGN}`, `{SQL_KEYWORD}` |
| `error-handling` | Empty catch, bare except, swallowed promises | Direct regex |
| `typescript` | `any` type, `@ts-ignore`, assertion chains | Direct regex |
| `python` | Mutable defaults, shell injection, ECB mode | `{FUNC_DEF_PY}` |
| `react` | Async useEffect, wrong router, exposed secrets | `{SECRET_NAME}` |
| `swift` | Force try/cast, UserDefaults secrets, print() | `{SECRET_NAME}` |
| `docker` | FROM :latest, privileged, hostPath / | Direct regex |
| `ai-llm` | Unpinned models, JSON.parse response, creds in prompts | `{LLM_MODEL}`, `{STRING_OPEN}` |
| `ai-slop` | LLM vocabulary, restatement comments, step-numbered, MARK saturation, "This function" docs | `{COMMENT}`, `{BANNED_WORD}`, `{DOC_NOUN_START}` |
| `pseudocode` | FOREACH/ENDFOR, ellipsis bodies, natural language bodies, mock returns | `{PSEUDO_KW}`, `{ELLIPSIS_BODY}`, `{NATURAL_LANG}` |
| `visual-slop` | Purple gradients, centered text, bubbly radius, hero copy, glassmorphism | `{AI_PURPLE_HEX}`, `{HERO_COPY}`, `{GLASSMORPHISM}` |

## Filtering

If the user requests a specific scope:

- `vibecheck security` → only run rules with `category = "security"`
- `vibecheck ai-slop` → only `ai-slop` category
- `vibecheck --severity high` → only critical + high rules
- `vibecheck <path>` → scan specific directory or file

## Key Design Decisions

- **Co-occurrence over individual matches** — banned words like "robust" and "comprehensive" are legitimate in isolation. Flag density, not presence
- **Two-pass for context-dependent rules** — restatement comments need the next line to confirm. Don't auto-report
- **Python excluded from G116 (ellipsis)** — `...` is valid Python for abstract methods and type stubs
- **MARK threshold at 5** — Swift `// MARK: -` is normal. Five in one file is AI saturation
- **Visual slop needs 3+ co-occurring items** — purple alone isn't slop. Purple + centered + bubbly radius = AI aesthetic

## Standalone CLI (for humans/CI)

The Python package at `src/vibecheck/` wraps the same rules for terminal use:

```bash
pip install -e .
vibecheck .              # scan current dir
vibecheck . --json       # CI-friendly output
vibecheck . -c ai-slop   # category filter
```

This is a separate distribution channel. The skill does not depend on it.
