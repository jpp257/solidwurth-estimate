# Copyright (c) 2026, SolidWurth Corp. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class EstimateScope(Document):
    def validate(self):
        self._compute_duration()
        self._compute_labor_rows()
        self._compute_equipment_rows()
        self._compute_material_rows()
        self._compute_scope_totals()

    def on_update(self):
        """Recalculate parent Estimate waterfall totals when a scope is saved."""
        self._update_parent_totals()

    def after_delete(self):
        """Recalculate parent Estimate waterfall totals after a scope is deleted."""
        self._update_parent_totals()

    def _update_parent_totals(self):
        """Load parent Estimate, recompute waterfall, write directly to DB."""
        if not self.estimate:
            return
        try:
            est = frappe.get_doc("Estimate", self.estimate)
        except frappe.DoesNotExistError:
            return  # Parent being cascade-deleted

        est._calculate_totals()
        frappe.db.set_value("Estimate", self.estimate, {
            "direct_cost": est.direct_cost,
            "ocm_amount": est.ocm_amount,
            "profit_amount": est.profit_amount,
            "subtotal": est.subtotal,
            "vat_amount": est.vat_amount,
            "grand_total": est.grand_total,
            "base_direct_cost": est.base_direct_cost,
            "base_grand_total": est.base_grand_total,
        }, update_modified=False)

    def _compute_duration(self):
        quantity = flt(self.quantity)
        output_per_day = flt(self.output_per_day)

        if quantity > 0 and output_per_day == 0:
            frappe.throw(
                _("Cannot calculate duration: Output per Day must be greater than 0 when Quantity is set."),
                title=_("Division by Zero")
            )

        if output_per_day > 0:
            self.duration_days = flt(quantity / output_per_day, 2)
        else:
            self.duration_days = 0.0

    def _compute_labor_rows(self):
        duration = flt(self.duration_days)
        for row in self.labor_rows:
            row.total_rate = flt(flt(row.persons) * flt(row.daily_rate), 2)
            row.total_cost = flt(row.total_rate * duration, 2)

    def _compute_equipment_rows(self):
        duration = flt(self.duration_days)
        for row in self.equipment_rows:
            row.total_rate = flt(flt(row.units) * flt(row.daily_rate), 2)
            row.total_cost = flt(row.total_rate * duration, 2)

    def _compute_material_rows(self):
        for row in self.material_rows:
            wastage_factor = 1 + flt(row.wastage_percent) / 100
            row.adjusted_qty = flt(flt(row.qty) * wastage_factor, 2)
            row.amount = flt(row.adjusted_qty * flt(row.rate), 2)
            row.margin = flt(flt(row.rate) - flt(row.buying_rate), 2)

    def _compute_scope_totals(self):
        self.total_labor_cost = flt(sum(flt(r.total_cost) for r in self.labor_rows), 2)
        self.total_equipment_cost = flt(sum(flt(r.total_cost) for r in self.equipment_rows), 2)
        self.total_material_cost = flt(sum(flt(r.amount) for r in self.material_rows), 2)
        self.direct_cost = flt(
            self.total_labor_cost + self.total_equipment_cost + self.total_material_cost, 2
        )


@frappe.whitelist()
def get_buying_rate(item_code):
    """Waterfall: Last PO rate -> Buying Price List -> 0"""
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"item_code": item_code, "docstatus": 1},
        fields=["rate"],
        order_by="creation desc",
        limit=1,
    )
    if po_items:
        return {"rate": flt(po_items[0].rate, 2), "source": "Last PO"}

    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": "Standard Buying", "selling": 0},
        "price_list_rate",
    )
    if price:
        return {"rate": flt(price, 2), "source": "Buying Price List"}

    return {"rate": 0, "source": "Not Found"}


@frappe.whitelist()
def get_sq_rate(supplier_quotation, item_code):
    """Fetch quoted rate for item from a Supplier Quotation"""
    sq_items = frappe.get_all(
        "Supplier Quotation Item",
        filters={"parent": supplier_quotation, "item_code": item_code},
        fields=["rate"],
    )
    if sq_items:
        return {"rate": flt(sq_items[0].rate, 2), "found": True}
    return {"rate": 0, "found": False}
