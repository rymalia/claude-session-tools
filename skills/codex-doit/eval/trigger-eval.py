#!/usr/bin/env python3
"""Track A — trigger eval for the codex-doit skill.

Measures whether the skill's *live description* (read from SKILL.md) causes it to
activate on should-trigger queries and stay quiet on should-not near-misses.

Blind: each query is classified in isolation, seeing only the description + that one
query — never the expected label, never the other queries. 3 samples/query to expose
nondeterminism. No optimizer; this is measurement only (any description rewrite is
proposed to the human, never auto-applied).

Run:  ANTHROPIC_API_KEY=$(cat .akey) .venv/bin/python codex-doit-trigger-eval.py
Env:  CDOIT_MODEL (default claude-sonnet-5), CDOIT_SAMPLES (default 3)
"""
import os, re, sys, collections
from anthropic import Anthropic

SKILL = os.path.expanduser("~/.claude/skills/codex-doit/SKILL.md")
MODEL = os.environ.get("CDOIT_MODEL", "claude-sonnet-5")
SAMPLES = int(os.environ.get("CDOIT_SAMPLES", "3"))

# (query, expected)  expected True = should TRIGGER
CASES = [
    ("before I start building the export retry logic, get codex to sanity-check my plan", True),
    ("about to rename a symbol across ~40 files — have codex review the plan first", True),
    ("just finished the auth middleware refactor on this branch — have codex give it a skeptical review before I open the PR", True),
    ("codex doit on the diff", True),
    ("I refactored the caching layer but haven't committed — run it past codex", True),
    (r"ask codex whether this regex is correct: ^(?=.*\d).{8,}$", True),
    ("get codex to look at this SQL query and tell me if the join is right", True),
    ("have codex implement the parseDuration helper in src/time.js — just that function", True),
    ("let codex write the retry wrapper, you don't need to do it yourself", True),
    ("route this migration plan to codex for a second set of eyes before I code it", True),
    ("give me a second opinion on Postgres vs SQLite for this", False),
    ("review PR #482 on github and leave comments", False),
    ("run the test suite and tell me what fails", False),
    ("fix this typo in the readme: recieve should be receive", False),
    ("codex keeps crashing on launch, help me debug the install", False),
    ("what does codex think about tabs vs spaces, out of curiosity?", False),
    ("explain how JWT refresh tokens work", False),
    ("should I use codex or claude for this project?", False),
    ("write a plan to migrate auth to JWT", False),
    ("commit my changes with a good message", False),
]

def load_description(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"^---\s*\n(.*?)\n---", txt, re.S)
    fm = m.group(1) if m else txt
    # folded/literal block scalar: `description: >-` then indented lines
    dm = re.search(r"(?m)^description:\s*[>|]-?\s*\n((?:[ \t]+.*\n?)+)", fm)
    if dm:
        return " ".join(l.strip() for l in dm.group(1).splitlines() if l.strip())
    dm = re.search(r"(?m)^description:[ \t]*(\S.*)$", fm)  # single-line form
    return dm.group(1).strip() if dm else ""

SYSTEM = (
    "You route user requests to skills in a coding assistant. Given ONE skill's "
    "description and a user request, decide whether that skill should activate for "
    "the request, based ONLY on what the description says the skill is for and its "
    "stated exclusions. First line: exactly TRIGGER or NO. Then one short reason."
)

def classify(client, desc, query):
    r = client.messages.create(
        model=MODEL, max_tokens=1024, system=SYSTEM,
        messages=[{"role": "user",
                   "content": f"SKILL DESCRIPTION:\n{desc}\n\nUSER REQUEST:\n{query}"}],
    )
    text = next((b.text for b in r.content if getattr(b, "type", None) == "text"), "")
    line = (text.strip().splitlines() or [""])[0].upper()
    return line.startswith("TRIGGER")

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set. Run: ANTHROPIC_API_KEY=$(cat .akey) .venv/bin/python codex-doit-trigger-eval.py")
    desc = load_description(SKILL)
    if not desc:
        sys.exit(f"could not parse description from {SKILL}")
    client = Anthropic()
    print(f"model={MODEL} samples={SAMPLES} desc_chars={len(desc)}\n")
    tp = fp = fn = tn = 0
    misfires = []
    for q, exp in CASES:
        votes = sum(classify(client, desc, q) for _ in range(SAMPLES))
        fired = votes > SAMPLES / 2
        ok = fired == exp
        if exp and fired: tp += 1
        elif exp and not fired: fn += 1
        elif not exp and fired: fp += 1
        else: tn += 1
        tag = "ok " if ok else "MISS"
        exp_s = "TRIG" if exp else "NO  "
        print(f"[{tag}] exp={exp_s} votes={votes}/{SAMPLES}  {q[:72]}")
        if not ok:
            misfires.append((q, exp, votes))
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    print(f"\nconfusion: TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"precision={prec:.2f} recall={rec:.2f} accuracy={(tp+tn)/len(CASES):.2f}")
    if misfires:
        print("\nMISFIRES (query | expected | fired-votes):")
        for q, exp, v in misfires:
            print(f"  - {'TRIGGER' if exp else 'NO':7} but {v}/{SAMPLES}: {q}")
    else:
        print("\nno misfires — trigger boundary holds across all 20.")

if __name__ == "__main__":
    main()
