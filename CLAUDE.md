# vibecheck-anti-vibecode

## What This Is

Vibecode detection reference — patterns and grep rules for identifying AI-generated code before it ships. Not a runtime tool (yet). The core artifact is `vibecode-detection.md`.

## Repository Structure

```
vibecheck-anti-vibecode/
├── vibecode-detection.md    # Core detection reference
├── docs/assets/             # SVG headers (Red Orange skin)
├── README.md
├── LICENSE.md               # MIT
├── CLAUDE.md                # This file
└── .gitignore
```

## Key Concepts

- **P1-P11:** Core detection patterns (phantom code, pattern drift, AI slop, pseudocode, visual slop)
- **S01-S23:** Auto-fail security patterns (always Critical, block merge)
- **G01-G133:** Grep rules with ripgrep Rust regex syntax
- **Co-occurrence model:** P9 banned words flag density (3+ per file), not individual matches
- **Two-pass checks:** Some rules require a first grep pass + semantic follow-up

## Regex Syntax

All patterns use **ripgrep Rust regex**:
- Alternation: `|` (not `\|`)
- No PCRE lookaheads/lookbehinds
- Multiline requires explicit flag
- In markdown tables, `\|` is escaped pipe for table rendering — the actual regex uses `|`

## Review History

- v1: Initial patterns (P1-P7)
- v2: Quorum --max --diverse review (regex fixes, Swift rules, Step 0 batching)
- v3: Python crypto rules, Next.js Server Actions
- v4: AI slop (P9), pseudocode (P10), visual slop (P11), Quorum re-review with Gemini + Codex
