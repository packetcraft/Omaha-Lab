#!/usr/bin/env python3
"""
bench.py — Evaluation harness for the Omaha-Lab attack prompt library.

Loads every YAML file under prompts/, fires each prompt against the guard
stack, and reports hits/misses versus the expected outcome declared in the
prompt's guard_expected field.

Modes
-----
  (default)      Full guard stack: LlamaGuard.check_input() — needs llama-guard3
  --regex-only   Regex pre-filter only — no Ollama call, instant results

Filters
-------
  --category LLM01          Only prompts in this OWASP category
  --layer    regex           Only prompts expected to be caught by this layer
  --difficulty easy          Only prompts with this difficulty rating

Output
------
  (default)    Coloured table on stdout
  --json       JSON summary + result list (stdout or --output FILE)

Examples
--------
  python bench.py --regex-only
  python bench.py --category LLM01 --layer regex
  python bench.py --json --output results.json
  python bench.py --base-url http://localhost:11434
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# Ensure stdout can handle Unicode box-drawing characters on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

class C:
    _t     = sys.stdout.isatty()
    RESET  = "\033[0m"  if _t else ""
    BOLD   = "\033[1m"  if _t else ""
    GREEN  = "\033[92m" if _t else ""
    RED    = "\033[91m" if _t else ""
    YELLOW = "\033[93m" if _t else ""
    CYAN   = "\033[96m" if _t else ""
    GRAY   = "\033[90m" if _t else ""
    DIM    = "\033[2m"  if _t else ""

STATUS_COLOUR = {
    "pass": C.GREEN,
    "fail": C.RED,
    "skip": C.GRAY,
    "info": C.YELLOW,
}


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def load_prompts(prompts_dir: str, filters: dict) -> list[dict]:
    files = sorted(glob.glob(f"{prompts_dir}/**/*.yaml", recursive=True))
    if not files:
        sys.exit(f"[bench] No YAML files found under {prompts_dir!r}")
    prompts = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict) or "id" not in data:
            continue
        if filters.get("category") and data.get("category") != filters["category"]:
            continue
        if filters.get("layer") and data.get("layer") != filters["layer"]:
            continue
        if filters.get("difficulty") and data.get("difficulty") != filters["difficulty"]:
            continue
        prompts.append(data)
    return prompts


# ---------------------------------------------------------------------------
# Skip logic
# ---------------------------------------------------------------------------

def skip_reason(p: dict, regex_only: bool) -> str | None:
    if p.get("rag"):
        return "rag=true (ChromaDB not supported in bench mode)"
    if p.get("hitl"):
        return "hitl=true (requires interactive approval)"
    if regex_only and p.get("layer") not in ("regex", None, "") and p.get("guard_expected") == "blocked":
        return f"layer={p.get('layer')!r} (not testable in --regex-only mode)"
    return None


# ---------------------------------------------------------------------------
# Evaluation — regex-only (no Ollama)
# ---------------------------------------------------------------------------

def eval_regex_only(p: dict) -> dict:
    from guardrails.llama_guard import _INJECTION_PATTERNS

    text     = (p.get("prompt") or "").strip()
    expected = p.get("guard_expected", "varies")
    exp_layer = p.get("layer", "")

    matched = any(pat.search(text) for pat in _INJECTION_PATTERNS)
    actual  = "blocked" if matched else "passes"

    if expected == "varies":
        status = "info"
    elif exp_layer == "regex":
        # Regex-layer prompts must be caught by the regex
        status = "pass" if matched else "fail"
    elif expected == "passes":
        # Benign prompts must NOT be caught by the regex (false-positive check)
        status = "pass" if not matched else "fail"
    else:
        # Non-regex blocked prompts: we can't score them in regex-only mode,
        # but we can show whether the regex caught them anyway (coverage info)
        status = "info"

    return _result(p, expected, actual, "regex" if matched else "", status, 0.0)


# ---------------------------------------------------------------------------
# Evaluation — full guard stack via LlamaGuard.check_input()
# ---------------------------------------------------------------------------

def eval_full_guard(p: dict, guard) -> dict:
    text     = (p.get("prompt") or "").strip()
    expected = p.get("guard_expected", "varies")

    t0 = time.perf_counter()
    result = guard.check_input(text)
    elapsed = time.perf_counter() - t0

    actual   = "blocked" if not result.safe else "passes"
    layer_hit = ""
    if not result.safe:
        layer_hit = (
            "regex" if result.raw_response == "injection-prefilter" else "llama_guard"
        )

    if expected == "varies":
        status = "info"
    elif actual == expected:
        status = "pass"
    else:
        status = "fail"

    return _result(p, expected, actual, layer_hit, status, elapsed)


def _result(p, expected, actual, layer_hit, status, elapsed):
    return {
        "id":         p["id"],
        "name":       p.get("name", ""),
        "category":   p.get("category", ""),
        "layer":      p.get("layer", ""),
        "difficulty": p.get("difficulty", ""),
        "expected":   expected,
        "actual":     actual,
        "layer_hit":  layer_hit,
        "status":     status,
        "elapsed":    round(elapsed, 3),
    }


# ---------------------------------------------------------------------------
# Table output
# ---------------------------------------------------------------------------

def _col(status: str) -> str:
    return STATUS_COLOUR.get(status, "") + status.upper().ljust(4) + C.RESET

def print_table(rows: list[dict]) -> None:
    id_w   = max(len(r["id"])   for r in rows) + 1
    name_w = min(max(len(r["name"]) for r in rows) + 1, 34)

    header = (
        f"{'ID':<{id_w}}  {'NAME':<{name_w}}  "
        f"{'CAT':<6}  {'LAYER':<11}  {'DIFF':<6}  "
        f"{'EXPECTED':<8}  {'ACTUAL':<7}  {'HIT':<11}  STATUS  TIME"
    )
    print(C.BOLD + header + C.RESET)
    print(C.DIM + "─" * len(header) + C.RESET)

    for r in rows:
        status_str = _col(r["status"])
        name = r["name"][:name_w].ljust(name_w)
        elapsed = f"{r['elapsed']:.3f}s" if r["elapsed"] else "—"
        print(
            f"{r['id']:<{id_w}}  {name}  "
            f"{r['category']:<6}  {r['layer']:<11}  {r['difficulty']:<6}  "
            f"{r['expected']:<8}  {r['actual']:<7}  {r['layer_hit']:<11}  "
            f"{status_str}  {C.GRAY}{elapsed}{C.RESET}"
        )


def print_summary(rows: list[dict], skips: list[dict], config: dict, total_elapsed: float) -> None:
    counts = {"pass": 0, "fail": 0, "skip": len(skips), "info": 0}
    for r in rows:
        counts[r["status"]] += 1

    guard_label = "regex-only" if config["regex_only"] else ("on" if config["guard"] else "off")
    print()
    print(
        f"{C.BOLD}Results:{C.RESET}  "
        f"{C.GREEN}{counts['pass']} passed{C.RESET}  "
        f"{C.RED}{counts['fail']} failed{C.RESET}  "
        f"{C.GRAY}{counts['skip']} skipped{C.RESET}  "
        f"{C.YELLOW}{counts['info']} info{C.RESET}  "
        f"| guard: {guard_label}  total: {len(rows)+len(skips)}  "
        f"time: {total_elapsed:.2f}s"
    )

    # Per-category breakdown
    categories: dict[str, dict] = {}
    for r in rows:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"pass": 0, "fail": 0, "info": 0}
        categories[cat][r["status"]] = categories[cat].get(r["status"], 0) + 1
    if categories:
        print()
        print(C.BOLD + "By category:" + C.RESET)
        for cat in sorted(categories):
            c = categories[cat]
            print(
                f"  {cat:<8}  "
                f"{C.GREEN}{c.get('pass',0):>2} pass{C.RESET}  "
                f"{C.RED}{c.get('fail',0):>2} fail{C.RESET}  "
                f"{C.YELLOW}{c.get('info',0):>2} info{C.RESET}"
            )

    # Per-layer breakdown
    layers: dict[str, dict] = {}
    for r in rows:
        lyr = r["layer"] or "unknown"
        if lyr not in layers:
            layers[lyr] = {"pass": 0, "fail": 0, "info": 0}
        layers[lyr][r["status"]] = layers[lyr].get(r["status"], 0) + 1
    if layers:
        print()
        print(C.BOLD + "By layer:" + C.RESET)
        for lyr in sorted(layers):
            c = layers[lyr]
            print(
                f"  {lyr:<13}  "
                f"{C.GREEN}{c.get('pass',0):>2} pass{C.RESET}  "
                f"{C.RED}{c.get('fail',0):>2} fail{C.RESET}  "
                f"{C.YELLOW}{c.get('info',0):>2} info{C.RESET}"
            )

    # Failures detail
    failures = [r for r in rows if r["status"] == "fail"]
    if failures:
        print()
        print(C.RED + C.BOLD + "Failures:" + C.RESET)
        for r in failures:
            print(
                f"  {C.RED}✗{C.RESET}  {r['id']}  —  "
                f"expected {r['expected']!r}, got {r['actual']!r}"
                + (f"  (caught by {r['layer_hit']!r})" if r["layer_hit"] else "")
            )

    if skips:
        print()
        print(C.GRAY + C.BOLD + "Skipped:" + C.RESET)
        for s in skips:
            print(f"  {C.GRAY}–{C.RESET}  {s['id']}  —  {s['reason']}")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json(rows: list[dict], skips: list[dict], config: dict, total_elapsed: float) -> dict:
    counts = {"pass": 0, "fail": 0, "skip": len(skips), "info": 0}
    for r in rows:
        counts[r["status"]] += 1
    return {
        "config":       config,
        "total_elapsed": round(total_elapsed, 3),
        "summary":      counts,
        "results":      rows,
        "skipped":      skips,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Omaha-Lab evaluation harness — fires attack prompts, reports guard hits/misses.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--prompts-dir", default="prompts", metavar="DIR",
                        help="Root directory of the prompt library (default: prompts)")
    parser.add_argument("--regex-only", action="store_true",
                        help="Test regex pre-filter only — no Ollama call required")
    parser.add_argument("--category",   metavar="CODE",
                        help="Filter: only run prompts with this OWASP category (e.g. LLM01)")
    parser.add_argument("--layer",      metavar="NAME",
                        help="Filter: only run prompts with this expected catch layer")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"],
                        help="Filter: only run prompts with this difficulty")
    parser.add_argument("--base-url",
                        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                        metavar="URL",
                        help="Ollama base URL (default: OLLAMA_BASE_URL env or http://localhost:11434)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of a table")
    parser.add_argument("--output", metavar="FILE",
                        help="Write JSON output to FILE (implies --json)")
    args = parser.parse_args()

    if args.output:
        args.json = True

    filters = {
        k: v for k, v in {
            "category":   args.category,
            "layer":      args.layer,
            "difficulty": args.difficulty,
        }.items() if v
    }

    prompts = load_prompts(args.prompts_dir, filters)
    if not prompts:
        sys.exit("[bench] No prompts matched the given filters.")

    # Build guard (not needed for --regex-only)
    guard = None
    if not args.regex_only:
        from guardrails.llama_guard import LlamaGuard
        guard = LlamaGuard(base_url=args.base_url)
        if not args.json:
            print(f"[bench] Guard: full stack (llama-guard3 @ {args.base_url})")
            print(f"[bench] Loaded {len(prompts)} prompts — running...\n")
    else:
        if not args.json:
            print(f"[bench] Guard: regex pre-filter only (no Ollama)")
            print(f"[bench] Loaded {len(prompts)} prompts — running...\n")

    rows: list[dict] = []
    skips: list[dict] = []
    t_start = time.perf_counter()

    for p in prompts:
        reason = skip_reason(p, args.regex_only)
        if reason:
            skips.append({"id": p["id"], "name": p.get("name", ""), "reason": reason})
            continue

        if args.regex_only:
            row = eval_regex_only(p)
        else:
            row = eval_full_guard(p, guard)

        rows.append(row)

        if not args.json:
            status_str = _col(row["status"])
            print(f"  {status_str}  {row['id']}")

    total_elapsed = time.perf_counter() - t_start

    config = {
        "regex_only":  args.regex_only,
        "guard":       not args.regex_only,
        "base_url":    args.base_url,
        "filters":     filters,
    }

    if args.json:
        payload = build_json(rows, skips, config, total_elapsed)
        out = json.dumps(payload, indent=2)
        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
            print(f"[bench] Results written to {args.output}")
        else:
            print(out)
        return

    print()
    print_table(rows)
    print_summary(rows, skips, config, total_elapsed)

    # Exit non-zero if any failures (useful for CI)
    failures = sum(1 for r in rows if r["status"] == "fail")
    sys.exit(failures)


if __name__ == "__main__":
    main()
