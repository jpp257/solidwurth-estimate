# Copyright (c) 2026, SolidWurth Corp. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


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
        Enforce valid status transitions and compute waterfall totals.
        D30 from CONTEXT.md: Invalid transitions throw error.
        D9/D10/D11: Dual waterfall — all scopes and non-optional scopes.
        Phase 14 replaces status transitions with Frappe native Workflow.
        """
        self._validate_status_transition()
        self._calculate_totals()

    def _validate_status_transition(self):
        """Enforce valid status transitions (D30). Extracted from original validate."""
        if self.is_new():
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

    def _calculate_totals(self):
        """
        Compute dual waterfall totals from all linked Estimate Scopes.
        D9: Recalculation runs on Estimate save only.
        D10: Optional scopes get full waterfall.
        D11: grand_total = all scopes. base_grand_total = non-optional only.
        """
        scopes = frappe.db.sql("""
            SELECT name, direct_cost, is_optional
            FROM `tabEstimate Scope`
            WHERE estimate = %s
        """, self.name, as_dict=True)

        total_direct = flt(sum(flt(s.direct_cost) for s in scopes), 2)
        base_direct = flt(sum(flt(s.direct_cost) for s in scopes if not s.is_optional), 2)

        def waterfall(dc):
            ocm = flt(dc * flt(self.ocm_percent) / 100, 2)
            profit = flt((dc + ocm) * flt(self.profit_percent) / 100, 2)
            sub = flt(dc + ocm + profit, 2)
            vat = flt(sub * flt(self.vat_percent) / 100, 2) if self.vat_inclusive else 0.0
            grand = flt(sub + vat, 2)
            return ocm, profit, sub, vat, grand

        ocm_amt, profit_amt, sub_amt, vat_amt, grand = waterfall(total_direct)

        self.direct_cost = total_direct
        self.ocm_amount = ocm_amt
        self.profit_amount = profit_amt
        self.subtotal = sub_amt
        self.vat_amount = vat_amt
        self.grand_total = grand

        _, _, _, _, base_grand = waterfall(base_direct)
        self.base_direct_cost = base_direct
        self.base_grand_total = base_grand


@frappe.whitelist()
def recalc_totals(estimate):
    """Force recalculate and save Estimate totals from server side."""
    est = frappe.get_doc("Estimate", estimate)
    est.save()
    frappe.db.commit()
    return {
        "direct_cost": est.direct_cost,
        "ocm_amount": est.ocm_amount,
        "profit_amount": est.profit_amount,
        "subtotal": est.subtotal,
        "vat_amount": est.vat_amount,
        "grand_total": est.grand_total,
        "base_direct_cost": est.base_direct_cost,
        "base_grand_total": est.base_grand_total,
    }


@frappe.whitelist()
def debug_totals(estimate):
    """Diagnostic: run the same query as _calculate_totals and return results."""
    scopes = frappe.db.sql("""
        SELECT name, direct_cost, is_optional
        FROM `tabEstimate Scope`
        WHERE estimate = %s
    """, estimate, as_dict=True)

    est = frappe.get_doc("Estimate", estimate)
    total_direct = flt(sum(flt(s.direct_cost) for s in scopes), 2)
    base_direct = flt(sum(flt(s.direct_cost) for s in scopes if not s.is_optional), 2)

    return {
        "scope_count": len(scopes),
        "scopes": [{"name": s.name, "direct_cost": s.direct_cost, "is_optional": s.is_optional} for s in scopes],
        "total_direct": total_direct,
        "base_direct": base_direct,
        "ocm_percent": est.ocm_percent,
        "profit_percent": est.profit_percent,
        "vat_percent": est.vat_percent,
        "vat_inclusive": est.vat_inclusive,
        "current_grand_total": est.grand_total,
    }


@frappe.whitelist()
def get_scope_summary(estimate):
    """Return linked Estimate Scope records for the scope summary table."""
    return frappe.db.sql("""
        SELECT name, scope_name, scope_group, is_optional, direct_cost
        FROM `tabEstimate Scope`
        WHERE estimate = %s
        ORDER BY scope_group ASC, scope_name ASC
    """, estimate, as_dict=True)


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
