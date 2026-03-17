# Copyright (c) 2026, SolidWurth Corp. and contributors
# For license information, please see license.txt

import frappe


def before_delete_project(doc, method):
    """Block deletion of Projects linked to an Estimate. D13.
    Protects the audit trail — a Converted Estimate is permanently linked to its Project.
    """
    if doc.get("custom_estimate"):
        frappe.throw(
            f"Cannot delete Project — linked to Estimate {doc.custom_estimate}. "
            "To proceed, create a new Estimate instead of re-using this project."
        )
