#!/usr/bin/env python3
"""skill-audit: read a SKILL.md, apply a 4-point rubric, print a report.

Deterministic — no LLM calls. Every finding is a rule applied to the
file's text or structure.

Usage:
    python audit.py path/to/SKILL.md

Exit codes:
    0 = all PASS
    1 = at least one WARN
    2 = at least one FAIL
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

GENERIC_TRIGGERS = {
    "help", "help me", "fix this", "do it", "yes", "no", "ok",
    "what should I do", "any ideas",
}

REQUIRED_FRONTMATTER_KEYS = ["name", "description", "triggers"]

SAFETY_CUE_WORDS = [
    "never auto-merge", "no auto-merge", "do not auto-merge",
    "never push directly", "do not push to main",
    "never force-push", "no force-push", "no rebase",
    "stop. ", "stop and", "do not merge", "smallest possible patch",
    "out of scope", "## out of scope", "## safety", "## rules",
    "human reviews", "review carefully", "review before merging",
]

CREDENTIAL_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9_]{20,}",
    r"gho_[a-zA-Z0-9_]{20,}",
    r"github_pat_[a-zA-Z0-9_]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY",
    r"password\s*[:=]\s*[\"\']?\w{4,}",
]


@dataclass
class Finding:
    label: str
    text: str


@dataclass
class Dimension:
    name: str
    findings: list[Finding] = field(default_factory=list)

    def status(self) -> tuple[str, int]:
        has_fail = any(f.label == "FAIL" for f in self.findings)
        has_warn = any(f.label == "WARN" for f in self.findings)
        if has_fail:
            return "FAIL", 0
        if has_warn:
            return "WARN", 4
        return "PASS", 7


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return {}, text
    end = None
    for i, ln in enumerate(lines[1:], start=1):
        if ln.strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm: dict = {}
    cur_list_key = None
    for ln in lines[1:end]:
        if not ln.strip():
            continue
        m = re.match(r"^([a-zA-Z_-]+)\s*:\s*(.*)$", ln)
        if m and not ln.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            if val:
                fm[key] = val
                cur_list_key = None
            else:
                fm[key] = []
                cur_list_key = key
        elif ln.lstrip().startswith("-") and cur_list_key:
            item = ln.lstrip()[1:].strip().strip("\"").strip("\'")
            fm[cur_list_key].append(item)
    body = "\n".join(lines[end + 1:])
    return fm, body


def check_triggers(fm: dict, body: str) -> Dimension:
    d = Dimension(name="TRIGGER QUALITY")
    triggers = fm.get("triggers", [])
    n = len(triggers) if isinstance(triggers, list) else 0
    if n == 0:
        d.findings.append(Finding("FAIL", "no triggers declared"))
        return d
    if n < 3:
        d.findings.append(Finding("WARN", f"{n} trigger(s) is too narrow (3-7 ideal)"))
    elif n > 10:
        d.findings.append(Finding("WARN", f"{n} triggers is spammy (3-7 ideal)"))
    else:
        d.findings.append(Finding("OK", f"{n} trigger phrases (good count)"))

    generic_hits = [t for t in triggers if t.lower().strip() in GENERIC_TRIGGERS]
    if generic_hits:
        d.findings.append(Finding(
            "WARN",
            f"trigger {generic_hits[0]!r} is too generic — likely to misfire",
        ))

    avg_len = sum(len(t.split()) for t in triggers) / max(1, len(triggers))
    if avg_len < 1.8:
        d.findings.append(Finding("WARN", f"avg trigger length {avg_len:.1f} words is short"))

    one_word_common = [t for t in triggers if len(t.split()) == 1 and len(t) < 6]
    if one_word_common:
        d.findings.append(Finding(
            "WARN",
            f"trigger {one_word_common[0]!r} is a single short word "
            "— may collide with everyday queries",
        ))
    else:
        d.findings.append(Finding("OK", "no overly generic single-word triggers"))

    return d


def count_distinct_action_verbs(body: str) -> int:
    verbs = set()
    for ln in body.splitlines():
        m = re.match(r"^\s*(?:[-*]|\d+\.)\s+([a-zA-Z]+)", ln)
        if m:
            verbs.add(m.group(1).lower())
    return len(verbs)


def check_scope(fm: dict, body: str) -> Dimension:
    d = Dimension(name="SCOPE DRIFT")
    name = fm.get("name", "")
    desc = fm.get("description", "")
    if name and name.lower() in desc.lower():
        d.findings.append(Finding("OK", f"name {name!r} appears in description"))
    else:
        d.findings.append(Finding("WARN", f"skill name {name!r} missing from description"))

    if name and name.lower() not in body.lower():
        d.findings.append(Finding("WARN", f"skill name {name!r} not mentioned in body"))
    else:
        d.findings.append(Finding("OK", "name reinforced in body"))

    _DRIFT_RE = (
        r"(?i)\b(and also|in addition|on top of that|plus,? also|"
        r"while you'?re at it)\b"
    )
    drift_markers = re.findall(_DRIFT_RE, body)
    if drift_markers:
        d.findings.append(Finding(
            "WARN",
            f"found scope-drift markers: {drift_markers[:2]}",
        ))
    else:
        d.findings.append(Finding("OK", "no scope-drift markers"))

    verbs = count_distinct_action_verbs(body)
    if verbs > 12:
        d.findings.append(Finding("WARN", f"{verbs} distinct action verbs — possible bolt-ons"))
    else:
        d.findings.append(Finding("OK", f"{verbs} distinct action verbs (concise)"))

    return d


def check_safety(fm: dict, body: str) -> Dimension:
    d = Dimension(name="SAFETY")
    body_lower = body.lower()

    cue_hits = [c for c in SAFETY_CUE_WORDS if c in body_lower]
    if cue_hits:
        d.findings.append(Finding("OK", f"safety clauses present (e.g. {cue_hits[0]!r})"))
    else:
        d.findings.append(Finding("WARN", "no explicit safety clauses found"))

    _OOS_RE = r"^#+\s*(out of scope|rules|safety|guardrails)\b"
    if re.search(_OOS_RE, body, re.MULTILINE | re.IGNORECASE):
        d.findings.append(Finding("OK", "structured out-of-scope/safety section present"))
    else:
        d.findings.append(Finding("WARN", "no explicit out-of-scope section"))

    for pat in CREDENTIAL_PATTERNS:
        if re.search(pat, body, re.IGNORECASE):
            d.findings.append(Finding("FAIL", f"plaintext credential pattern detected: /{pat}/"))
            break
    else:
        d.findings.append(Finding("OK", "no plaintext credentials"))

    automerge_mentioned = re.search(r"auto[-\s]?merge", body_lower) is not None
    automerge_forbidden = any(s in body_lower for s in (
        "never auto-merge", "no auto-merge", "do not auto-merge",
    ))
    if automerge_mentioned and not automerge_forbidden:
        d.findings.append(Finding("WARN", "skill mentions auto-merge — verify it is gated"))
    else:
        d.findings.append(Finding("OK", "auto-merge is either absent or explicitly forbidden"))

    return d


def check_clarity(fm: dict, body: str) -> Dimension:
    d = Dimension(name="CLARITY")

    missing = [k for k in REQUIRED_FRONTMATTER_KEYS if k not in fm]
    if missing:
        d.findings.append(Finding("WARN", f"missing frontmatter keys: {missing}"))
    else:
        d.findings.append(Finding("OK", "frontmatter has name/description/triggers"))

    nlines = len(body.splitlines())
    if nlines > 200:
        d.findings.append(Finding("WARN", f"body is {nlines} lines — consider splitting"))
    elif nlines > 120:
        d.findings.append(Finding("WARN", f"body is {nlines} lines — on the long side"))
    else:
        d.findings.append(Finding("OK", f"body is {nlines} lines (tight)"))

    headers = re.findall(r"^#+\s+(.+)$", body, re.MULTILINE)
    if len(headers) < 2:
        d.findings.append(Finding("WARN", "fewer than 2 section headers — structure is thin"))
    else:
        d.findings.append(Finding("OK", f"{len(headers)} section headers"))

    fenced = re.findall(r"^```(\S*)$", body, re.MULTILINE)
    untagged = [f for f in fenced if f == ""]
    if fenced and len(untagged) > len(fenced) // 2:
        d.findings.append(Finding("WARN", f"{len(untagged)} code blocks lack a language tag"))
    else:
        d.findings.append(Finding("OK", "code blocks tagged appropriately"))

    return d


def label_glyph(label: str) -> str:
    return {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "OK": "✓"}.get(label, " ")


def render(path: Path, dims: list[Dimension]) -> str:
    out = []
    out.append(f"SKILL AUDIT: {path}")
    out.append("=" * 58)
    for i, dim in enumerate(dims, start=1):
        status, score = dim.status()
        out.append(f"[{i}] {dim.name:<20} {status:<6} ({score}/7)")
        for f in dim.findings:
            out.append(f"    {label_glyph(f.label)} {f.text}")
        out.append("")
    n_pass = sum(1 for d in dims if d.status()[0] == "PASS")
    n_warn = sum(1 for d in dims if d.status()[0] == "WARN")
    n_fail = sum(1 for d in dims if d.status()[0] == "FAIL")
    total = sum(d.status()[1] for d in dims)
    max_total = 7 * len(dims)
    pct = round(100 * total / max_total)
    out.append("=" * 58)
    out.append(f"OVERALL: {n_pass} PASS  ·  {n_warn} WARN  ·  {n_fail} FAIL")
    out.append(f"SCORE:   {total}/{max_total}  ({pct}%)")
    out.append("=" * 58)
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} path/to/SKILL.md", file=sys.stderr)
        return 64
    path = Path(argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 66
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    dims = [
        check_triggers(fm, body),
        check_scope(fm, body),
        check_safety(fm, body),
        check_clarity(fm, body),
    ]
    print(render(path, dims))
    statuses = [d.status()[0] for d in dims]
    if "FAIL" in statuses:
        return 2
    if "WARN" in statuses:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
