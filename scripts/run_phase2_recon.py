#!/usr/bin/env python3
"""
Phase 2 — Repo Structure Reconnaissance

Scans the Apollo-11 repo headers, sends to Claude for categorization.
Uses Claude Code CLI (Max plan, no API key needed).

Usage:
  python run_phase2_recon.py
  python run_phase2_recon.py --model claude-opus-4-6
"""

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APOLLO_REPO  = PROJECT_ROOT / "Apollo-11"
PROMPTS_DIR  = PROJECT_ROOT / "prompts"
OUTPUT_DIR   = PROJECT_ROOT / "walkthrough"


def heartbeat(stop_event, t0):
    while not stop_event.is_set():
        elapsed = int(time.time() - t0)
        print(f"\r  Working... {elapsed}s", end="", flush=True)
        stop_event.wait(10)
    print()


def extract_header(filepath, max_lines=40):
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return f"[ERROR: {e}]"
    header = []
    for line in lines[:max_lines]:
        s = line.strip()
        if s.startswith("#") or s.startswith("$") or s == "":
            header.append(line)
        else:
            break
    return "\n".join(header)


def scan_module(module_dir):
    results = []
    for f in sorted(module_dir.glob("*.agc")):
        lc = sum(1 for _ in f.open(encoding="utf-8", errors="replace"))
        results.append({"filename": f.name, "line_count": lc, "header": extract_header(f)})
    return results


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
        print(f"\n  TIMEOUT after {timeout}s"); sys.exit(1)
    except FileNotFoundError:
        stop.set()
        print("\n  ERROR: 'claude' not found"); sys.exit(1)
    finally:
        stop.set(); hb.join(timeout=2)

    elapsed = time.time() - t0
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


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Repo structure recon")
    parser.add_argument("--model", default="claude-opus-4-6")
    args = parser.parse_args()

    if not APOLLO_REPO.exists():
        print(f"ERROR: Apollo-11 repo not found at {APOLLO_REPO}")
        sys.exit(1)

    print("Scanning Luminary099 (Lunar Module)...")
    lm = scan_module(APOLLO_REPO / "Luminary099")
    print(f"  Found {len(lm)} .agc files")

    print("Scanning Comanche055 (Command Module)...")
    cm = scan_module(APOLLO_REPO / "Comanche055")
    print(f"  Found {len(cm)} .agc files")

    def fmt(files, name):
        parts = [f"## {name}\n"]
        for f in files:
            parts.append(f"### {f['filename']} ({f['line_count']} lines)\n```\n{f['header']}\n```\n")
        return "\n".join(parts)

    prompt = f"""Respond with the full markdown document directly in your text response.
Do NOT try to create files or write files. Do NOT use any tools.
Just output the markdown content as your response text.

All data is provided below. Start directly with the markdown heading. No preamble.

Produce a markdown document with two major sections: Luminary099 and Comanche055.
Each section must contain a table grouped by functional category with columns:
| Category | Filename | Lines | Purpose |

Categories: Executive/Scheduler, Restart/Fault Handling, Guidance/Navigation,
Propulsion/Thrust Control, Autopilot/Attitude Control, DSKY/Display, IMU/Sensors,
Interpreter/Math, System Infrastructure, Mission-Specific, Configuration/Data.

After both tables, add a section listing files that appear in BOTH modules
(shared infrastructure) vs files unique to one module.

Here are the file headers:

{fmt(lm, 'Luminary099 (Lunar Module)')}

---

{fmt(cm, 'Comanche055 (Command Module)')}
"""

    print(f"\nPrompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)")
    print(f"Model: {args.model}")

    output, elapsed = run_claude(prompt, args.model)
    if output is None:
        sys.exit(1)

    out_path = OUTPUT_DIR / "00-repo-structure.md"
    out_path.write_text(output, encoding="utf-8")
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
