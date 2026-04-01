---
name: vibecheck
description: Detect AI-generated code patterns (vibecode, AI slop, pseudocode, visual slop) in any codebase using ripgrep-based detection rules.
---

<!-- All your slop are belong to us -->

# vibecheck

Scan a codebase for AI-generated code patterns. 72 rules across 11 categories, compiled from human-readable TOML stanzas.

## When to Use This Skill

- Before merging a PR that may contain AI-generated code
- As a pre-commit or CI check
- When reviewing code from contributors you haven't worked with
- When onboarding a codebase you suspect was vibecoded

## Quick Start

```bash
# Scan current directory
vibecheck .

# Only critical and high severity
vibecheck . --severity high

# Show matching lines
vibecheck . --context

# Filter to AI slop detection only
vibecheck . --category ai-slop

# JSON output for CI pipelines
vibecheck . --json

# Strict mode: exit 1 on ANY finding
vibecheck . --strict
```

## Categories

| Category | What It Catches |
|----------|----------------|
| `security` | Hardcoded secrets, SQL injection, eval, XSS, disabled TLS |
| `error-handling` | Empty catch, bare except, swallowed promises, string throws |
| `typescript` | `any` type, `@ts-ignore`, non-null chains, index backdoors |
| `python` | Mutable defaults, shell injection, DEBUG=True, ECB mode |
| `react` | Async useEffect, Pages Router in App Router, exposed secrets |
| `swift` | Force try/cast, UserDefaults secrets, NavigationView, print() |
| `docker` | FROM :latest, privileged containers, hostPath /, --reload |
| `ai-llm` | Unpinned models, JSON.parse LLM response, credentials in prompts |
| `ai-slop` | LLM vocabulary density, restatement comments, step-numbered comments, MARK saturation, "This function" docstrings |
| `pseudocode` | FOREACH/ENDFOR keywords, ellipsis bodies, natural language function bodies, mock returns |
| `visual-slop` | AI purple gradients, centered text density, bubbly radius, generic hero copy, glassmorphism |

## Detection Modes

### Direct Match
Most rules fire on individual regex matches. One match = one finding.

### Co-occurrence
Rules marked `mode = "co-occurrence"` count matches per file. A single "robust" in a security comment is fine. Three banned LLM words in the same file is a signal.

### Two-pass
Rules marked `two_pass = true` produce candidates that need semantic follow-up. The grep finds the pattern; a human (or reviewer) confirms whether it's a real finding.

## Architecture

```
atoms.toml  →  Named regex building blocks ({COMMENT}, {BANNED_WORD}, etc.)
rules.toml  →  72 rules as readable stanzas: pattern = "{COMMENT}.*{BANNED_WORD}"
patterns.py →  Compiler: expands atoms to ripgrep regex at import time
scanner.py  →  Runs compiled rules via ripgrep subprocess, applies co-occurrence filtering
cli.py      →  Terminal UI with severity colors, JSON mode, category filtering
```

Rules are TOML, not Python. Contributors add patterns by writing:

```toml
[rule.G999]
name      = "My new pattern"
pattern   = "{COMMENT}.*my_regex_here"
files     = ["{SWIFT}"]
severity  = "medium"
fp_risk   = "low"
category  = "ai-slop"
notes     = "Why this matters"
```

No Python required. The compiler handles atom expansion.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Passed — no critical or high findings |
| 1 | Failed — critical or high findings present (or `--strict` with any findings) |
| 2 | Error — ripgrep not found, invalid target, etc. |

## Requirements

- Python 3.10+
- [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) installed and on PATH
