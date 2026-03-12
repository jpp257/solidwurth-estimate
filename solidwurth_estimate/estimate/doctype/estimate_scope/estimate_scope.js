// Copyright (c) 2026, SolidWurth Corp. and contributors
// For license information, please see license.txt

// D14: Single shared debounce timer for ALL field changes
let _calc_timer = null;

function debounced_calculate(frm) {
    clearTimeout(_calc_timer);
    _calc_timer = setTimeout(() => calculate_all_totals(frm), 300);
}

function calculate_all_totals(frm) {
    const doc = frm.doc;
    const quantity = flt(doc.quantity);
    const output_per_day = flt(doc.output_per_day);

    // Duration
    let duration_days = 0;
    if (output_per_day > 0) {
        duration_days = flt(quantity / output_per_day, precision("duration_days", doc));
    }
    frappe.model.set_value(doc.doctype, doc.name, "duration_days", duration_days);

    // D15/AC10: Inline warning when qty > 0 and output_per_day empty
    const warning_wrapper = frm.fields_dict["output_per_day"]?.$wrapper;
    if (quantity > 0 && !output_per_day) {
        if (warning_wrapper && !warning_wrapper.find(".output-warning").length) {
            warning_wrapper.append(
                '<p class="output-warning text-danger small mt-1">' +
                __("Enter Output per Day to calculate duration and costs.") +
                "</p>"
            );
        }
    } else if (warning_wrapper) {
        warning_wrapper.find(".output-warning").remove();
    }

    // Labor rows
    let total_labor_cost = 0;
    (doc.labor_rows || []).forEach((row) => {
        const total_rate = flt(flt(row.persons) * flt(row.daily_rate), precision("total_rate", row));
        const total_cost = flt(total_rate * duration_days, precision("total_cost", row));
        frappe.model.set_value(row.doctype, row.name, "total_rate", total_rate);
        frappe.model.set_value(row.doctype, row.name, "total_cost", total_cost);
        total_labor_cost += total_cost;
    });
    frm.refresh_field("labor_rows");

    // Equipment rows (D1: ownership_type does NOT affect calculation)
    let total_equipment_cost = 0;
    (doc.equipment_rows || []).forEach((row) => {
        const total_rate = flt(flt(row.units) * flt(row.daily_rate), precision("total_rate", row));
        const total_cost = flt(total_rate * duration_days, precision("total_cost", row));
        frappe.model.set_value(row.doctype, row.name, "total_rate", total_rate);
        frappe.model.set_value(row.doctype, row.name, "total_cost", total_cost);
        total_equipment_cost += total_cost;
    });
    frm.refresh_field("equipment_rows");

    // Material rows
    let total_material_cost = 0;
    (doc.material_rows || []).forEach((row) => {
        const wastage_factor = 1 + flt(row.wastage_percent) / 100;
        const adjusted_qty = flt(flt(row.qty) * wastage_factor, precision("adjusted_qty", row));
        const amount = flt(adjusted_qty * flt(row.rate), precision("amount", row));
        const margin = flt(flt(row.rate) - flt(row.buying_rate), precision("margin", row));
        frappe.model.set_value(row.doctype, row.name, "adjusted_qty", adjusted_qty);
        frappe.model.set_value(row.doctype, row.name, "amount", amount);
        frappe.model.set_value(row.doctype, row.name, "margin", margin);
        total_material_cost += amount;
    });
    frm.refresh_field("material_rows");

    // Scope totals
    frappe.model.set_value(doc.doctype, doc.name, "total_labor_cost",
        flt(total_labor_cost, precision("total_labor_cost", doc)));
    frappe.model.set_value(doc.doctype, doc.name, "total_equipment_cost",
        flt(total_equipment_cost, precision("total_equipment_cost", doc)));
    frappe.model.set_value(doc.doctype, doc.name, "total_material_cost",
        flt(total_material_cost, precision("total_material_cost", doc)));
    frappe.model.set_value(doc.doctype, doc.name, "direct_cost",
        flt(total_labor_cost + total_equipment_cost + total_material_cost,
            precision("direct_cost", doc)));
}

// Form events
frappe.ui.form.on("Estimate Scope", {
    refresh(frm) {
        calculate_all_totals(frm);
    },
    quantity(frm) {
        debounced_calculate(frm);
    },
    output_per_day(frm) {
        debounced_calculate(frm);
    },
});

// Labor child table events
frappe.ui.form.on("Estimate Scope Labor", {
    persons(frm) { debounced_calculate(frm); },
    daily_rate(frm) { debounced_calculate(frm); },
    labor_rows_add(frm) { debounced_calculate(frm); },
    labor_rows_remove(frm) { debounced_calculate(frm); },
});

// Equipment child table events
frappe.ui.form.on("Estimate Scope Equipment", {
    units(frm) { debounced_calculate(frm); },
    daily_rate(frm) { debounced_calculate(frm); },
    ownership_type(frm) { debounced_calculate(frm); },
    equipment_rows_add(frm) { debounced_calculate(frm); },
    equipment_rows_remove(frm) { debounced_calculate(frm); },
});

// Material child table events
frappe.ui.form.on("Estimate Scope Material", {
    item(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.item) return;

        frappe.call({
            method: "solidwurth_estimate.estimate.doctype.estimate_scope.estimate_scope.get_buying_rate",
            args: { item_code: row.item },
            callback(r) {
                if (!r.exc && r.message) {
                    frappe.model.set_value(cdt, cdn, "buying_rate", r.message.rate);
                    if (r.message.source === "Not Found") {
                        frappe.show_alert({
                            message: __("No buying rate found for {0}. Enter manually if needed.", [row.item]),
                            indicator: "orange",
                        }, 5);
                    }
                    debounced_calculate(frm);
                }
            },
        });
    },

    supplier_quotation(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.supplier_quotation || !row.item) return;

        frappe.call({
            method: "solidwurth_estimate.estimate.doctype.estimate_scope.estimate_scope.get_sq_rate",
            args: {
                supplier_quotation: row.supplier_quotation,
                item_code: row.item,
            },
            callback(r) {
                if (!r.exc && r.message) {
                    frappe.model.set_value(cdt, cdn, "sq_rate", r.message.rate);
                    if (!r.message.found) {
                        frappe.show_alert({
                            message: __(
                                "Item {0} was not found in Supplier Quotation {1}. SQ Rate set to 0.",
                                [row.item, row.supplier_quotation]
                            ),
                            indicator: "orange",
                        }, 8);
                    }
                }
            },
        });
    },

    qty(frm) { debounced_calculate(frm); },
    wastage_percent(frm) { debounced_calculate(frm); },
    rate(frm) { debounced_calculate(frm); },
    buying_rate(frm) { debounced_calculate(frm); },
    material_rows_add(frm) { debounced_calculate(frm); },
    material_rows_remove(frm) { debounced_calculate(frm); },
});
