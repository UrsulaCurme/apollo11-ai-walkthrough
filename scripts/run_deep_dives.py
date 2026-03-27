#!/usr/bin/env python3
"""
Apollo 11 AGC — AI Deep Dive Runner

Uses Claude Code CLI (Max plan, no API key).
Model: claude-opus-4-6 (Opus 4.6)

Usage:
  python run_deep_dives.py --fetch-manual
  python run_deep_dives.py --dive 3a
  python run_deep_dives.py --all
"""

import argparse
import datetime
import httpx
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APOLLO_REPO  = PROJECT_ROOT / "Apollo-11"
PROMPTS_DIR  = PROJECT_ROOT / "prompts"
OUTPUT_DIR   = PROJECT_ROOT / "walkthrough"
CACHE_DIR    = PROJECT_ROOT / "scripts" / "manual_cache"
LOG_FILE     = PROJECT_ROOT / "scripts" / "run_log.jsonl"

MANUAL_URL = "https://www.ibiblio.org/apollo/assembly_language_manual.html"

DIVES = {
    "3a": {
        "name": "The Executive (Job Scheduler)",
        "files": ["Luminary099/EXECUTIVE.agc"],
        "output": "01-executive.md",
        "prompt_section": "3A",
    },
    "3a2": {
        "name": "The Waitlist (Timer-Driven Scheduler)",
        "files": ["Luminary099/WAITLIST.agc"],
        "output": "02-waitlist.md",
        "prompt_section": "3A2",
    },
    "3b": {
        "name": "Fresh Start & Restart (1202 Alarm)",
        "files": ["Luminary099/FRESH_START_AND_RESTART.agc",
                  "Luminary099/ALARM_AND_ABORT.agc"],
        "output": "03-restart.md",
        "prompt_section": "3B",
    },
    "3c": {
        "name": "Landing Guidance Equations",
        "files": ["Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc"],
        "output": "04-landing-guidance.md",
        "prompt_section": "3C",
    },
    "3d": {
        "name": "BURN_BABY_BURN — Master Ignition",
        "files": ["Luminary099/BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc"],
        "output": "05-burn-baby-burn.md",
        "prompt_section": "3D",
    },
    "3e": {
        "name": "The Interpreter",
        "files": ["Luminary099/INTERPRETER.agc",
                  "Luminary099/INTER-BANK_COMMUNICATION.agc"],
        "output": "06-interpreter.md",
        "prompt_section": "3E",
    },
    "3f": {
        "name": "Pinball Game — DSKY Interface",
        "files": ["Luminary099/PINBALL_GAME_BUTTONS_AND_LIGHTS.agc",
                  "Luminary099/PINBALL_NOUN_TABLES.agc"],
        "output": "07-dsky-interface.md",
        "prompt_section": "3F",
    },
    "synthesis": {
        "name": "Lessons for 2026 — Synthesis",
        "files": [],
        "walkthrough_inputs": [
            "01-executive.md", "02-waitlist.md", "03-restart.md",
            "04-landing-guidance.md", "05-burn-baby-burn.md",
            "06-interpreter.md", "07-dsky-interface.md",
        ],
        "output": "08-lessons.md",
        "prompt_section": "SYNTHESIS",
    },
}


# --- Heartbeat ---
def heartbeat(stop_event, t0):
    while not stop_event.is_set():
        elapsed = int(time.time() - t0)
        print(f"\r  Working... {elapsed}s", end="", flush=True)
        stop_event.wait(10)
    print()


# --- Run Claude Code CLI ---
def run_claude(prompt, model, timeout=1800):
    cmd = ["claude", "-p", "--output-format", "text", "--model", model]
    t0 = time.time()
    stop = threading.Event()
    hb = threading.Thread(target=heartbeat, args=(stop, t0), daemon=True)
    hb.start()
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill(); stop.set()
        print(f"\n  TIMEOUT after {timeout}s")
        return None, time.time() - t0
    except FileNotFoundError:
        stop.set()
        print("\n  ERROR: 'claude' not found"); sys.exit(1)
    finally:
        stop.set(); hb.join(timeout=2)

    elapsed = time.time() - t0
    # Filter out noisy but harmless plugin errors
    stderr_clean = "\n".join(
        l for l in stderr.splitlines()
        if "mgrep" not in l and "ProcessLookupError" not in l
        and "SessionEnd hook" not in l and "os.kill" not in l
    ).strip()
    if stderr_clean:
        print(f"  stderr: {stderr_clean[:300]}")
    if proc.returncode != 0:
        print(f"  ERROR (exit={proc.returncode}): {stdout.strip()[:300]}")
        return None, elapsed
    output = stdout.strip()
    if not output or output.startswith("Error:"):
        print(f"  ERROR: {output[:300]}")
        return None, elapsed
    print(f"  Completed in {elapsed:.1f}s ({len(output):,} chars)")
    return output, elapsed


# --- Manual fetch/cache ---
def fetch_manual():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "assembly_language_manual.html"
    if cache.exists():
        print(f"  Manual cached at {cache}")
        return cache.read_text(encoding="utf-8")
    print(f"  Fetching {MANUAL_URL} ...")
    resp = httpx.get(MANUAL_URL, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    cache.write_text(resp.text, encoding="utf-8")
    print(f"  Cached ({len(resp.text):,} chars)")
    return resp.text


def extract_manual_sections(html):
    cache = CACHE_DIR / "manual_sections.txt"
    if cache.exists():
        print(f"  Using cached sections ({cache})")
        return cache.read_text(encoding="utf-8")

    def strip_tags(s):
        s = re.sub(r'<style[^>]*>.*?</style>', '', s, flags=re.DOTALL)
        s = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.DOTALL)
        s = re.sub(r'<[^>]+>', ' ', s)
        for e, c in [('&amp;','&'),('&lt;','<'),('&gt;','>'),('&nbsp;',' ')]:
            s = s.replace(e, c)
        s = re.sub(r'&#\d+;', '', s)
        return re.sub(r'[ \t]+', ' ', re.sub(r'\n{3,}', '\n\n', s)).strip()

    sections = [
        ("The_Interpreter_vs._the_CPU", "Formatting"),
        ("Data_Representation", "CPU_Architecture_Registers"),
        ("CPU_Architecture_Registers", "Memory_Map"),
        ("Memory_Map", "Interrupt_Processing"),
        ("Interrupt_Processing", "Instruction_Representation"),
        ("Instruction_Representation", "AGC4_Instruction_Set"),
        ("AGC4_Instruction_Set", "Pseudo-Operations"),
    ]
    extracted = []
    for sid, eid in sections:
        s = html.find(f'id="{sid}"')
        if s == -1: s = html.find(f'name="{sid}"')
        e = html.find(f'id="{eid}"')
        if e == -1: e = html.find(f'name="{eid}"')
        if s != -1 and e != -1 and e > s:
            extracted.append(strip_tags(html[s:e]))
    result = "\n\n---\n\n".join(extracted)
    if len(result) > 60000:
        result = result[:60000] + "\n\n[... truncated ...]"
    cache.write_text(result, encoding="utf-8")
    print(f"  Extracted {len(result):,} chars")
    return result


# --- Load prompts ---
def load_phase1():
    text = (PROMPTS_DIR / "phase1-context.md").read_text(encoding="utf-8")
    marker = "## PROMPT BEGINS HERE"
    idx = text.find(marker)
    return text[idx + len(marker):].strip() if idx != -1 else text.strip()


def load_dive_prompt(section_id):
    text = (PROMPTS_DIR / "phase3-deep-dives.md").read_text(encoding="utf-8")
    for pat in [f"## {section_id}:", f"## {section_id} "]:
        start = text.find(pat)
        if start != -1: break
    if start == -1:
        raise ValueError(f"Section {section_id} not found")
    nxt = text.find("\n## ", start + 1)
    chunk = text[start:] if nxt == -1 else text[start:nxt]
    cs, ce = chunk.find("```"), chunk.rfind("```")
    if cs != -1 and ce != -1 and ce > cs:
        return chunk[cs+3:ce].strip()
    return chunk.strip()


# --- Run a single dive ---
def run_dive(dive_key, model, manual_sections):
    dive = DIVES[dive_key]
    print(f"\n{'='*60}")
    print(f"  DIVE {dive_key.upper()}: {dive['name']}")
    print(f"{'='*60}")

    is_synthesis = "walkthrough_inputs" in dive
    dive_prompt = load_dive_prompt(dive["prompt_section"])

    if is_synthesis:
        # Load completed walkthrough chapters
        sources = {}
        missing = []
        for fn in dive["walkthrough_inputs"]:
            fp = OUTPUT_DIR / fn
            if not fp.exists():
                missing.append(fn)
            else:
                c = fp.read_text(encoding="utf-8")
                sources[fn] = c
                print(f"  Loaded {fn} ({len(c):,} chars)")
        if missing:
            print(f"  MISSING: {', '.join(missing)} — run those dives first")
            return {"dive": dive_key, "error": f"missing walkthroughs: {', '.join(missing)}"}

        wt_blocks = "\n\n".join(
            f"### {fn}\n\n{c}" for fn, c in sources.items()
        )
        prompt = f"""Respond with the full markdown document directly in your text response.
Do NOT try to create files or write files. Do NOT use any tools.
Just output the markdown content as your response text.

You have read seven deep-dive walkthroughs of the Apollo 11 AGC flight software.
Start directly with the markdown heading. No preamble.

## WALKTHROUGH CHAPTERS

{wt_blocks}

---

## ANALYSIS TASK

{dive_prompt}

Write an opinionated, well-structured essay. Reference specific examples
from the walkthroughs above.
"""
    else:
        # Load AGC source files
        sources = {}
        for rel in dive["files"]:
            fp = APOLLO_REPO / rel
            if not fp.exists():
                print(f"  WARNING: {fp} not found"); continue
            c = fp.read_text(encoding="utf-8", errors="replace")
            sources[rel] = c
            print(f"  Loaded {rel} ({len(c):,} chars)")
        if not sources:
            return {"dive": dive_key, "error": "no source files"}

        phase1 = load_phase1()
        src_blocks = "\n\n".join(
            f"### Source: {fn}\n\n```agc\n{c}\n```" for fn, c in sources.items()
        )
        prompt = f"""Respond with the full markdown document directly in your text response.
Do NOT try to create files or write files. Do NOT use any tools.
Just output the markdown content as your response text.

All source code and reference material is provided below.
Start directly with the markdown heading. No preamble.

## AGC4 ARCHITECTURE REFERENCE

{phase1}

---

## AUTHORITATIVE AGC4 REFERENCE (Virtual AGC Manual)

Use this as ground truth. If it conflicts with the above, trust this.

{manual_sections}

---

## SOURCE FILES

{src_blocks}

---

## ANALYSIS TASK

{dive_prompt}

Write a detailed, well-structured markdown document with actual code
snippets and line references. Flag any uncertain interpretations.
"""

    print(f"\n  Prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)")
    output, elapsed = run_claude(prompt, model)

    if output is None:
        return {"dive": dive_key, "error": "failed"}

    out_path = OUTPUT_DIR / dive["output"]
    out_path.write_text(output, encoding="utf-8")
    print(f"  Saved -> {out_path}")

    meta = {
        "dive": dive_key, "name": dive["name"], "model": model,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "prompt_chars": len(prompt), "output_chars": len(output),
        "output_file": str(out_path), "source_files": dive["files"],
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(meta) + "\n")
    return meta


# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Apollo 11 AGC deep dives")
    parser.add_argument("--fetch-manual", action="store_true")
    parser.add_argument("--dive", choices=list(DIVES.keys()))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--model", default="claude-opus-4-6")
    args = parser.parse_args()

    if not APOLLO_REPO.exists():
        print(f"ERROR: Apollo-11 repo not found at {APOLLO_REPO}")
        sys.exit(1)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    mc = CACHE_DIR / "manual_sections.txt"

    if args.fetch_manual or not mc.exists():
        print("\nFetching AGC manual...")
        raw = fetch_manual()
        print("Extracting key sections...")
        manual = extract_manual_sections(raw)
    else:
        manual = mc.read_text(encoding="utf-8")
        print(f"Using cached manual ({len(manual):,} chars)")

    if args.fetch_manual and not args.dive and not args.all:
        print("Manual cached. Run with --dive 3a or --all")
        sys.exit(0)

    if not args.dive and not args.all:
        parser.print_help()
        sys.exit(0)

    runs = list(DIVES.keys()) if args.all else [args.dive]
    results = []
    for dk in runs:
        results.append(run_dive(dk, args.model, manual))
        if len(runs) > 1 and dk != runs[-1]:
            print("\n  Pausing 15s...")
            time.sleep(15)

    print(f"\n{'='*60}\n  DONE\n{'='*60}")
    for r in results:
        if "error" in r:
            print(f"  x {r['dive']}: {r['error']}")
        else:
            print(f"  + {r['dive']}: {r['name']} "
                  f"-- {r['output_chars']:,} chars in {r['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
