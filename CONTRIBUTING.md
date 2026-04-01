# Contributing to Vibecheck

Vibecheck aims to be the **universal record for anti-vibecode detection** — a community-maintained catalog of patterns that identify AI-generated code. Contributions are welcome.

## What We Accept

### New Detection Patterns (P-rules)

If you've identified a pattern that reliably distinguishes AI-generated code from human-written code, submit it as a new P-rule. Requirements:

- **Description:** What the pattern detects and why it's a signal
- **Cause:** Why LLMs produce this pattern
- **Check:** How to detect it (grep, AST analysis, or heuristic)
- **FP guard:** When this pattern appears in legitimate code
- **Severity:** Critical / High / Medium / Low with justification
- **Evidence:** Examples from real codebases (sanitized)

### New Grep Rules (G-rules)

Concrete regex patterns that detect vibecode. Requirements:

- **Valid ripgrep Rust regex** (no PCRE-only features like lookaheads)
- **Glob pattern** specifying which file types to scan
- **FP risk rating** (low/medium/high) with explanation
- **Two-pass guidance** if the regex needs semantic follow-up
- **Tested against** at least one real codebase to verify FP rate

### Stack Coverage Expansion

We have full coverage for TypeScript, Python, Swift, Docker/K8s, and CSS/Tailwind. Partial coverage for Go, Rust, AI/LLM. Gaps:

- **Java/Kotlin** — minimal coverage, needs framework-specific patterns (Spring, Android)
- **C/C++** — no coverage
- **Ruby/Rails** — no coverage
- **PHP/Laravel** — no coverage
- **Rust** — only 2 rules (G61-G62), needs expansion

### AI Visual Slop Patterns

The P11 blacklist covers common web patterns. We need:

- **Mobile-specific** visual slop (SwiftUI, Flutter, React Native)
- **Framework-specific** template tells (Next.js App Router, Nuxt, SvelteKit)
- **Design system** anti-patterns beyond Tailwind

## Submission Format

### For P-rules

```markdown
### P[N]: [Name] ([Severity])
[One-line description]
- **Cause:** [Why LLMs produce this]
- **Check:** [How to detect]
- **FP guard:** [When this appears in legitimate code]
- **Severity:** [Rating] — [justification]
```

### For G-rules

```markdown
| ID | Pattern | Regex | Glob | Severity | FP Risk | Notes |
|----|---------|-------|------|----------|---------|-------|
| G[N] | [Name] | `[regex]` | `[glob]` | [sev] | [fp] | [notes] |
```

## Quality Bar

- Every pattern must have a **false positive guard**. If it can't distinguish AI from human code in some contexts, document those contexts
- Regex must be **tested in ripgrep** (`rg '[pattern]' --glob '[glob]'`) before submitting
- Severity must be **justified**, not arbitrary
- FP risk must be **honest**. Underrating FP risk gets patterns disabled in production

## What We Don't Accept

- Patterns that flag **style preferences** without AI-specific signal (e.g., "uses tabs instead of spaces")
- Rules that require **AST parsing** without a grep-based first pass (we're grep-first, AST-optional)
- **Duplicate patterns** — check existing G-rules before submitting
- Patterns targeting **specific AI vendors** (e.g., "ChatGPT always does X") — patterns should be model-agnostic

## Process

1. **Fork** the repo
2. **Add** your pattern to `vibecode-detection.md` in the appropriate section
3. **Update** the stack coverage table if you're adding coverage for a new stack
4. **Test** your regex with `rg` against real code
5. **Open a PR** with:
   - What pattern you're adding
   - Why it's a reliable signal
   - FP rate from your testing (approximate is fine)

## Code of Conduct

Be constructive. The goal is accuracy, not gatekeeping. If you disagree with a pattern's severity or FP rating, open an issue with evidence.

---

<p align="center">Built by <a href="https://github.com/qinnovates">qinnovates</a></p>
