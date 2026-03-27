#!/bin/bash
#
# Apollo 11 AGC AI Walkthrough — Runner
#
# Usage:
#   ./run.sh setup      — Clone repo + install deps
#   ./run.sh recon      — Phase 2: repo structure scan
#   ./run.sh dive 3a    — Run a single deep dive
#   ./run.sh dive all   — Run all 5 deep dives
#   ./run.sh status     — Show what's been generated
#

set -euo pipefail
cd "$(dirname "$0")"

REPO_DIR="Apollo-11"
SCRIPTS_DIR="scripts"
WALKTHROUGH_DIR="walkthrough"

case "${1:-help}" in

  setup)
    echo "=== Setting up ==="
    if [ ! -d "$REPO_DIR" ]; then
      echo "Cloning Apollo-11 repo..."
      git clone https://github.com/chrislgarry/Apollo-11.git "$REPO_DIR"
    else
      echo "Apollo-11 repo already exists at $REPO_DIR"
    fi

    echo "Installing Python dependencies..."
    pip install -r "$SCRIPTS_DIR/requirements.txt"

    echo "Fetching and caching AGC manual..."
    python "$SCRIPTS_DIR/run_deep_dives.py" --fetch-manual

    echo ""
    echo "=== Ready ==="
    echo "Next steps:"
    echo "  ./run.sh recon       — Map the repo structure"
    echo "  ./run.sh dive 3a     — Run first deep dive (Executive)"
    echo "  ./run.sh dive all    — Run all deep dives"
    ;;

  recon)
    echo "=== Phase 2: Repo Reconnaissance ==="
    python "$SCRIPTS_DIR/run_phase2_recon.py" "${@:2}"
    echo ""
    echo "Output: $WALKTHROUGH_DIR/00-repo-structure.md"
    ;;

  dive)
    TARGET="${2:-help}"
    if [ "$TARGET" = "all" ]; then
      echo "=== Phase 3: All Deep Dives ==="
      python "$SCRIPTS_DIR/run_deep_dives.py" --all "${@:3}"
    elif [ "$TARGET" = "help" ]; then
      echo "Usage: ./run.sh dive <3a|3a2|3b|3c|3d|3e|3f|synthesis|all>"
      echo ""
      echo "  3a        — Executive (job scheduler)"
      echo "  3a2       — Waitlist (timer-driven task scheduler)"
      echo "  3b        — Fresh Start & Restart (1202 alarm)"
      echo "  3c        — Landing Guidance Equations (P63/P64/P66)"
      echo "  3d        — BURN_BABY_BURN (master ignition)"
      echo "  3e        — The Interpreter (virtual machine)"
      echo "  3f        — Pinball Game (DSKY interface)"
      echo "  synthesis — Lessons for 2026 (requires all dives completed)"
      echo "  all       — Run all 8 sequentially"
    else
      echo "=== Phase 3: Deep Dive $TARGET ==="
      python "$SCRIPTS_DIR/run_deep_dives.py" --dive "$TARGET" "${@:3}"
    fi
    ;;

  status)
    echo "=== Walkthrough Status ==="
    echo ""
    for f in "$WALKTHROUGH_DIR"/*.md; do
      name=$(basename "$f")
      lines=$(wc -l < "$f" 2>/dev/null || echo "0")
      if [ "$lines" -le 5 ]; then
        echo "  ⬜  $name  (placeholder)"
      else
        echo "  ✅  $name  ($lines lines)"
      fi
    done
    echo ""
    if [ -f "$SCRIPTS_DIR/run_log.jsonl" ]; then
      echo "=== Run Log ==="
      echo "  $(wc -l < "$SCRIPTS_DIR/run_log.jsonl") API calls logged"
      echo "  Last run: $(tail -1 "$SCRIPTS_DIR/run_log.jsonl" | python3 -c "import sys,json; print(json.load(sys.stdin).get('timestamp','?'))" 2>/dev/null || echo "?")"
    fi
    ;;

  help|*)
    echo "Apollo 11 AGC AI Walkthrough"
    echo ""
    echo "Usage: ./run.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup    Clone Apollo-11 repo, install deps, cache AGC manual"
    echo "  recon    Phase 2: scan repo structure"
    echo "  dive     Phase 3: run deep dives (3a|3b|3c|3d|3e|all)"
    echo "  status   Show which walkthrough files are generated"
    echo "  help     This message"
    echo ""
    echo "Options (pass after command):"
    echo "  --verbose    Show Claude Code progress"
    echo "  --model X    Override model (e.g. claude-sonnet-4-20250514)"
    ;;
esac
