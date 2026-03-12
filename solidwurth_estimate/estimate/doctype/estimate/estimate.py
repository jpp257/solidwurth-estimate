# Copyright (c) 2026, SolidWurth Corp. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Estimate(Document):
    """
    Estimate master document.

    Naming: EST-.YY.-.#### (e.g. EST-26-0001)
    Linked to Estimate Scope records via estimate field (Connections panel).

    Phase 11 scope:
    - on_trash: cascade delete all linked Estimate Scopes
    - validate: enforce valid status transitions
    - (Phase 12 will add calculate() and beforeSave total computation)
    """

    # Valid status transitions (D30 from CONTEXT.md)
    VALID_TRANSITIONS = {
        "Draft": ["Under Review"],
        "Under Review": ["Approved", "Rejected"],
        "Rejected": ["Draft"],
        "Approved": ["Converted"],
        "Converted": [],
    }

    def on_trash(self):
        """
        Cascade delete all Estimate Scopes linked to this Estimate.
        Prevents orphan records when an Estimate is deleted.
        D7 from CONTEXT.md: on_trash in Estimate controller.
        """
        scope_names = frappe.get_all(
            "Estimate Scope",
            filters={"estimate": self.name},
            pluck="name"
        )
        for scope_name in scope_names:
            frappe.delete_doc("Estimate Scope", scope_name, ignore_permissions=True)

    def validate(self):
        """
        Enforce valid status transitions.
        D30 from CONTEXT.md: Invalid transitions throw error.
        Phase 14 replaces this with Frappe native Workflow.
        """
        if self.is_new():
            # New document — no previous status to compare against
            return

        previous_status = frappe.db.get_value("Estimate", self.name, "status")

        if previous_status is None:
            # Document not yet in DB (shouldn't happen after is_new() check, but guard anyway)
            return

        if previous_status == self.status:
            # No status change — nothing to validate
            return

        allowed = self.VALID_TRANSITIONS.get(previous_status, [])
        if self.status not in allowed:
            allowed_str = ", ".join(allowed) if allowed else "none"
            frappe.throw(
                f"Cannot transition Estimate from '{previous_status}' to '{self.status}'. "
                f"Allowed next status: {allowed_str}."
            )


@frappe.whitelist()
def create_scope_from_template(estimate, template_name, scope_group):
    """
    Create a single Estimate Scope from a Scope Template.
    Copies all L/E/M child rows exactly.

    Called by create_scopes_from_templates (batch) and directly by bot API.
    D8 from CONTEXT.md: server-side Python + client-side JS trigger.

    Args:
        estimate (str): Name of the parent Estimate (e.g. "EST-26-0001")
        template_name (str): Name of the Scope Template to copy
        scope_group (str): Free-text building/area group (e.g. "Guard House")

    Returns:
        str: Name of the created Estimate Scope (e.g. "ESC-26-0001")
    """
    template = frappe.get_doc("Scope Template", template_name)

    scope = frappe.new_doc("Estimate Scope")
    scope.estimate = estimate
    scope.scope_template = template_name
    scope.scope_name = template.template_name
    scope.description = template.description
    scope.dpwh_pay_item = template.dpwh_pay_item
    scope.uom = template.uom
    scope.output_per_day = template.output_per_day
    scope.scope_group = scope_group or ""

    # Copy Labor Gang rows
    for row in template.labor_rows:
        scope.append("labor_rows", {
            "role": row.role,
            "persons": row.persons,
            "daily_rate": row.daily_rate,
        })

    # Copy Equipment rows
    for row in template.equipment_rows:
        scope.append("equipment_rows", {
            "item": row.item,
            "units": row.units,
            "daily_rate": row.daily_rate,
            "ownership_type": row.ownership_type,
        })

    # Copy Material rows
    for row in template.material_rows:
        scope.append("material_rows", {
            "item": row.item,
            "qty": row.qty,
            "wastage_percent": row.wastage_percent,
            "uom": row.uom,
            "rate": row.rate,
        })

    scope.insert(ignore_permissions=False)
    return scope.name


@frappe.whitelist()
def create_scopes_from_templates(estimate, template_names, scope_group):
    """
    Create multiple Estimate Scopes from a list of Scope Templates.
    Accepts template_names as either a Python list or a JSON string (from JS frappe.call).

    Called from estimate.js show_template_picker dialog.
    Also callable directly via bot API for AC3.

    Args:
        estimate (str): Name of the parent Estimate
        template_names (list|str): List of Scope Template names, or JSON string of the list
        scope_group (str): Scope group to assign to all created scopes

    Returns:
        list[str]: Names of all created Estimate Scopes
    """
    # frappe.call from JS sends lists as JSON strings
    if isinstance(template_names, str):
        template_names = frappe.parse_json(template_names)

    if not template_names:
        frappe.throw("No templates selected.")

    created_scopes = []
    for template_name in template_names:
        scope_name = create_scope_from_template(estimate, template_name, scope_group)
        created_scopes.append(scope_name)

    return created_scopes
