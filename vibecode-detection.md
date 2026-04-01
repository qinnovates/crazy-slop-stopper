# Vibecode Detection Reference (v2 — Quorum-reviewed)

## Definition

**Vibecode** is code that appears functional in isolation but does not integrate with
the actual codebase. It compiles (maybe) but calls nothing real, imports nothing installed,
and follows patterns from a different project or a hallucinated API.

This reference supports Step 0 of `/review code`. It defines 11 core detection patterns
(P1-P11), 23 auto-fail security patterns, and grep rules for automated scanning.

**Important — grep rules use ripgrep (Rust regex engine):**
- Alternation uses `|` NOT `\|` (literal pipe)
- Lookaheads `(?!...)` are NOT supported — use two-pass checks instead
- Multiline patterns require `multiline: true` in the Grep tool
- Globs: use separate Grep calls per glob, not comma-separated

---

## Stack Coverage

| Stack | Rules | Coverage |
|-------|-------|----------|
| TypeScript/React/Next.js | G41-G45, G76-G83, G110-G113, G120-G126 | Full |
| Python (general + Django/Flask + crypto) | G49-G58, G65-G68a, G110-G113, G115-G118 | Full |
| Swift/iOS | G63-G64, G101-G108, G110-G113, G115-G118 | Full |
| Go | G59-G60, G110-G113, G115-G118 | Partial (G59 high FP — use with semantic follow-up) |
| Rust | G61-G62, G110-G113, G115-G118 | Minimal |
| Docker/K8s/IaC | G67-G75 | Full |
| AI/LLM | G86-G88 | Partial |
| CSS/Tailwind/SwiftUI (visual) | G120-G126 | New — visual slop detection |
| Cross-language (slop + pseudocode) | G110-G118 | Full — applies to all source |

---

## Step 0 Execution Guidance

**Batch to stay fast.** Step 0 should NOT make 200+ tool calls. Target: ~30-40 max.

1. **Read manifest ONCE** (1 Read), match all imports against it in-context
2. **Batch grep patterns** by file type — combine rules into 1-2 Grep calls per glob group
3. **Only verify NEW imports/calls** in the diff — modified files with unchanged imports are proven
4. **Skip test files and docs** for P6 (orphan) and most grep rules
5. **Path exclusions:** Exclude `**/test*/**`, `**/*spec*/**`, `**/*stories*/**`, `**/docs/**`,
   `**/__mocks__/**`, `**/fixtures/**` from auto-fail security scan (not from P1-P4)
6. **If diff > 30 files:** Run 0f (auto-fail security) fully, sample P1-P4 on new files only,
   note "partial vibecode scan due to diff size"

**Short-circuit always completes 0f.** Even if 3+ Critical P1-P4 findings trigger short-circuit,
the auto-fail security scan (0f) runs to completion.

---

## Core Detection Patterns (P1-P11)

### P1: Phantom Dependency (Critical)
Import references a package not in the project's dependency manifest.
- **Cause:** LLM inventing plausible package names (19.7% hallucination rate in Python/JS)
- **Check:** Read the nearest manifest by walking up from the changed file's directory:
  - JS/TS: `package.json` (manifest) → `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` (lock)
  - Python: `pyproject.toml` / `requirements.txt` / `setup.cfg` (manifest) → `pip.lock` / `poetry.lock` (lock)
  - Go: `go.mod` (manifest) → `go.sum` (lock for transitive deps)
  - Rust: `Cargo.toml` (manifest) → `Cargo.lock` (lock)
  - Swift SPM: `Package.swift` (manifest) → `Package.resolved` (lock)
  - Swift Xcode: `Podfile` / `Cartfile` (manifest) → `Podfile.lock` / `Cartfile.resolved` (lock)
  - Monorepo: find nearest manifest, then check root workspace config if not found
- **FP guard:** Check lock file for transitive deps before flagging.

### P2: Phantom Module (Critical)
Import references an internal file path that does not exist.
- **Cause:** LLM inventing plausible paths based on naming conventions
- **Check:** Glob for the exact file path
- **FP guard:** File may be generated at build time (check build scripts, codegen config)

### P3: Phantom Symbol (High)
Import or call references a function/class/constant not exported by the target module.
- **Cause:** LLM generating plausible function names from the module's domain
- **Check:** Grep the target file for the symbol definition (export, pub fn, def, func, class)
- **FP guard:** Symbol may be re-exported from barrel/index files
- **Limitation:** Cannot verify methods on stdlib/framework instances (e.g., hallucinated
  `.expire()` on `OrderedDict`). These require LLM knowledge, not codebase grep.

### P4: Signature Mismatch (High)
Function call has wrong argument count, wrong types, or wrong parameter names.
- **Cause:** LLM working from stale or hallucinated API signatures
- **Check:** Read the function definition, compare parameter list
- **FP guard:** Variadic functions, optional parameters, overloads

### P5: Pattern Alien (Medium)
Code uses naming conventions, error handling, or architecture patterns that don't match
the surrounding codebase.
- **Cause:** LLM defaulting to generic patterns instead of reading the project
- **Check:** Read 2-3 adjacent files, compare style and structure
- **Indicators:** Generic names (data, result, handler, utils), wrong casing, different
  error types, different logging library, framework conventions from wrong framework
- **Swift/iOS indicators:** UIKit patterns in SwiftUI project (UIViewController, storyboard refs),
  Combine sink chains where async/await is standard, delegate patterns where @Environment is used,
  VIPER/MVC in a feature-grouped MVVM project
- **Next.js indicators:** Pages Router mental model in App Router (props on page components,
  `router.query` instead of `useSearchParams()`, `getServerSideProps` style data fetching)

### P6: Orphan Code (High)
New code that nothing in the system references.
- **Cause:** LLM generating a complete file without wiring it into the application
- **Check:** Grep the codebase for imports/references to the new file or its exports
- **Exceptions (do NOT flag as orphan):**
  - Test files (`*Test*`, `*spec*`, `*_test.*`)
  - Entry points (`main.*`, `index.*`, `App.*`)
  - Filesystem-routed files: `pages/**`, `app/**/page.*`, `app/**/route.*`, `app/**/layout.*`,
    `app/**/error.*`, `app/**/loading.*`, `app/**/not-found.*`, `app/**/template.*`
  - Config files at project root
  - Lambda/serverless handlers registered via config (e.g., `serverless.yml`)

### P7: God File Dump (Medium)
Single file containing multiple responsibilities that should be split.
- **Cause:** LLM dumping an entire feature into one file
- **Check:** File exceeds 300 lines AND contains 3+ unrelated public types/classes
- **Exception:** Single-purpose scripts, Redux reducers, and complex UI components that are
  logically cohesive (P7 is an advisory, not an auto-fail)

### P8: Stub/Placeholder Code (Medium) — NEW
Code contains LLM laziness markers where real implementation should exist.
- **Cause:** LLM generating skeleton code and moving on
- **Check:** Grep for: `// ... rest of code`, `// implement`, `/* TODO */`, `pass  # placeholder`,
  `raise NotImplementedError`, `return nil // TODO`, `fatalError("not implemented")`
- **Severity:** Medium if function has callers; High if it's in a code path that runs in production

### P9: AI Slop Language (Medium)
Comments, docstrings, error messages, or UI copy containing telltale LLM verbal tics.
- **Cause:** LLM defaulting to its trained voice instead of matching the project/team voice
- **Check:** Grep for banned vocabulary in comments and strings (see G110-G113)
- **Indicators:**
  - **Banned words** (30+): delve, crucial, robust, comprehensive, nuanced,
    furthermore, moreover, additionally, pivotal, landscape, tapestry, underscore, foster,
    showcase, intricate, vibrant, fundamental, significant, interplay, utilize, leverage,
    seamlessly, streamline, facilitate, endeavor, paramount, bolster, harness, meticulously
  - **Detection model:** Co-occurrence, NOT individual matches. A single "robust" in a
    security comment is fine. Flag when **3+ banned words appear in the same file's
    comments/docstrings**, or when a single comment contains **2+ banned words**.
    Individual matches are noise; density is the signal
  - **Banned phrases:** "here's the kicker", "here's the thing", "plot twist",
    "let me break this down", "the bottom line", "make no mistake", "it's worth noting",
    "in order to" (use "to"), "as needed" (vague), "feel free to" (in code comments)
  - **Restatement comments:** comment says exactly what the next line of code does
    (`// Set the name` above `name = value`)
  - **Over-documentation:** docstrings on trivial getters/setters, constructors with
    one assignment, or functions whose name already describes the behavior
  - **Markdown in code comments:** `**bold**`, `- bullet`, `## heading` inside source code
  - **Emoji in source code:** unless the project explicitly uses emoji (rare)
- **FP guard:** Technical docs, user-facing copy, and i18n strings may legitimately use
  some of these words. Flag only in code comments, docstrings, and log messages
- **Severity:** Medium. High if in user-facing UI copy (degrades brand voice)

### P10: Pseudocode (High)
Code that reads like English instructions rather than compilable/executable implementation.
- **Cause:** LLM generating a sketch instead of real code, or truncating implementation
  with natural-language descriptions of what should happen
- **Check:** Grep for pseudocode markers (see G115-G118)
- **Indicators:**
  - Pseudocode keywords: `FOREACH`, `ENDFOR`, `ENDIF`, `BEGIN`, `END`, `REPEAT UNTIL`,
    `PRINT`, `INPUT`, `PROCEDURE`, `CALL` (in non-SQL contexts)
  - Natural language in function bodies: `// do something here`, `// check if valid`,
    `// loop through items`, `// handle the response`, `// process data`
  - Arrow notation in code: `→`, `←`, `⟶` used as assignment/flow operators
  - Ellipsis as implementation: `...` or `// ...` or `/* ... */` as the function body
  - English-sentence variable names: `the_result_of_calling_api`, `what_we_got_back`
  - Mix of real syntax and prose: half the function is code, half is English
- **FP guard:** Comments describing complex algorithms are fine. The flag is when
  the *implementation itself* is pseudocode, not when comments explain intent
- **Severity:** High. AI has no excuse for pseudocode — it can write real code.
  Critical if in a production code path

### P11: AI Visual Slop (Medium)
UI code that produces generic, recognizably AI-generated visual patterns.
- **Cause:** LLM defaulting to its most common training examples (SaaS templates,
  tutorial UIs, landing page generators)
- **Check:** Grep for visual slop markers in CSS/Tailwind/SwiftUI (see G120-G126)
- **Indicators (10-item AI Slop Blacklist, adapted from gstack):**
  1. **Purple/violet/indigo gradient backgrounds** — hex values in `#6366f1`–`#8b5cf6` range,
     or blue-to-purple `linear-gradient`. The single most recognizable AI color choice
  2. **The 3-column feature grid** — icon-in-colored-circle + bold title + 2-line description.
     Most recognizable AI layout pattern
  3. **Icons in colored circles** as section decoration (SaaS starter template look)
  4. **Centered everything** — `text-align: center` on >60% of text containers
  5. **Uniform bubbly border-radius** — same large radius (16px+) on all elements
  6. **Decorative blobs, floating circles, wavy SVG dividers** — no functional purpose
  7. **Emoji as design elements** — rocket emoji bullets, sparkle headers
  8. **Colored left-border on cards** — `border-left: 3px solid <accent>`
  9. **Generic hero copy** — "Welcome to [X]", "Unlock the power of...",
     "Your all-in-one solution for...", "Revolutionize your..."
  10. **Cookie-cutter section rhythm** — hero → 3 features → testimonials → pricing → CTA
- **FP guard:** Individual items are not auto-fails. Flag when 3+ items co-occur.
  Some legitimate designs use centered text or rounded corners — context matters
- **Severity:** Medium for internal tools. High for user-facing products where brand
  identity matters. Flag as "AI-generated aesthetic detected" with specific items

---

## Auto-Fail Security Patterns (23 patterns, always Critical)

These block merge unconditionally. No context makes them acceptable.

| ID | Pattern | Why Auto-Fail |
|----|---------|---------------|
| S01 | Hardcoded API key/secret in source | Irrevocable without rotation. Every clone is compromised |
| S02 | SQL string interpolation/concatenation | Injection exploitable by unauthenticated users |
| S03 | `eval()`/`new Function()` with dynamic input | Remote code execution |
| S04 | JWT `none` algorithm accepted | Complete auth bypass with zero tooling |
| S05 | Unsanitized `dangerouslySetInnerHTML` / `innerHTML` with user data | Stored XSS, wormable |
| S06 | `Math.random()` for session/auth tokens | Predictable tokens, session hijack |
| S07 | Path traversal (uncanonicalized user filename) | File system boundary violation |
| S08 | Hardcoded encryption key in source | Defeats all encryption |
| S09 | IDOR (no ownership check on resource access) | Trivially exploitable by any authenticated user |
| S10 | `pickle.loads` / insecure deserialization of user input | Arbitrary code execution |
| S11 | Django/Flask SECRET_KEY hardcoded or default `"dev"` | Session forgery |
| S12 | `render_template(user_input)` / SSTI | Server-side template injection to RCE |
| S13 | Committed `.env` file with real secrets | Concentrated secret exposure |
| S14 | Credentials embedded in LLM prompt | Secret sent to third-party provider |
| S15 | SSH private keys baked in Docker image | Extractable from any image pull |
| S16 | K8s `hostPath: /` mount | Container escape to host filesystem |
| S17 | K8s `privileged: true` | Full container escape |
| S18 | Client-side-only auth gate | No server-side authorization = no authorization |
| S19 | AI-removed auth middleware (hallucinated security bypass) | The defining vibecode security failure |
| S20 | `rm -rf $VAR` with unset/unvalidated variable | Catastrophic data loss |
| S21 | Raw SQL via `cursor.execute(f"...")` | SQL injection (ORM bypass variant) |
| S22 | `chmod 777` in production Dockerfile | World-writable application directory |
| S23 | `process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0'` in production | MITM via disabled TLS verification |

**Note:** These are first-pass grep detections, not SAST replacements. For production
security scanning, use dedicated tools (Semgrep, Bandit, ESLint security plugins).

---

## Grep Detection Rules

All regexes below are valid **ripgrep Rust regex syntax**. No PCRE-only features.
Rules marked [multiline] require `multiline: true` in the Grep tool.

### Security-Critical

| ID | Pattern | Regex | Glob | FP Risk |
|----|---------|-------|------|---------|
| G01 | Hardcoded API key | `(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*["'][a-zA-Z0-9_/+\-]{20,}["']` | `*.{ts,js,py,swift,kt,go,rs,java}` | medium |
| G02 | SQL f-string (Python) | `f["'](SELECT|INSERT|UPDATE|DELETE)` | `*.py` | low |
| G03 | SQL template literal (JS) | `` `(SELECT|INSERT|UPDATE|DELETE).*\$\{ `` | `*.{ts,js}` | low |
| G04 | eval() with variable | `eval\s*\([^"')]+\)` | `*.{ts,js,py}` | low |
| G05 | new Function() with variable | `new\s+Function\s*\([^"')]+\)` | `*.{ts,js}` | low |
| G06 | innerHTML with variable | `\.innerHTML\s*=\s*[^"'<\s]` | `*.{ts,js,jsx,tsx}` | medium |
| G07 | dangerouslySetInnerHTML | `dangerouslySetInnerHTML` | `*.{jsx,tsx}` | medium |
| G08 | Disabled TLS (Node) | `NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['"]0['"]` | `*.{ts,js}` | low |
| G09 | Disabled TLS (Python) | `requests\.\w+\(.*verify\s*=\s*False` | `*.py` | medium |
| G10 | pickle.loads | `pickle\.loads?\(` | `*.py` | medium |
| G11 | Hardcoded encryption key | `(?i)(encrypt|cipher|aes)\s*[:=]\s*["'][^"']{8,}["']` | `*.{ts,js,py,go,rs,java,swift,kt}` | medium |
| G12 | Secret in Docker ENV | `(?i)(password|secret|token|api_key)\s*=\s*[^$\s{]` | `docker-compose*.yml` | low |
| G13 | Secret in Dockerfile | `(?i)(password|secret|key)\s*[=:]\s*["']?[a-zA-Z0-9]` | `Dockerfile*` | medium |
| G14 | SSH key in Docker | `id_rsa|id_ed25519` | `Dockerfile*` | low |
| G15 | chmod 777 | `chmod.*777` | `Dockerfile*` | low |
| G16 | MD5 for passwords | `(?i)md5.*password|password.*md5` | `*.{ts,js,py}` | medium |
| G17 | CORS wildcard | `allow_origin.*["']\*["']|Access-Control-Allow-Origin.*\*` | `*.{ts,js,py,go,java}` | medium |
| G18 | Mass assignment ORM | `\.(update|create)\(req\.body\)` | `*.{ts,js}` | low |
| G19 | rm -rf with variable | `rm\s+-rf\s+\$` | `*.{sh,bash,zsh}` | low |
| G20 | Raw user input in prompt | `f["'].*\{user_input\}|f["'].*\{request\.` | `*.py` | medium |

### Error Handling

| ID | Pattern | Regex | Glob | Severity | FP Risk | Notes |
|----|---------|-------|------|----------|---------|-------|
| G21 | Empty catch (JS) | `catch\s*\([^)]*\)\s*\{\s*\}` | `*.{ts,js,jsx,tsx}` | high | low | |
| G22 | Empty except (Python) | `except.*:\s*$` | `*.py` | high | low | Two-pass: match except line, then check next line is `pass` or `...` |
| G23 | console.log error handler | `catch\s*\([^)]*\)\s*\{` | `*.{ts,js,jsx,tsx}` | high | medium | Two-pass ONLY: find catch blocks, then check for console.log inside. Do NOT grep `console.log` alone. |
| G24 | printStackTrace (Java) | `\.printStackTrace\(\)` | `*.{java,kt}` | high | low | |
| G25 | Catch-swallow promise | `\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)` | `*.{ts,js}` | high | low | |
| G26 | String throw | `throw\s+['"]` | `*.{ts,js}` | high | low | |
| G27 | 200 on error | `status\(200\).*json\(.*error` | `*.{ts,js}` | high | high | Two-pass recommended: check context |
| G28 | Bare except (Python) | `except\s*:` | `*.py` | high | low | |
| G29 | Silent except Exception | `except\s+Exception` | `*.py` | high | low | Two-pass: check next line is `pass` |
| G30 | Return in finally | `finally` | `*.{ts,js,java,kt}` | high | medium | Two-pass: find finally blocks, check for return inside |

### TypeScript Type System

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G41 | `any` type | `:\s*any\b|<any>|as\s+any` | `*.{ts,tsx}` | high | low |
| G42 | @ts-ignore no reason | `//\s*@ts-ignore\s*$` | `*.{ts,tsx}` | high | low |
| G43 | Non-null assertion chain | `!\.\w+!\.\w+` | `*.{ts,tsx}` | high | low |
| G44 | Index signature backdoor | `\[key:\s*string\]:\s*any` | `*.{ts,tsx}` | high | low |
| G45 | Object type | `:\s*Object\b` | `*.{ts,tsx}` | medium | low |

### Python-Specific

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G49 | Mutable default arg | `def\s+\w+\(.*=\s*\[\]|def\s+\w+\(.*=\s*\{\}` | `*.py` | high | low |
| G50 | HTTP client no timeout | `requests\.(get|post|put|patch|delete)\(` | `*.py` | medium | medium |
| G51 | time.sleep in async | `time\.sleep\(` | `*.py` | high | medium |
| G52 | Django DEBUG=True | `DEBUG\s*=\s*True` | `*/settings*.py` | critical | low |
| G53 | Django ALLOWED_HOSTS * | `ALLOWED_HOSTS\s*=\s*\[\s*['"]\*['"]` | `*/settings*.py` | critical | low |
| G54 | Django SECRET_KEY hardcoded | `SECRET_KEY\s*=\s*['"][^'"]+['"]` | `*/settings*.py` | critical | medium |
| G55 | Flask SECRET_KEY dev | `SECRET_KEY.*=.*['"]dev['"]` | `*.py` | critical | low |
| G56 | fit_transform on test | `fit_transform\(.*[Tt]est` | `*.py` | high | medium |
| G57 | subprocess shell=True | `subprocess\.(run|call|Popen)\(.*shell\s*=\s*True` | `*.py` | high | medium |
| G58 | os.system call | `os\.system\(` | `*.py` | high | low |
| G65 | httpx no timeout | `httpx\.(get|post|put|patch|delete|request)\(` | `*.py` | medium | medium |
| G66 | AES ECB mode | `MODE_ECB|mode.*ECB` | `*.py` | critical | low |
| G67a | Weak hash non-checksum | `hashlib\.(md5|sha1)\(` | `*.py` | high | medium |
| G68a | Random for crypto | `random\.(randint|randbytes|choice)\(.*(?i:key|iv|nonce|token|secret)` | `*.py` | critical | medium |

### React/Next.js

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G76 | Async useEffect | `useEffect\s*\(\s*async` | `*.{jsx,tsx}` | high | low |
| G77 | next/router in app dir | `from\s+['"]next/router['"]` | `app/**/*.{ts,tsx}` | high | low |
| G78 | getServerSideProps in app | `getServerSideProps` | `app/**/*.{ts,tsx}` | high | low |
| G79 | NEXT_PUBLIC_ on secrets | `NEXT_PUBLIC_.*(?i:secret|key|password|token)` | `*.env*` | critical | medium |
| G80 | Server Component with useState | `use(State|Effect|Reducer|Context)\b` | `app/**/page.{ts,tsx}` | high | medium |
| G81 | Async client component | `export\s+default\s+async\s+function` | Files with `"use client"` | high | low |
| G82 | Server Action no validation | `"use server"` | `app/**/*.{ts,tsx}` | high | medium |
| G83 | revalidate without auth | `revalidate(Path|Tag)\(` | `app/**/*.{ts,tsx}` | high | medium |

### Go/Rust/Swift

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G59 | Go error return ignored | `\w+,\s*_\s*:?=\s*\w+\.\w+\(` | `*.go` | high | medium |
| G60 | Go log.Fatal in library | `log\.Fatal` | `*.go` | medium | medium |
| G61 | Rust unwrap chain | `\.unwrap\(\).*\.unwrap\(\)` | `*.rs` | high | low |
| G62 | Rust static mut | `static\s+mut\s+` | `*.rs` | high | low |
| G63 | Swift force try | `try!` | `*.swift` | high | low |
| G64 | Swift force cast | `\bas!\b` | `*.swift` | high | low |

### Swift/iOS — NEW (G101-G108)

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G101 | Swift print in production | `\bprint\(` | `*.swift` | medium | medium |
| G102 | Implicitly unwrapped optional | `:\s*\w+!` | `*.swift` | high | medium |
| G103 | DispatchQueue.main in SwiftUI | `DispatchQueue\.main\.async` | `*.swift` | medium | medium |
| G104 | UserDefaults for secrets | `UserDefaults.*(?i:token|key|secret|password)` | `*.swift` | high | low |
| G105 | Missing weak self | `\{\s*self\.\w+` | `*.swift` | medium | high |
| G106 | NavigationView (deprecated) | `NavigationView\s*\{` | `*.swift` | medium | low |
| G107 | nonisolated(unsafe) | `nonisolated\(unsafe\)` | `*.swift` | high | low |
| G108 | Task without error handling | `Task\s*\{\s*$` | `*.swift` | medium | medium |

### Docker/K8s/IaC

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G67 | FROM :latest | `FROM\s+\w+:latest` | `Dockerfile*` | medium | low |
| G68 | ADD . before install | `ADD\s+\.\s+` | `Dockerfile*` | medium | low |
| G69 | npm as PID 1 | `ENTRYPOINT\s+\["npm"` | `Dockerfile*` | medium | low |
| G70 | K8s privileged | `privileged:\s*true` | `*.yml` | critical | low |
| G71 | K8s hostPath / | `path:\s*["']/["']` | `*.yml` | critical | low |
| G72 | Terraform master ref | `ref=master` | `*.tf` | medium | low |
| G73 | uvicorn --reload prod | `uvicorn.*--reload` | `Dockerfile*` | high | medium |

### AI/LLM

| ID | Pattern | Regex | Glob | Severity | FP Risk |
|----|---------|-------|------|----------|---------|
| G86 | Unpinned model version | `model\s*[:=]\s*["'](gpt-4|gpt-4o|claude-3|claude-4|gemini)["']` | `*.{py,ts,js}` | medium | low |
| G87 | JSON.parse LLM response | `JSON\.parse\(\w*[Rr]espon` | `*.{ts,js}` | high | medium |
| G88 | Credential in prompt | `(?i:api[_-]?key|password|secret).*prompt\s*=` | `*.{py,ts,js}` | critical | medium |

### AI Slop Language (P9)

| ID | Pattern | Regex | Glob | Severity | FP Risk | Notes |
|----|---------|-------|------|----------|---------|-------|
| G110 | LLM vocabulary density | `(?i)(//\|#\|/\*\|"""\|''').*\b(delve|robust|comprehensive|leverage|utilize|seamlessly|paramount|meticulously|bolster|harness|furthermore|moreover|pivotal|tapestry|foster|showcase|endeavor)\b` | `*.{ts,js,py,swift,go,rs,java,kt}` | medium | high | **Co-occurrence model:** grep finds candidates, then count per-file. Flag only when 3+ banned words in same file's comments, or 2+ in a single comment. Individual matches are NOT findings |
| G111 | LLM vocabulary in strings | `(?i)["'](.*\b(delve|robust|comprehensive|leverage|utilize|seamlessly|paramount|meticulously|harness|furthermore|pivotal|tapestry|foster|showcase|endeavor)\b)` | `*.{ts,js,jsx,tsx,py,swift}` | medium | high | Same co-occurrence model as G110. Individual string matches are noise. Skip i18n files |
| G112 | Restatement comment | `(?i)//\s*(set|get|return)\s+(the\s+)?\w+\s*$` | `*.{ts,js,swift,go,rs,java,kt}` | medium | high | **Narrowed:** only short restatements (set/get/return + max 3-4 words). Two-pass MANDATORY: verify next line does exactly what comment says. Do NOT flag intent comments like `// Handle edge case where...` |
| G113 | Markdown in code comments | `(//\|#)\s*(\*\*\w+\*\*\|- \w\|## )` | `*.{ts,js,py,swift,go,rs}` | low | low | Markdown formatting has no business in source code comments |
| G114 | Step-numbered comments | `(//\|#)\s*Step\s+\d+\s*:` | `*.{ts,js,py,swift,go,rs,java,kt}` | medium | low | Strongest uncaught AI signal. LLMs produce `// Step 1: ... Step 2: ...` as implementation plan. Humans almost never do this |

### Pseudocode Detection (P10)

| ID | Pattern | Regex | Glob | Severity | FP Risk | Notes |
|----|---------|-------|------|----------|---------|-------|
| G115 | Pseudocode keywords | `\b(FOREACH\|ENDFOR\|ENDIF\|ELSEIF\|REPEAT\s+UNTIL\|PROCEDURE\|ENDWHILE\|BEGIN\b.*END\b)\b` | `*.{ts,js,py,swift,go,rs,java,kt}` | high | low | These are not valid in any modern language. SQL contexts excluded |
| G116 | Ellipsis as implementation | `^\s*(\.{3}\|//\s*\.{3}\|#\s*\.{3}\|/\*\s*\.{3}\s*\*/)\s*$` | `*.{ts,js,swift,go,rs,java,kt}` | high | low | Bare `...` as function body = LLM gave up. **Exclude Python** — `...` (Ellipsis) is valid Python for abstract methods, type stubs, Protocol definitions. Exception: JS spread operator (requires context) |
| G117 | Natural language function body | `(?i)^\s*(//\|#)\s*(do something\|check if\|loop through\|handle the\|process the\|get the\|send the\|validate the\|parse the\|convert the)` | `*.{ts,js,py,swift,go,rs,java,kt}` | high | low | English instructions where implementation should be |
| G118 | Arrow notation in code | `[→←⟶⟵]` | `*.{ts,js,py,swift,go,rs,java,kt}` | high | low | Unicode arrows as pseudocode operators. Not valid syntax |

### AI Visual Slop (P11)

| ID | Pattern | Regex | Glob | Severity | FP Risk | Notes |
|----|---------|-------|------|----------|---------|-------|
| G120 | AI purple gradient | `(?i)linear-gradient.*#(6366f1\|7c3aed\|8b5cf6\|a855f7\|7e22ce\|6d28d9)` | `*.{css,scss,tsx,jsx}` | medium | medium | The #1 AI color tell. Flag if not in a design system file |
| G121 | AI purple Tailwind | `(?i)(from\|via\|to)-(purple\|violet\|indigo)-(400\|500\|600)` | `*.{tsx,jsx,html,vue,svelte}` | medium | high | Tailwind variant of G120. Purple is standard Tailwind — only flag as P11 co-occurrence (3+ items), NOT standalone. Exclude design token files (`**/tokens.*`, `**/theme.*`, `**/brand.*`) |
| G122 | Centered text density | `text-align:\s*center\|text-center` | `*.{css,scss,tsx,jsx,html,vue,svelte}` | medium | high | Two-pass: count occurrences vs total text containers. Flag if >60% centered |
| G123 | Uniform bubbly radius | `border-radius:\s*(16px\|20px\|24px\|1rem\|1\.5rem)\|rounded-(2xl\|3xl)` | `*.{css,scss,tsx,jsx,html,vue,svelte}` | low | high | Two-pass: aggregate values. Flag if >80% use same large radius |
| G124 | Generic hero copy | `(?i)(unlock the power\|your all-in-one\|revolutionize your\|welcome to .+\|supercharge your\|take .+ to the next level\|streamline your)` | `*.{tsx,jsx,html,vue,svelte,swift}` | medium | low | Marketing slop. If this is in your codebase, someone vibecoded the copy. `.+` catches multi-word names |
| G125 | Emoji as design element | `[🚀✨💡🔥⚡🎯🌟💪🎉🏆]` | `*.{tsx,jsx,html,vue,svelte}` | low | medium | Flag in production UI. Fine in docs/README |
| G126 | Colored left border card | `border-left:\s*[2-4]px\s+solid` | `*.{css,scss}` | low | high | Common AI card pattern. Only flag when co-occurring with 2+ other P11 items |
| G127 | Default AI box-shadow | `box-shadow:\s*0\s+4px\s+6px\s+rgba\(0,\s*0,\s*0,\s*0\.1\)` | `*.{css,scss,tsx,jsx}` | low | medium | The most common AI shadow value. P11 co-occurrence contributor |
| G128 | Glassmorphism blur | `backdrop-filter:\s*blur\(10px\)` | `*.{css,scss,tsx,jsx}` | low | medium | Very 2023-AI aesthetic. P11 co-occurrence contributor |

### AI Documentation Slop (P9 extended)

| ID | Pattern | Regex | Glob | Severity | FP Risk | Notes |
|----|---------|-------|------|----------|---------|-------|
| G130 | "This function/method/class" docstring | `^\s*\*?\s*This\s+(function\|method\|class\|module)\s` | `*.{ts,js,py,swift,rs}` | medium | low | LLMs open every docstring with "This function does X". Humans write the behavior directly |
| G131 | Param doc restates name | `@param\s+(\w+)\s+[-–]\s+[Tt]he\s+\1` | `*.{ts,js}` | medium | low | `@param name - The name` literally restates the parameter. Uses backreference |
| G132 | Section divider comments | `(//\|#)\s*={4,}\s*\w+\s*={4,}` | `*.{ts,js,swift,rs}` | low | low | `// ======= SECTION =======` — LLM organizational tic |
| G133 | Hardcoded mock return | `return\s+\[\s*\{\s*id:\s*[12],\s*name:` | `*.{ts,js,tsx,jsx}` | high | low | Returning `[{id: 1, name: "..."}, {id: 2, name: "..."}]` as "implementation." Classic LLM laziness |

---

## Severity Tiers (Vibecode Context)

| Tier | Definition | Action |
|------|-----------|--------|
| **Critical** | Code cannot run (phantom dep/module), creates exploitable vulnerability, or exposes secrets irrevocably. No mitigating context. | Blocks merge. Short-circuits review if 3+ Critical. |
| **High** | Runtime error on first use (phantom symbol, signature mismatch), silent security bypass, or data loss risk. Exploitable under realistic conditions. | Must fix before deploy. |
| **Medium** | Maintainability degradation, defense-in-depth weakness, or pattern mismatch that increases future bug risk. Not directly exploitable alone. | Fix this sprint. |
| **Low** | Style drift, over-documentation, minor naming issues. Code works but doesn't match project conventions. | Log it. Fix in normal cycle. |

## Context-Dependent Severity

These patterns change severity based on context:

| Pattern | Low-Risk Context | High-Risk Context |
|---------|-----------------|-------------------|
| Missing CSRF | Token-based API auth (Bearer) | Cookie-based auth on state-changing endpoints |
| Disabled TLS | Local dev with self-signed cert | Production code calling external APIs |
| Empty catch | Best-effort cleanup code | Auth/payment/data-integrity paths |
| assert for validation | Test files | Request handler input validation |
| Django DEBUG=True | `local_settings.py` | `settings.py` without env guard |
| SQLite in production | Read-heavy single-process CLI | Multi-worker web server |
| Swift print() | Scripts, playgrounds | Production iOS app code |
| G102 (IUO) | IBOutlets in UIKit code | SwiftUI / non-UI code |

## What This Does NOT Flag

- Code that is ugly but functional and doesn't match P9-P11 (Step 7 catches remaining style issues)
- Code that has bugs but uses real APIs (correctness check, Steps 3-6)
- Code that is insecure but integrated (security mode)
- Code that is over-engineered but real (SOLID check, Step 8)
- Methods called on stdlib/framework instances (P3 limitation — requires LLM knowledge)

---

## Full Pattern Catalog

The complete 442-pattern catalog (post-dedup from 600 raw examples) is stored at:
`/tmp/vibecode-research/raw/` (Codex, Gemini, Claude researcher outputs)

### Taxonomy (16 categories, 442 unique patterns)

| # | Category | Count | Primary Detection |
|---|----------|-------|-------------------|
| 1 | Lifecycle & Resource Management | 28 | AST (cleanup return analysis) |
| 2 | Hallucinated APIs & Phantom References | 78 | Heuristic (manifest + symbol lookup) |
| 3 | Security Vulnerabilities | 24 | Grep (G01-G20) + Review |
| 4 | Secrets & Credential Management | 14 | Grep (G01, G11-G14) |
| 5 | Error Handling Anti-Patterns | 23 | Grep (G21-G30) + AST |
| 6 | Type System Abuse | 18 | Grep (G41-G45) + ESLint |
| 7 | State Management & Reactivity Bugs | 20 | AST (framework-specific) |
| 8 | Architecture & Design Smells | 22 | Heuristic (LLM analysis) |
| 9 | API Design Anti-Patterns | 26 | Review-only |
| 10 | Database & ORM Misuse | 15 | AST + Heuristic |
| 11 | Testing Anti-Patterns | 21 | Heuristic (LLM analysis) |
| 12 | Configuration & Environment | 14 | Grep (G52-G55) |
| 13 | Infrastructure & DevOps | 48 | Grep (G67-G73) |
| 14 | Framework-Specific Misuse | 52 | AST + Grep (G76-G80) |
| 15 | AI/LLM-Specific & Documentation | 26 | Grep (G86-G88) + Review |
| 16 | ML/Data Science Pipeline | 13 | Heuristic |

---

## Changelog

### v4 (AI slop + pseudocode + visual slop, 2026-03-31)
- **P9 added:** AI Slop Language — 30+ banned LLM vocabulary words (co-occurrence model:
  flag 3+ in same file, not individual matches), banned phrases, restatement comments,
  over-documentation, markdown-in-code. Grep rules G110-G114, G130-G132
- **P10 added:** Pseudocode detection — pseudocode keywords, ellipsis bodies (Python excluded —
  `...` is valid syntax), natural language function bodies, arrow notation. Grep rules G115-G118
- **P11 added:** AI Visual Slop — 10-item blacklist adapted from gstack's design-checklist
  (purple gradients, 3-column grids, centered everything, bubbly radius, generic hero copy,
  emoji bullets, decorative blobs). Grep rules G120-G128
- **"multifaceted" removed from banned list** — user preference override
- **Sources:** gstack (AI_SLOP_BLACKLIST, banned vocabulary, design-checklist.md),
  ui-ux-pro-max (ui-reasoning.csv anti-patterns, color validation)
- **Quorum --max --diverse review (Claude + Gemini 2.5 Pro + Codex/GPT-5.2):**
  - G110/G111: FP upgraded medium→high, switched to co-occurrence detection model
  - G112: Narrowed regex to short restatements only (set/get/return), FP upgraded medium→high
  - G116: Python excluded (Ellipsis is valid syntax for abstract methods/type stubs)
  - G121: FP upgraded medium→high, restricted to P11 co-occurrence only
  - G124: Fixed `\w+` → `.+` to catch multi-word names
  - G114 added: Step-numbered comments (`// Step 1:`) — strongest uncaught AI signal
  - G127-G128 added: Default AI box-shadow, glassmorphism blur (P11 co-occurrence)
  - G130-G133 added: "This function" docstrings, param restating, section dividers, mock returns
- **Core patterns updated:** P1-P8 → P1-P11 (11 core detection patterns)
- **Stack coverage:** CSS/Tailwind/SwiftUI now covered for visual slop

### v3 (backlog resolution, 2026-03-31)
- **Python crypto rules added:** G65 (httpx no timeout), G66 (AES ECB mode), G67a (weak hash),
  G68a (random for crypto) — covers Myelin8's encryption.py and index_crypto.py
- **Next.js Server Action rules added:** G82 (Server Action no validation), G83 (revalidate without auth)
- **Stack coverage updated:** Python and Next.js now Full coverage

### v2 (Quorum --max --diverse review, 2026-03-31)
- **Regex syntax fixed:** All `\|` alternation replaced with `|`, removed unsupported lookaheads,
  multiline patterns converted to two-pass single-line checks
- **P1 expanded:** Added go.mod, Podfile.lock, Cartfile.resolved, xcodeproj support, monorepo resolution
- **P3 limitation documented:** Cannot verify methods on stdlib instances
- **P5 enriched:** Added Swift/iOS and Next.js App Router specific indicators
- **P6 exceptions expanded:** Filesystem-routed files, lambda handlers, config files
- **P8 added:** Stub/placeholder detection (LLM laziness markers)
- **Swift rules added:** G101-G108 (print, IUO, DispatchQueue, UserDefaults secrets, weak self,
  NavigationView, nonisolated(unsafe), Task without error handling)
- **Python rules added:** G57 (subprocess shell=True), G58 (os.system)
- **G09 fixed:** Scoped to requests.* call context to reduce FP on cert-pinning code
- **G50 simplified:** Removed broken lookahead, now two-pass (grep finds call, reviewer checks timeout)
- **G59 narrowed:** Now requires function call on RHS to reduce idiomatic Go FPs
- **G71 fixed:** Removed multiline dependency, matches path line directly
- **G80 replaced:** Now detects hooks in server components instead of broken multiline pattern
- **G86 updated:** Added claude-4, gpt-4o model names
- **Step 0 batching guidance added:** Cap at ~40 tool calls, batch manifest reads
- **Path exclusions added:** Test/docs/fixtures excluded from auto-fail scan
- **Short-circuit fix:** Always completes 0f (security scan) even when short-circuiting
- **Stack coverage table added**
- **Rule count corrected** (was claiming 94, now accurately reflects actual rules)
- **Cross-model review:** Codex found regex syntax errors, Gemini found FP gaps, Claude agents
  found Swift coverage gap and Step 0 performance issues
