#!/usr/bin/env python3
"""
Generate fixtures/print_format.json from HTML source files.

Usage:
    cd /home/claude/frappe-bench/apps/solidwurth_estimate
    python3 scripts/generate_print_fixtures.py

Re-run whenever .html source files in solidwurth_estimate/estimate/print_format/ are updated.
The modified timestamp is always set to now — Frappe bench migrate uses this to detect changes.

Records generated:
    - "Cost Proposal" from cost_proposal.html
    - "Cost Proposal (BP)" from cost_proposal_bp.html

Each record: doctype=Print Format, standard=No, custom_format=1, disabled=0, module=Estimate
"""

import json
import os
import sys
from datetime import datetime

# Resolve paths relative to this script file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)  # apps/solidwurth_estimate/
SOURCE_DIR = os.path.join(APP_DIR, "solidwurth_estimate", "estimate", "print_format")
FIXTURE_PATH = os.path.join(APP_DIR, "solidwurth_estimate", "fixtures", "print_format.json")

# Map: (html_filename, record_name, doc_type)
PRINT_FORMAT_RECORDS = [
    ("cost_proposal.html", "Cost Proposal", "Estimate"),
    ("cost_proposal_bp.html", "Cost Proposal (BP)", "Estimate"),
    ("cost_proposal_long.html", "Cost Proposal - Long", "Estimate"),
    ("cost_proposal_bp_long.html", "Cost Proposal (BP) - Long", "Estimate"),
]


def read_html(filename):
    """Read HTML source file content."""
    path = os.path.join(SOURCE_DIR, filename)
    if not os.path.exists(path):
        print("ERROR: Source file not found: {}".format(path), file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate():
    """Generate print_format.json fixture records from HTML sources."""
    # Always bump modified timestamp so bench migrate picks up changes
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    records = []
    for html_file, name, doc_type in PRINT_FORMAT_RECORDS:
        html_content = read_html(html_file)
        record = {
            "doctype": "Print Format",
            "name": name,
            "doc_type": doc_type,
            "module": "Estimate",
            "custom_format": 1,
            "standard": "No",
            "disabled": 0,
            "html": html_content,
            "modified": now,
        }
        records.append(record)
        print("Generated: {} ({} chars)".format(name, len(html_content)))

    # Ensure fixtures directory exists
    fixtures_dir = os.path.dirname(FIXTURE_PATH)
    os.makedirs(fixtures_dir, exist_ok=True)

    with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=1, ensure_ascii=False)

    print("\nWritten: {}".format(FIXTURE_PATH))
    print("Records: {}".format(len(records)))
    print("Modified timestamp: {}".format(now))


if __name__ == "__main__":
    generate()
