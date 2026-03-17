// Copyright (c) 2026, SolidWurth Corp. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Estimate", {
    /**
     * Called on every form load and refresh.
     * Adds "Add Scope from Template" button only on Draft estimates.
     * D8, D28 from CONTEXT.md.
     */
    refresh(frm) {
        // Only show picker button on Draft estimates (not submitted/cancelled)
        // Uses workflow_state (not status) — workflow_state_field = "status" so they are the same field,
        // but workflow_state is the canonical check per 14-01 critical context.
        if (frm.doc.docstatus === 0 && frm.doc.workflow_state === "Draft") {
            frm.add_custom_button(
                __("Add Scope from Template"),
                () => show_template_picker(frm)
            );
        }

        // Convert to Project button — D15: visible only when Approved AND no linked Project
        if (frm.doc.workflow_state === "Approved" && !frm.doc.project) {
            frm.add_custom_button(
                __("Convert to Project"),
                () => show_conversion_dialog(frm)
            );
        }

        render_scope_summary(frm);

        // D30: Compute BP totals on form load so fields are populated
        calculate_bp_totals(frm);
    },

    /**
     * BP field change handlers — trigger live bp_grand_total recalculation.
     * Plan 13-03: D30 — browser-side approximation of BP total.
     * Exact per-scope calculation runs at print time in Jinja (cost_proposal_bp.html).
     */
    bp_rate_factor(frm) { calculate_bp_totals(frm); },
    bp_ocm_percent(frm) { calculate_bp_totals(frm); },
    bp_profit_percent(frm) { calculate_bp_totals(frm); },

    /**
     * NOTE: Payment Terms amounts are server-computed (read_only field).
     * Amounts are calculated in estimate.py _calculate_payment_amounts() on each Estimate save.
     * The amount column is read_only — no client-side calculation is needed or correct here.
     * Server-only is the right pattern because scope group totals come from a DB query
     * (tabEstimate Scope), not from child table rows accessible in browser memory.
     * Do NOT add field_change handlers for the payment_terms.amount column.
     */

    /**
     * Auto-populate terms from selected template.
     * User can still edit the terms field after — it's per-estimate.
     */
    terms_template(frm) {
        if (frm.doc.terms_template) {
            frappe.db.get_value(
                "Estimate Terms Template",
                frm.doc.terms_template,
                "terms",
                (r) => {
                    if (r && r.terms) {
                        frm.set_value("terms", r.terms);
                    }
                }
            );
        }
    },
});


/**
 * Show multi-select template picker dialog.
 * User sets a scope_group, searches and checks templates, then clicks Add.
 * All selected templates are created as Estimate Scopes in one batch call.
 *
 * D28 from CONTEXT.md:
 *   Scope Group: [Guard House       ]
 *   Search: [concrete...            ]
 *   ☑ Concrete Pouring - Footing
 *   ☑ Rebar Installation - Footing
 *   ☐ Formworks - Footing
 *   [Cancel]           [Add 2 Scopes]
 */
function show_template_picker(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Add Scopes from Templates"),
        fields: [
            {
                fieldname: "scope_group",
                fieldtype: "Data",
                label: __("Scope Group"),
                reqd: 1,
                placeholder: __("e.g. Guard House, Main Building"),
                description: __("All selected templates will be added under this group."),
            },
            {
                fieldname: "sb_templates",
                fieldtype: "Section Break",
                label: __("Select Templates"),
            },
            {
                fieldname: "template_names",
                fieldtype: "MultiSelectList",
                label: __("Scope Templates"),
                reqd: 1,
                /**
                 * get_data is called on every keystroke in the search box.
                 * Returns a Promise resolving to [{value, label, description}]
                 */
                get_data(txt) {
                    const filters = [];
                    if (txt) {
                        filters.push(["template_name", "like", "%" + txt + "%"]);
                    }
                    return frappe.db
                        .get_list("Scope Template", {
                            filters: filters,
                            fields: ["name", "template_name", "description", "dpwh_pay_item"],
                            limit: 50,
                            order_by: "template_name asc",
                        })
                        .then(function (results) {
                            return results.map(function (r) {
                                return {
                                    value: r.name,
                                    label: r.template_name,
                                    description: r.dpwh_pay_item
                                        ? r.dpwh_pay_item + (r.description ? " — " + r.description : "")
                                        : r.description || "",
                                };
                            });
                        });
                },
            },
        ],
        primary_action_label: __("Add Scopes"),
        primary_action(values) {
            if (!values.template_names || values.template_names.length === 0) {
                frappe.msgprint(__("Please select at least one template."));
                return;
            }

            dialog.hide();

            frappe.call({
                method: "solidwurth_estimate.estimate.doctype.estimate.estimate.create_scopes_from_templates",
                args: {
                    estimate: frm.doc.name,
                    // JS arrays must be JSON-stringified for frappe.call list args
                    template_names: JSON.stringify(values.template_names),
                    scope_group: values.scope_group,
                },
                freeze: true,
                freeze_message: __("Creating scopes..."),
                callback(r) {
                    if (!r.exc) {
                        const count = r.message ? r.message.length : 0;
                        frappe.show_alert({
                            message: __(
                                "{0} scope(s) added under '{1}'.",
                                [count, values.scope_group]
                            ),
                            indicator: "green",
                        });
                        frm.reload_doc(function() {
                            render_scope_summary(frm);
                        });
                    }
                },
            });
        },
    });

    dialog.show();
}


/**
 * Show confirmation dialog before converting Estimate to Project. D16.
 * Displays: Estimate name, proposed project name, estimated costing.
 * On confirm: calls convert_to_project() whitelist method. D17, D18.
 */
function show_conversion_dialog(frm) {
    const costing = format_currency(frm.doc.grand_total, "PHP");
    frappe.confirm(
        `Create Project from <strong>${frm.doc.name}</strong>?<br><br>
         Project name: <strong>${frappe.utils.escape_html(frm.doc.estimate_title)}</strong><br>
         Estimated costing: <strong>${costing}</strong>`,
        () => {
            frappe.call({
                method: "solidwurth_estimate.estimate.doctype.estimate.estimate.convert_to_project",
                args: { estimate_name: frm.doc.name },
                freeze: true,
                freeze_message: __("Creating project..."),
                callback(r) {
                    if (!r.exc && r.message) {
                        const link = `<a href="${r.message.project_url}">${frappe.utils.escape_html(r.message.project_name)}</a>`;
                        frappe.msgprint({
                            title: __("Project Created"),
                            message: __("Project {0} created successfully.", [link]),
                            indicator: "green"
                        });
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}


/**
 * Compute approximate BP totals in the browser for live field feedback.
 *
 * Plan 13-03: D30 — browser-side approximation.
 * The exact per-scope BP calculation runs at print time in cost_proposal_bp.html
 * (Jinja queries each scope's material rows and applies bp_rate_factor).
 *
 * Browser approximation: grand_total * bp_rate * extra_ocm_factor * extra_profit_factor
 * This is an estimate — exact value appears when printing the BP format.
 *
 * Sets:
 *   bp_effective_multiplier — ratio of BP total to standard grand_total (4 dp)
 *   bp_grand_total          — approximate BP contract amount
 */
function calculate_bp_totals(frm) {
    const bp_rate = flt(frm.doc.bp_rate_factor) || 1.0;
    const bp_ocm = flt(frm.doc.bp_ocm_percent);
    const bp_profit = flt(frm.doc.bp_profit_percent);
    const std_ocm = flt(frm.doc.ocm_percent);
    const std_profit = flt(frm.doc.profit_percent);
    const grand_total = flt(frm.doc.grand_total);

    if (!grand_total) {
        // No grand total yet — nothing to compute
        return;
    }

    // Approximate: scale grand_total by bp_rate on material component, then
    // re-apply the delta between BP and standard OCM/profit percentages.
    // This gives a quick browser estimate without fetching per-scope material rows.
    const ocm_extra_factor = 1 + (bp_ocm - std_ocm) / 100;
    const profit_extra_factor = 1 + (bp_profit - std_profit) / 100;
    const multiplier = flt(bp_rate * ocm_extra_factor * profit_extra_factor, 4);

    const bp_gt = flt(grand_total * multiplier, 2);

    frappe.model.set_value(frm.doc.doctype, frm.doc.name, "bp_effective_multiplier", multiplier);
    frappe.model.set_value(frm.doc.doctype, frm.doc.name, "bp_grand_total", bp_gt);
}


/**
 * Render a summary table of all Estimate Scopes linked to this Estimate.
 * Displays scope name (linked), group, optional flag, and direct cost.
 * Shows Base Total and Optional Total in the table footer.
 *
 * Phase 12-02: D9, D10, D11 — complements the dual waterfall totals.
 */
function render_scope_summary(frm) {
    if (!frm.doc.name || frm.doc.__islocal) {
        frm.fields_dict.scope_summary_html.$wrapper.html(
            '<p class="text-muted" style="padding:8px;">' + __("No scopes added") + '</p>'
        );
        return;
    }

    frappe.call({
        method: "solidwurth_estimate.estimate.doctype.estimate.estimate.get_scope_summary",
        args: { estimate: frm.doc.name },
        callback(r) {
            const scopes = r.message || [];
            const wrapper = frm.fields_dict.scope_summary_html.$wrapper;

            if (!scopes.length) {
                wrapper.html(
                    '<p class="text-muted" style="padding:8px;">' + __("No scopes added") + '</p>'
                );
                return;
            }

            // Group scopes by scope_group
            let baseTotal = 0;
            let optionalTotal = 0;
            const groups = {};
            scopes.forEach(s => {
                const dc = flt(s.direct_cost);
                if (s.is_optional) { optionalTotal += dc; } else { baseTotal += dc; }
                const g = s.scope_group || "";
                if (!groups[g]) groups[g] = [];
                groups[g].push(s);
            });

            // Build grouped rows
            let rows = "";
            Object.keys(groups).sort().forEach(groupName => {
                // Group header row
                const label = groupName || __("Ungrouped");
                rows += `<tr class="scope-group-header" style="background:var(--bg-light-gray, var(--subtle-fg, #f7f7f7));">
                    <td colspan="3" style="font-weight:600;padding:6px 8px;">
                        <span style="color:var(--text-muted);margin-right:4px;">&#9656;</span>${frappe.utils.escape_html(label)}
                    </td>
                </tr>`;
                // Scope rows under this group
                groups[groupName].forEach(s => {
                    const link = `/app/estimate-scope/${encodeURIComponent(s.name)}`;
                    const optFlag = s.is_optional ? "&#10003;" : "";
                    const dc = format_currency(flt(s.direct_cost), "PHP");
                    rows += `<tr>
                        <td style="padding-left:24px;"><a href="${link}">${frappe.utils.escape_html(s.scope_name || s.name)}</a></td>
                        <td style="text-align:center;">${optFlag}</td>
                        <td style="text-align:right;">${dc}</td>
                    </tr>`;
                });
            });

            const html = `
<table class="table table-bordered table-condensed" style="margin:0;font-size:13px;">
  <thead>
    <tr>
      <th>${__("Scope Name")}</th>
      <th style="text-align:center;width:50px;">${__("Opt")}</th>
      <th style="text-align:right;width:150px;">${__("Direct Cost")}</th>
    </tr>
  </thead>
  <tbody>${rows}</tbody>
  <tfoot>
    <tr style="font-weight:bold;">
      <td colspan="2">${__("Base Total")}</td>
      <td style="text-align:right;">${format_currency(baseTotal, "PHP")}</td>
    </tr>
    <tr style="font-weight:bold;">
      <td colspan="2">${__("Optional Total")}</td>
      <td style="text-align:right;">${format_currency(optionalTotal, "PHP")}</td>
    </tr>
  </tfoot>
</table>`;

            wrapper.html(html);
        },
    });
}
