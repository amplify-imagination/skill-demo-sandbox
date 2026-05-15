---
name: skill-audit
description: Audit any SKILL.md file against a four-point quality rubric — trigger quality, scope drift, safety, and clarity. Returns a structured report with PASS / WARN / FAIL per dimension and a combined score. Use whenever the user wants to review, audit, grade, or sanity-check a skill they have written. Trigger phrases include "audit my skills", "grade my skill", "review skill quality", "check this SKILL.md", or any request asking for a quality review of a skill file.
triggers:
  - "audit my skills"
  - "audit my skill"
  - "grade my skill"
  - "review my skill"
  - "check my SKILL.md"
  - "is this skill any good"
  - "skill audit"
tools:
  - read_file
  - bash (for running scripts/audit.py)
---

# skill-audit

A meta-skill: read any SKILL.md file, apply a four-point quality rubric, and
return a structured report.

This skill is the partner to `/skill-creator`. Where `/skill-creator` measures
*runtime performance* (does the skill work? how fast? how consistent?),
`/skill-audit` measures *static quality* (is the skill well-written? does it
have a clear scope? are the write paths bounded? could a new reader follow
it in under a minute?).

## When to use

- The user asks you to "audit", "grade", or "review" a SKILL.md
- The user wants a sanity check before publishing a skill
- A weekly maintenance pass on all the skills in a project: `/loop weekly /skill-audit`

## How it works

`scripts/audit.py` performs deterministic checks on the SKILL.md text. The
script does NOT call an LLM — every finding is a rule applied to the file
structure or wording, so the output is fully reproducible.

```bash
python skills/skill-audit/scripts/audit.py path/to/some/SKILL.md
```

You will get a text report on stdout and an exit code:
- `0` — all PASS
- `1` — at least one WARN
- `2` — at least one FAIL

## The four dimensions

### 1. Trigger quality
Are the trigger phrases specific enough that the skill fires only when you
mean it? Checks:
- Trigger count (3–7 ideal, < 2 too narrow, > 10 spammy)
- Generic-word-only triggers (e.g. "help") that collide with everyday speech
- Average trigger phrase length (very short triggers are risky)
- Triggers that may overlap with common queries on the same domain

### 2. Scope drift
Does the skill stay within its named scope, or has it quietly grown to do
several jobs? Checks:
- The skill name appears in the description and the body
- No "and also …" or "in addition …" patterns suggesting bolt-ons
- Instruction verbs cluster around the named domain
- Reasonable count of distinct sub-tasks (> 8 → WARN)

### 3. Safety
Are the write paths bounded, or is there an unaudited route to production?
Checks:
- Presence of explicit "do not" clauses (no auto-merge / no push to main /
  no force-push, etc.)
- An "Out of scope" / "Rules" / "Safety" section exists
- No plaintext credentials or tokens in the file
- Shell commands restricted to expected tools

### 4. Clarity
Could a new reader follow this skill in under one minute? Checks:
- Frontmatter has the required keys (name, description, triggers, tools)
- Line count (≤ 120 ideal; > 200 suggests splitting)
- Structural headers present (Steps, Out of scope, Safety)
- Code blocks are tagged with a language

## Output format

```
SKILL AUDIT: <path>
==========================================
[1] TRIGGER QUALITY     <PASS|WARN|FAIL>   (n/m)
    bulleted findings
[2] SCOPE DRIFT         <PASS|WARN|FAIL>   (n/m)
    bulleted findings
[3] SAFETY              <PASS|WARN|FAIL>   (n/m)
    bulleted findings
[4] CLARITY             <PASS|WARN|FAIL>   (n/m)
    bulleted findings
==========================================
OVERALL: <p> PASS · <w> WARN · <f> FAIL
SCORE: <total>/<max> (<pct>%)
==========================================
```

Each dimension is worth 7 points: PASS = 7, WARN = 4, FAIL = 0.

## Out of scope

- Never modifies the target SKILL.md.
- Never calls an LLM; output is deterministic for a given input.
- Does not replace `/skill-creator` — it complements it. If you also want
  *runtime* validation, run `/skill-creator` separately and read both
  reports together.

## Wrapping `/skill-creator`

If the caller wants both static audit AND runtime performance in one go,
they can call `/skill-audit` first (fast, deterministic) and `/skill-creator`
second (slow, evaluates real prompts). The two outputs answer different
questions and should be read together.
