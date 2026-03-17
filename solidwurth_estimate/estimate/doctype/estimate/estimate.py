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

    Phase 14 changes:
    - status transitions removed — Frappe Workflow handles state validation
    - status transition method removed — replaced by Frappe Workflow engine
    - _enforce_locked_states() added — blocks field edits on Approved/Converted
    - on_update() added — auto-increments revision on Rejected->Draft transition
    """

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
        Enforce locked-state guard and compute waterfall totals.
        D9/D10/D11: Dual waterfall — all scopes and non-optional scopes.
        Phase 14: status transition check removed — Frappe Workflow handles state validation.
        """
        # Phase 14: status transition check removed — Frappe Workflow handles state validation
        self._enforce_locked_states()   # D11, D12: block edits on Approved/Converted
        self._calculate_totals()
        self._calculate_payment_amounts()

    def _enforce_locked_states(self):
        """Block any field edits when Estimate is Approved or Converted. D11, D12.
        Uses DB comparison to distinguish workflow transitions (allowed) from field edits (blocked).
        Pitfall 3 from RESEARCH.md: only throw if workflow_state has NOT changed (i.e. not a transition).
        """
        if self.is_new():
            return
        locked_states = {"Approved", "Converted"}
        if self.status not in locked_states:
            return
        previous = frappe.db.get_value(
            "Estimate", self.name,
            ["status"],
            as_dict=True
        )
        if previous and previous.status == self.status:
            # status unchanged — someone is editing a field on a locked document
            frappe.throw(
                f"Estimate is {self.status} and cannot be edited. "
                "To make changes, ask the CEO to reject and revise."
            )

    def on_update(self):
        """Detect Rejected -> Draft transition and auto-increment revision. D10.
        Uses db_set (not save) to avoid recursive on_update trigger. Pitfall 4 from RESEARCH.md.
        """
        previous = self.get_doc_before_save()
        if (
            previous
            and getattr(previous, "status", None) == "Rejected"
            and self.status == "Draft"
        ):
            self.db_set("revision", (self.revision or 0) + 1)

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

    def _calculate_payment_amounts(self):
        """
        Compute amount for each payment term row based on scope group grand total x percentage.

        Per scope group (not per individual item).
        amount = scope_group_grand_total x (percentage / 100)

        Scope group grand total = waterfall applied to sum of direct_costs for that group.
        If scope_group is blank/missing in a term row, uses overall estimate grand_total.
        """
        if not self.payment_terms:
            return

        # Build scope group -> direct_cost map
        group_rows = frappe.db.sql("""
            SELECT scope_group, SUM(direct_cost) as group_dc
            FROM `tabEstimate Scope`
            WHERE estimate = %s
            GROUP BY scope_group
        """, self.name, as_dict=True)

        group_dc_map = {r.scope_group: flt(r.group_dc) for r in group_rows}

        def group_grand_total(group_dc):
            """Apply waterfall to a group's direct cost (same formula as _calculate_totals)."""
            ocm = flt(group_dc * flt(self.ocm_percent) / 100, 2)
            profit = flt((group_dc + ocm) * flt(self.profit_percent) / 100, 2)
            sub = flt(group_dc + ocm + profit, 2)
            vat = flt(sub * flt(self.vat_percent) / 100, 2) if self.vat_inclusive else 0.0
            return flt(sub + vat, 2)

        for term in self.payment_terms:
            grp = (term.scope_group or "").strip()
            if grp and grp in group_dc_map:
                base = group_grand_total(group_dc_map[grp])
            else:
                # Blank scope_group or unmatched — use overall grand_total
                base = flt(self.grand_total, 2)

            term.amount = flt(base * flt(term.percentage) / 100, 2)


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


@frappe.whitelist()
def force_delete_estimate(estimate_name):
    """Temporary cleanup method: delete an Estimate regardless of workflow state.
    Uses frappe.db.set_value to bypass _enforce_locked_states validation.
    TODO: Remove after test data cleanup is complete.
    """
    frappe.only_for("System Manager")
    est = frappe.get_doc("Estimate", estimate_name)
    # Clear project link via db.set_value (bypasses validate)
    if est.project:
        frappe.db.set_value("Estimate", estimate_name, "project", "")
    # Reset status to Draft so on_trash can run normally
    frappe.db.set_value("Estimate", estimate_name, "status", "Draft")
    frappe.db.set_value("Estimate", estimate_name, "workflow_state", "Draft")
    frappe.db.commit()
    # Now delete normally (triggers on_trash cascade)
    frappe.delete_doc("Estimate", estimate_name, force=True)
    return "ok"


@frappe.whitelist()
def convert_to_project(estimate_name):
    """
    Atomically convert an Approved Estimate into an ERPNext Project.

    Creates the Project, sets bidirectional link, and transitions Estimate to Converted.
    All within one HTTP request = one DB transaction (auto-rollback on any exception). D18.

    IMPORTANT: Uses frappe.db.set_value (not estimate.save) to update Estimate fields.
    Reason: _enforce_locked_states() in validate() blocks saves on Approved estimates.
    frappe.db.set_value bypasses validate() entirely. D11 / Pitfall 3 from RESEARCH.md.

    IMPORTANT: Sets status = "Converted" via db.set_value directly (not apply_workflow).
    Reason: "Convert to Project" is not a workflow transition (D19 resolution, Pitfall 5).

    Args:
        estimate_name (str): Name of the Estimate to convert (e.g. "EST-26-0001")

    Returns:
        dict: {project_name: str, project_url: str}
    """
    estimate = frappe.get_doc("Estimate", estimate_name)

    # Guard: must be in Approved state
    if estimate.status != "Approved":
        frappe.throw(
            f"Estimate must be in 'Approved' state before conversion. "
            f"Current state: {estimate.status}."
        )

    # Guard: no double-conversion (D14)
    if estimate.project:
        frappe.throw(
            f"Estimate {estimate_name} is already linked to Project {estimate.project}. "
            "A new Estimate is required for a new Project."
        )

    # Create Project (D3: minimal data transfer)
    project = frappe.new_doc("Project")
    project.project_name = estimate.estimate_title
    project.estimated_costing = estimate.grand_total
    project.company = "SolidWurth Corp."
    project.custom_estimate = estimate_name
    if estimate.client:
        project.customer = estimate.client
    project.insert(ignore_permissions=False)

    # Set bidirectional link: Estimate.project -> new Project (D5)
    # Use db.set_value to bypass validate() which throws on locked Approved state
    frappe.db.set_value("Estimate", estimate_name, "project", project.name)

    # Transition Estimate to Converted state (D8, D11)
    # Direct db.set_value on status — "Convert to Project" is not a workflow transition
    frappe.db.set_value("Estimate", estimate_name, "status", "Converted")

    return {
        "project_name": project.name,
        "project_url": f"/app/project/{project.name}"
    }
