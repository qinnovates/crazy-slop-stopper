"""Pattern compiler — loads atoms.toml + rules.toml, expands to ripgrep regex.

Like Splunk's props.conf/transforms.conf: named atoms compose into rules.
The atoms are human-readable; the compiled regex is machine-readable.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).parent


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


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _load_atoms(path: Path | None = None) -> dict[str, str]:
    """Load atom definitions from TOML."""
    path = path or _HERE / "atoms.toml"
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("atoms", {})


def _expand_pattern(pattern: str, atoms: dict[str, str], *, depth: int = 0) -> str:
    """Replace {ATOM_NAME} references with their regex values.

    Supports recursive expansion up to 5 levels deep.
    """
    if depth > 5:
        return pattern

    def replacer(match: re.Match) -> str:
        name = match.group(1)
        value = atoms.get(name)
        if value is None:
            return match.group(0)
        return _expand_pattern(value, atoms, depth=depth + 1)

    return re.sub(r'\{([A-Z_][A-Z_0-9]*)\}', replacer, pattern)


def _expand_files(file_patterns: list[str], atoms: dict[str, str]) -> list[str]:
    """Expand atom references in file glob patterns."""
    expanded = []
    for pat in file_patterns:
        result = re.sub(
            r'\{([A-Z_][A-Z_0-9]*)\}',
            lambda m: atoms.get(m.group(1), m.group(0)),
            pat,
        )
        expanded.append(result)
    return expanded


def load_rules(
    rules_path: Path | None = None,
    atoms_path: Path | None = None,
) -> list[GrepRule]:
    """Load and compile rules from TOML files.

    Returns a list of GrepRule with all atom references expanded to regex.
    """
    rules_path = rules_path or _HERE / "rules.toml"
    atoms = _load_atoms(atoms_path)

    with open(rules_path, "rb") as f:
        data = tomllib.load(f)

    rules: list[GrepRule] = []

    for key, stanza in data.get("rule", {}).items():
        raw_pattern = stanza["pattern"]
        compiled_regex = _expand_pattern(raw_pattern, atoms)

        raw_files = stanza.get("files", [])
        compiled_files = _expand_files(raw_files, atoms)

        mode = stanza.get("mode", "")
        is_co_occurrence = mode == "co-occurrence"
        threshold = stanza.get("threshold", 0) if is_co_occurrence else 0

        for glob_pattern in compiled_files:
            rules.append(GrepRule(
                rule_id=key,
                name=stanza["name"],
                regex=compiled_regex,
                glob=glob_pattern,
                severity=stanza["severity"],
                fp_risk=stanza.get("fp_risk", "medium"),
                notes=stanza.get("notes", ""),
                category=stanza["category"],
                two_pass=stanza.get("two_pass", False),
                co_occurrence=is_co_occurrence,
                co_occurrence_threshold=threshold,
            ))

    return rules


# Compile on import — rules are immutable after load
ALL_RULES: list[GrepRule] = load_rules()
