"""Print a clerk system prompt for a case/variant.

Usage:
    python -m sim.dump CASE-A            # happy path
    python -m sim.dump CASE-C off_by_one
"""
import sys

from .personas import PERSONAS, render_clerk_prompt

if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "CASE-A"
    variant = sys.argv[2] if len(sys.argv) > 2 else "happy"
    if case_id not in PERSONAS:
        sys.exit(f"unknown case {case_id}; choose from {list(PERSONAS)}")
    print(render_clerk_prompt(case_id, variant))
