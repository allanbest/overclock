#!/usr/bin/env python3
"""Guide the compaction summary: keep what's needed to continue, drop what's been used up."""
import sys

sys.stdin.read()  # event payload; not needed
print("""When summarizing, keep: the user's goal and constraints; decisions made and why; exact file paths, names, commands and identifiers in play; errors or failing tests still unresolved (verbatim); what's done vs. still to do. Drop: raw tool output that was already acted on, exploration dead ends, superseded plans, and conversational filler. Be compact: bullet points, no prose.""")
