"""Detection patterns extracted from vibecode-detection.md.

Each pattern is a dict with: id, name, regex, glob, severity, fp_risk, notes, category.
Regexes are valid ripgrep Rust regex syntax.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GrepRule:
    rule_id: str
    name: str
    regex: str
    glob: str
    severity: str
    fp_risk: str
    notes: str
    category: str
    two_pass: bool = False
    co_occurrence: bool = False
    co_occurrence_threshold: int = 0


SECURITY_CRITICAL: list[GrepRule] = [
    GrepRule("G01", "Hardcoded API key",
             r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*["\'][a-zA-Z0-9_/+\-]{20,}["\']',
             "*.{ts,js,py,swift,kt,go,rs,java}", "critical", "medium",
             "Secrets in source code", "security"),
    GrepRule("G02", "SQL f-string (Python)",
             r'f["\'](?:SELECT|INSERT|UPDATE|DELETE)',
             "*.py", "critical", "low", "SQL injection via f-string", "security"),
    GrepRule("G03", "SQL template literal (JS)",
             r'`(?:SELECT|INSERT|UPDATE|DELETE).*\$\{',
             "*.{ts,js}", "critical", "low", "SQL injection via template literal", "security"),
    GrepRule("G04", "eval() with variable",
             r'eval\s*\([^"\')]+\)',
             "*.{ts,js,py}", "critical", "low", "Remote code execution", "security"),
    GrepRule("G05", "new Function() with variable",
             r'new\s+Function\s*\([^"\')]+\)',
             "*.{ts,js}", "critical", "low", "Remote code execution", "security"),
    GrepRule("G06", "innerHTML with variable",
             r'\.innerHTML\s*=\s*[^"\'<\s]',
             "*.{ts,js,jsx,tsx}", "high", "medium", "XSS via innerHTML", "security"),
    GrepRule("G07", "dangerouslySetInnerHTML",
             r'dangerouslySetInnerHTML',
             "*.{jsx,tsx}", "high", "medium", "XSS via React escape hatch", "security"),
    GrepRule("G08", "Disabled TLS (Node)",
             r'NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\'"]0[\'"]',
             "*.{ts,js}", "critical", "low", "MITM via disabled TLS", "security"),
    GrepRule("G09", "Disabled TLS (Python)",
             r'requests\.\w+\(.*verify\s*=\s*False',
             "*.py", "high", "medium", "MITM via disabled cert verify", "security"),
    GrepRule("G10", "pickle.loads",
             r'pickle\.loads?\(',
             "*.py", "high", "medium", "Arbitrary code execution via deserialization", "security"),
    GrepRule("G11", "Hardcoded encryption key",
             r'(?i)(?:encrypt|cipher|aes)\s*[:=]\s*["\'][^"\']{8,}["\']',
             "*.{ts,js,py,go,rs,java,swift,kt}", "critical", "medium",
             "Encryption key in source", "security"),
    GrepRule("G17", "CORS wildcard",
             r'allow_origin.*["\']\*["\']|Access-Control-Allow-Origin.*\*',
             "*.{ts,js,py,go,java}", "high", "medium", "Permissive CORS", "security"),
    GrepRule("G19", "rm -rf with variable",
             r'rm\s+-rf\s+\$',
             "*.{sh,bash,zsh}", "critical", "low", "Catastrophic data loss", "security"),
    GrepRule("G20", "Raw user input in prompt",
             r'f["\'].*\{user_input\}|f["\'].*\{request\.',
             "*.py", "high", "medium", "Prompt injection", "security"),
]

ERROR_HANDLING: list[GrepRule] = [
    GrepRule("G21", "Empty catch (JS)",
             r'catch\s*\([^)]*\)\s*\{\s*\}',
             "*.{ts,js,jsx,tsx}", "high", "low", "Silent error swallowing", "error-handling"),
    GrepRule("G22", "Empty except (Python)",
             r'except.*:\s*$',
             "*.py", "high", "low", "Two-pass: check next line is pass or ...",
             "error-handling", two_pass=True),
    GrepRule("G25", "Catch-swallow promise",
             r'\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)',
             "*.{ts,js}", "high", "low", "Silent promise rejection", "error-handling"),
    GrepRule("G26", "String throw",
             r'throw\s+[\'"]',
             "*.{ts,js}", "high", "low", "Untyped error", "error-handling"),
    GrepRule("G28", "Bare except (Python)",
             r'except\s*:',
             "*.py", "high", "low", "Catches everything including SystemExit", "error-handling"),
]

TYPESCRIPT_TYPE_SYSTEM: list[GrepRule] = [
    GrepRule("G41", "any type",
             r':\s*any\b|<any>|as\s+any',
             "*.{ts,tsx}", "high", "low", "Defeats the type system", "typescript"),
    GrepRule("G42", "@ts-ignore no reason",
             r'//\s*@ts-ignore\s*$',
             "*.{ts,tsx}", "high", "low", "Suppression without justification", "typescript"),
    GrepRule("G43", "Non-null assertion chain",
             r'!\.\w+!\.\w+',
             "*.{ts,tsx}", "high", "low", "Cascading unsafe access", "typescript"),
    GrepRule("G44", "Index signature backdoor",
             r'\[key:\s*string\]:\s*any',
             "*.{ts,tsx}", "high", "low", "Type system escape hatch", "typescript"),
]

PYTHON_SPECIFIC: list[GrepRule] = [
    GrepRule("G49", "Mutable default arg",
             r'def\s+\w+\(.*=\s*\[\]|def\s+\w+\(.*=\s*\{\}',
             "*.py", "high", "low", "Shared mutable default", "python"),
    GrepRule("G52", "Django DEBUG=True",
             r'DEBUG\s*=\s*True',
             "*/settings*.py", "critical", "low", "Debug mode in settings", "python"),
    GrepRule("G57", "subprocess shell=True",
             r'subprocess\.(?:run|call|Popen)\(.*shell\s*=\s*True',
             "*.py", "high", "medium", "Shell injection risk", "python"),
    GrepRule("G58", "os.system call",
             r'os\.system\(',
             "*.py", "high", "low", "Shell injection risk", "python"),
    GrepRule("G66", "AES ECB mode",
             r'MODE_ECB|mode.*ECB',
             "*.py", "critical", "low", "Insecure block cipher mode", "python"),
]

REACT_NEXTJS: list[GrepRule] = [
    GrepRule("G76", "Async useEffect",
             r'useEffect\s*\(\s*async',
             "*.{jsx,tsx}", "high", "low", "Memory leak from async effect", "react"),
    GrepRule("G77", "next/router in app dir",
             r'from\s+[\'"]next/router[\'"]',
             "app/**/*.{ts,tsx}", "high", "low", "Pages Router in App Router", "react"),
    GrepRule("G79", "NEXT_PUBLIC_ on secrets",
             r'NEXT_PUBLIC_.*(?i:secret|key|password|token)',
             "*.env*", "critical", "medium", "Secret exposed to client", "react"),
]

SWIFT_IOS: list[GrepRule] = [
    GrepRule("G63", "Swift force try",
             r'try!',
             "*.swift", "high", "low", "Runtime crash on error", "swift"),
    GrepRule("G64", "Swift force cast",
             r'\bas!\b',
             "*.swift", "high", "low", "Runtime crash on type mismatch", "swift"),
    GrepRule("G101", "Swift print in production",
             r'\bprint\(',
             "*.swift", "medium", "medium", "Use structured logger", "swift"),
    GrepRule("G104", "UserDefaults for secrets",
             r'UserDefaults.*(?i:token|key|secret|password)',
             "*.swift", "high", "low", "Secrets in unencrypted storage", "swift"),
    GrepRule("G106", "NavigationView (deprecated)",
             r'NavigationView\s*\{',
             "*.swift", "medium", "low", "Use NavigationStack", "swift"),
    GrepRule("G107", "nonisolated(unsafe)",
             r'nonisolated\(unsafe\)',
             "*.swift", "high", "low", "Concurrency safety bypass", "swift"),
]

DOCKER_K8S: list[GrepRule] = [
    GrepRule("G67", "FROM :latest",
             r'FROM\s+\w+:latest',
             "Dockerfile*", "medium", "low", "Unpinned base image", "docker"),
    GrepRule("G70", "K8s privileged",
             r'privileged:\s*true',
             "*.yml", "critical", "low", "Full container escape", "docker"),
    GrepRule("G71", "K8s hostPath /",
             r'path:\s*["\'/]["\']',
             "*.yml", "critical", "low", "Host filesystem access", "docker"),
    GrepRule("G73", "uvicorn --reload prod",
             r'uvicorn.*--reload',
             "Dockerfile*", "high", "medium", "Hot reload in production", "docker"),
]

AI_LLM: list[GrepRule] = [
    GrepRule("G86", "Unpinned model version",
             r'model\s*[:=]\s*["\'](gpt-4|gpt-4o|claude-3|claude-4|gemini)["\']',
             "*.{py,ts,js}", "medium", "low", "Model version will drift", "ai-llm"),
    GrepRule("G87", "JSON.parse LLM response",
             r'JSON\.parse\(\w*[Rr]espon',
             "*.{ts,js}", "high", "medium", "LLM output is not guaranteed JSON", "ai-llm"),
    GrepRule("G88", "Credential in prompt",
             r'(?i:api[_-]?key|password|secret).*prompt\s*=',
             "*.{py,ts,js}", "critical", "medium", "Secret sent to LLM provider", "ai-llm"),
]

AI_SLOP_LANGUAGE: list[GrepRule] = [
    GrepRule("G110", "LLM vocabulary density",
             r'(?i)(?://|#|/\*|"""|\'\'\')\s*.*\b(?:delve|robust|comprehensive|leverage|utilize|seamlessly|paramount|meticulously|bolster|harness|furthermore|moreover|pivotal|tapestry|foster|showcase|endeavor)\b',
             "*.{ts,js,py,swift,go,rs,java,kt}", "medium", "high",
             "Co-occurrence: flag 3+ banned words in same file, not individual matches",
             "ai-slop", co_occurrence=True, co_occurrence_threshold=3),
    GrepRule("G111", "LLM vocabulary in strings",
             r'(?i)["\'].*\b(?:delve|robust|comprehensive|leverage|utilize|seamlessly|paramount|meticulously|harness|furthermore|pivotal|tapestry|foster|showcase|endeavor)\b',
             "*.{ts,js,jsx,tsx,py,swift}", "medium", "high",
             "Co-occurrence model. Skip i18n files",
             "ai-slop", co_occurrence=True, co_occurrence_threshold=3),
    GrepRule("G112", "Restatement comment",
             r'(?i)//\s*(?:set|get|return)\s+(?:the\s+)?\w+\s*$',
             "*.{ts,js,swift,go,rs,java,kt}", "medium", "high",
             "Two-pass: verify next line does what comment says",
             "ai-slop", two_pass=True),
    GrepRule("G113", "Markdown in code comments",
             r'(?://|#)\s*(?:\*\*\w+\*\*|- \w|## )',
             "*.{ts,js,py,swift,go,rs}", "low", "low",
             "Markdown formatting in source code comments", "ai-slop"),
    GrepRule("G114", "Step-numbered comments",
             r'(?://|#)\s*Step\s+\d+\s*:',
             "*.{ts,js,py,swift,go,rs,java,kt}", "medium", "low",
             "LLMs produce Step 1/2/3 as implementation plan. Humans almost never do this",
             "ai-slop"),
]

PSEUDOCODE: list[GrepRule] = [
    GrepRule("G115", "Pseudocode keywords",
             r'\b(?:FOREACH|ENDFOR|ENDIF|ELSEIF|REPEAT\s+UNTIL|PROCEDURE|ENDWHILE)\b',
             "*.{ts,js,py,swift,go,rs,java,kt}", "high", "low",
             "Not valid in any modern language", "pseudocode"),
    GrepRule("G116", "Ellipsis as implementation",
             r'^\s*(?:\.{3}|//\s*\.{3}|#\s*\.{3}|/\*\s*\.{3}\s*\*/)\s*$',
             "*.{ts,js,swift,go,rs,java,kt}", "high", "low",
             "LLM gave up. Exclude Python (Ellipsis is valid syntax)", "pseudocode"),
    GrepRule("G117", "Natural language function body",
             r'(?i)^\s*(?://|#)\s*(?:do something|check if|loop through|handle the|process the|get the|send the|validate the|parse the|convert the)',
             "*.{ts,js,py,swift,go,rs,java,kt}", "high", "low",
             "English instructions where implementation should be", "pseudocode"),
    GrepRule("G118", "Arrow notation in code",
             r'[→←⟶⟵]',
             "*.{ts,js,py,swift,go,rs,java,kt}", "high", "low",
             "Unicode arrows as pseudocode operators", "pseudocode"),
]

AI_VISUAL_SLOP: list[GrepRule] = [
    GrepRule("G120", "AI purple gradient",
             r'(?i)linear-gradient.*#(?:6366f1|7c3aed|8b5cf6|a855f7|7e22ce|6d28d9)',
             "*.{css,scss,tsx,jsx}", "medium", "medium",
             "The #1 AI color tell", "visual-slop"),
    GrepRule("G121", "AI purple Tailwind",
             r'(?i)(?:from|via|to)-(?:purple|violet|indigo)-(?:400|500|600)',
             "*.{tsx,jsx,html,vue,svelte}", "medium", "high",
             "Only flag as P11 co-occurrence (3+ items), NOT standalone",
             "visual-slop", co_occurrence=True, co_occurrence_threshold=3),
    GrepRule("G122", "Centered text density",
             r'text-align:\s*center|text-center',
             "*.{css,scss,tsx,jsx,html,vue,svelte}", "medium", "high",
             "Two-pass: flag if >60% of text containers are centered",
             "visual-slop", two_pass=True),
    GrepRule("G123", "Uniform bubbly radius",
             r'border-radius:\s*(?:16px|20px|24px|1rem|1\.5rem)|rounded-(?:2xl|3xl)',
             "*.{css,scss,tsx,jsx,html,vue,svelte}", "low", "high",
             "Two-pass: flag if >80% use same large radius",
             "visual-slop", two_pass=True),
    GrepRule("G124", "Generic hero copy",
             r'(?i)(?:unlock the power|your all-in-one|revolutionize your|welcome to .+|supercharge your|take .+ to the next level|streamline your)',
             "*.{tsx,jsx,html,vue,svelte,swift}", "medium", "low",
             "Marketing slop", "visual-slop"),
    GrepRule("G125", "Emoji as design element",
             '[\U0001F680\u2728\U0001F4A1\U0001F525\u26A1\U0001F3AF\U0001F31F\U0001F4AA\U0001F389\U0001F3C6]',
             "*.{tsx,jsx,html,vue,svelte}", "low", "medium",
             "Flag in production UI. Fine in docs/README", "visual-slop"),
    GrepRule("G126", "Colored left border card",
             r'border-left:\s*[2-4]px\s+solid',
             "*.{css,scss}", "low", "high",
             "Only flag with 2+ other P11 items",
             "visual-slop", co_occurrence=True, co_occurrence_threshold=3),
    GrepRule("G127", "Default AI box-shadow",
             r'box-shadow:\s*0\s+4px\s+6px\s+rgba\(0,\s*0,\s*0,\s*0\.1\)',
             "*.{css,scss,tsx,jsx}", "low", "medium",
             "The most common AI shadow value", "visual-slop"),
    GrepRule("G128", "Glassmorphism blur",
             r'backdrop-filter:\s*blur\(10px\)',
             "*.{css,scss,tsx,jsx}", "low", "medium",
             "Very 2023-AI aesthetic", "visual-slop"),
]

AI_DOC_SLOP: list[GrepRule] = [
    GrepRule("G130", '"This function/method/class" docstring',
             r'^\s*\*?\s*This\s+(?:function|method|class|module)\s',
             "*.{ts,js,py,swift,rs}", "medium", "low",
             "LLMs open every docstring with This function does X", "ai-slop"),
    GrepRule("G131", "Param doc restates name",
             r'@param\s+(\w+)\s+[-\u2013]\s+[Tt]he\s+\1',
             "*.{ts,js}", "medium", "low",
             "@param name - The name", "ai-slop"),
    GrepRule("G132", "Section divider comments",
             r'(?://|#)\s*={4,}\s*\w+\s*={4,}',
             "*.{ts,js,swift,rs}", "low", "low",
             "LLM organizational tic", "ai-slop"),
    GrepRule("G133", "Hardcoded mock return",
             r'return\s+\[\s*\{\s*id:\s*[12],\s*name:',
             "*.{ts,js,tsx,jsx}", "high", "low",
             "Returning [{id: 1, name: ...}] as implementation", "pseudocode"),
]

ALL_RULES: list[GrepRule] = (
    SECURITY_CRITICAL
    + ERROR_HANDLING
    + TYPESCRIPT_TYPE_SYSTEM
    + PYTHON_SPECIFIC
    + REACT_NEXTJS
    + SWIFT_IOS
    + DOCKER_K8S
    + AI_LLM
    + AI_SLOP_LANGUAGE
    + PSEUDOCODE
    + AI_VISUAL_SLOP
    + AI_DOC_SLOP
)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
