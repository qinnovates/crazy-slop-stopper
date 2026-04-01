<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/header-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/header-light.svg">
    <img alt="vibecheck" src="docs/assets/header-dark.svg" width="700">
  </picture>
</p>

<p align="center">
  <a href="LICENSE.md"><img src="https://img.shields.io/github/license/qinnovates/vibecheck-slop-stopper?style=flat-square&color=FF453A" alt="License"></a>
  <img src="https://img.shields.io/badge/rules-78-FF9F0A?style=flat-square" alt="Rules">
  <img src="https://img.shields.io/badge/stacks-9-FFB74D?style=flat-square" alt="Stacks">
</p>

---

78 grep rules that detect AI-generated code. Runs as a **GitHub Action** on PRs, a **CLI** locally, or a **Claude Code skill** natively. Patterns are defined in human-readable TOML — no regex authoring required to contribute.

---

## Quick Start

### GitHub Action

```yaml
# .github/workflows/vibecheck.yml
name: vibecheck
on: [pull_request]
permissions:
  contents: read
  pull-requests: write
jobs:
  vibecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: qinnovates/vibecheck-slop-stopper@v1
```

### CLI

```bash
pip install git+https://github.com/qinnovates/vibecheck-slop-stopper.git
vibecheck .                    # scan current dir
vibecheck . --severity high    # critical + high only
vibecheck . -c ai-slop         # one category
vibecheck . --json             # CI output
vibecheck . --strict           # exit 1 on any finding
```

### Claude Code Skill

Install as a skill. Say `vibecheck` — Claude runs every pattern natively with its Grep tool. No Python, no ripgrep dependency.

---

## What's in the Repo

```
vibecheck-slop-stopper/
├── src/vibecheck/
│   ├── atoms.toml          ← 30+ named regex building blocks
│   ├── rules.toml          ← 78 detection rules as TOML stanzas
│   ├── patterns.py         ← compiler: atoms + rules → ripgrep regex
│   ├── scanner.py          ← runs compiled rules via ripgrep subprocess
│   └── cli.py              ← terminal UI (colors, JSON, filtering)
├── action.yml              ← GitHub Action (composite, runs on caller's quota)
├── SKILL.md                ← Claude Code skill definition
├── vibecode-detection.md   ← full reference doc (P1-P11, S01-S23, all grep rules)
├── CONTRIBUTING.md         ← how to add patterns
├── pyproject.toml          ← pip install config
└── .github/workflows/
    └── vibecheck.yml       ← dogfood: runs vibecheck on our own PRs
```

---

## Atom/Stanza Engine

**atoms.toml** defines reusable regex fragments by name:

```toml
[atoms]
COMMENT     = "(?:///|//|#|/\\*)"
BANNED_WORD = "(?i)\\b(?:delve|robust|comprehensive|leverage|utilize|seamlessly)\\b"
SWIFT       = "*.swift"
```

**rules.toml** composes atoms into detection stanzas:

```toml
[rule.G110]
name      = "LLM vocabulary density"
pattern   = "{COMMENT}.*{BANNED_WORD}"
files     = ["{SWIFT}", "*.{ts,js,py}"]
severity  = "medium"
category  = "ai-slop"
mode      = "co-occurrence"
threshold = 3
```

**patterns.py** compiles `{COMMENT}.*{BANNED_WORD}` into the full ripgrep regex at import time. Contributors write the TOML stanza — the compiler handles the rest.

---

## Detection Categories

### Security (G01-G20) — 14 rules
Hardcoded secrets, SQL injection, `eval()`, XSS, disabled TLS, `pickle.loads`, CORS wildcard, `rm -rf $VAR`, prompt injection.

### Error Handling (G21-G28) — 5 rules
Empty catch, bare except, swallowed promises, string throws.

### TypeScript (G41-G44) — 4 rules
`any` type, `@ts-ignore` without reason, non-null assertion chains, index signature backdoors.

### Python (G49-G66) — 5 rules
Mutable defaults, `DEBUG=True`, `subprocess shell=True`, `os.system`, AES ECB mode.

### React/Next.js (G76-G79) — 3 rules
Async useEffect, wrong router API, `NEXT_PUBLIC_` on secrets.

### Swift/iOS (G63-G107) — 6 rules
Force try/cast, `UserDefaults` for secrets, `NavigationView`, `nonisolated(unsafe)`, `print()`.

### Docker/K8s (G67-G73) — 4 rules
`FROM :latest`, `privileged: true`, `hostPath /`, `--reload` in Dockerfile.

### AI/LLM (G86-G88) — 3 rules
Unpinned model versions, `JSON.parse` on LLM response, credentials in prompts.

### AI Slop Language (G110-G145) — 19 rules
LLM vocabulary density (co-occurrence), restatement comments, markdown in comments, step-numbered comments, MARK template dumps, "This function/class" docstrings, param restating, section dividers, unicode box dividers, research citations in code, markdown tables in docstrings, file summary comments, generic TODOs, explanatory narration.

### Pseudocode (G115-G133) — 5 rules
`FOREACH`/`ENDFOR` keywords, bare ellipsis bodies, natural language function bodies, unicode arrows, hardcoded mock returns.

### Visual Slop (G120-G128) — 9 rules
AI purple gradients (hex + Tailwind), centered text density, bubbly border-radius, generic hero copy, emoji as design elements, colored left-border cards, default AI box-shadow, glassmorphism blur.

---

## Detection Modes

| Mode | How It Works | Example |
|------|-------------|---------|
| **Direct** | One regex match = one finding | G140: unicode box dividers |
| **Co-occurrence** | Counts per file, flags above threshold | G110: 3+ banned words in same file |
| **Two-pass** | Grep finds candidates, reviewer confirms | G112: restatement comment + check next line |

---

## Severity + Exit Codes

| Severity | Meaning | Action |
|----------|---------|--------|
| Critical | Secrets, injection, RCE | Blocks merge |
| High | Runtime crash, auth bypass, mock data | Fix before deploy |
| Medium | AI slop, pattern mismatch, stale docs | Fix this sprint |
| Low | Style drift, minor decoration | Log it |

| Exit | Meaning |
|------|---------|
| 0 | Passed — no critical/high |
| 1 | Failed — critical or high present |
| 2 | Error — rg not found, bad target |

---

## GitHub Action Config

```yaml
- uses: qinnovates/vibecheck-slop-stopper@v1
  with:
    severity: medium        # low | medium | high | critical
    category: ""            # ai-slop,security (comma-separated)
    fail-on: high           # high | critical | any | none
    comment: "true"         # post PR comment with findings
```

The action runs on the **caller's** GitHub Actions quota, not ours. Same as `actions/checkout` — the action definition is fetched and cached by GitHub.

---

## Roadmap

| Phase | Status | What |
|-------|--------|------|
| 1 | Done | Detection reference (vibecode-detection.md) |
| 2 | Done | CLI + atom/stanza TOML engine |
| 3 | Done | GitHub Action (PR scanning + comments) |
| 4 | Done | Claude Code Skill (SKILL.md) |
| 5 | Planned | GitHub App (one-click install, Dependabot-style) |
| 6 | Planned | `--quorum` flag for adversarial finding review |

---

## Credit

- [**ui-ux-pro-max**](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) — anti-pattern database for color/typography validation. P11 visual slop patterns sourced from its reasoning engine
- [**Quorum**](https://github.com/qinnovates/quorum) `--max --diverse` — cross-model adversarial review (Claude + Gemini 2.5 Pro + Codex/GPT-5.2). All patterns stress-tested by 9-agent panel
- [**gstack**](https://github.com/garrytan/gstack) — AI Slop Blacklist, banned vocabulary list, design scoring framework

---

## License

[MIT](LICENSE.md)

---

<p align="center">Built by <a href="https://github.com/qinnovates">qinnovates</a></p>
<p align="center"><sub>README template from <a href="https://github.com/qinnovates/repo-design-kit">repo-design-kit</a></sub></p>
