"""Core scanner — runs grep rules against a target directory via ripgrep."""

import json
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from vibecheck.patterns import ALL_RULES, SEVERITY_ORDER, GrepRule


@dataclass(frozen=True, slots=True)
class Finding:
    rule: GrepRule
    file_path: str
    line_number: int
    line_content: str


@dataclass
class ScanResult:
    findings: list[Finding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    files_scanned: int = 0
    rules_run: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.rule.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.rule.severity == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.rule.severity == "medium")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.rule.severity == "low")

    @property
    def passed(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


def _find_ripgrep() -> str | None:
    """Find the ripgrep binary. Checks PATH and common install locations."""
    rg_path = shutil.which("rg")
    if rg_path:
        return rg_path

    for candidate in ["/opt/homebrew/bin/rg", "/usr/local/bin/rg", "/usr/bin/rg"]:
        if Path(candidate).is_file():
            return candidate

    return None


def _run_ripgrep(
    pattern: str,
    target: Path,
    glob: str,
    *,
    rg_bin: str = "rg",
    timeout: int = 30,
) -> list[dict]:
    """Run a single ripgrep pattern, return matches as dicts."""
    cmd = [
        rg_bin,
        "--json",
        "--glob", glob,
        "--no-heading",
        pattern,
        str(target),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return []

    matches = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("type") == "match":
            match_data = data["data"]
            file_path = match_data["path"]["text"]
            line_number = match_data["line_number"]
            line_text = match_data["lines"]["text"].rstrip("\n")
            matches.append({
                "file": file_path,
                "line": line_number,
                "text": line_text,
            })
    return matches


def _apply_co_occurrence_filter(
    matches: list[dict],
    threshold: int,
) -> list[dict]:
    """Filter matches to only include files exceeding the co-occurrence threshold."""
    file_counts: dict[str, int] = defaultdict(int)
    for match in matches:
        file_counts[match["file"]] += 1

    return [m for m in matches if file_counts[m["file"]] >= threshold]


def scan(
    target: Path,
    *,
    categories: list[str] | None = None,
    severity_min: str = "low",
    exclude_two_pass: bool = False,
) -> ScanResult:
    """Scan a directory for vibecode patterns.

    Args:
        target: Directory to scan.
        categories: Filter to specific categories. None = all.
        severity_min: Minimum severity to report (low/medium/high/critical).
        exclude_two_pass: Skip rules that require semantic follow-up.

    Returns:
        ScanResult with all findings.
    """
    rg_bin = _find_ripgrep()
    if rg_bin is None:
        return ScanResult(
            errors=["ripgrep (rg) not found. Install: https://github.com/BurntSushi/ripgrep#installation"],
        )

    if not target.is_dir():
        return ScanResult(errors=[f"Target is not a directory: {target}"])

    min_sev = SEVERITY_ORDER.get(severity_min, 3)
    result = ScanResult()

    rules_to_run = [
        rule for rule in ALL_RULES
        if (categories is None or rule.category in categories)
        and SEVERITY_ORDER.get(rule.severity, 3) <= min_sev
        and not (exclude_two_pass and rule.two_pass)
    ]

    result.rules_run = len(rules_to_run)

    for rule in rules_to_run:
        all_matches: list[dict] = []
        matches = _run_ripgrep(rule.regex, target, rule.glob, rg_bin=rg_bin)
        all_matches.extend(matches)

        if rule.co_occurrence and rule.co_occurrence_threshold > 0:
            all_matches = _apply_co_occurrence_filter(
                all_matches, rule.co_occurrence_threshold
            )

        for match in all_matches:
            result.findings.append(Finding(
                rule=rule,
                file_path=match["file"],
                line_number=match["line"],
                line_content=match["text"],
            ))

    result.findings.sort(
        key=lambda f: (SEVERITY_ORDER.get(f.rule.severity, 3), f.file_path, f.line_number)
    )

    return result
