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
        if (frm.doc.docstatus === 0 && frm.doc.status === "Draft") {
            frm.add_custom_button(
                __("Add Scope from Template"),
                () => show_template_picker(frm)
            );
        }

        render_scope_summary(frm);
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
                        frm.reload_doc();
                        frm.once("after_load", () => render_scope_summary(frm));
                        frappe.show_alert({
                            message: __(
                                "{0} scope(s) added under '{1}'.",
                                [count, values.scope_group]
                            ),
                            indicator: "green",
                        });
                    }
                },
            });
        },
    });

    dialog.show();
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

            let baseTotal = 0;
            let optionalTotal = 0;
            scopes.forEach(s => {
                const dc = flt(s.direct_cost);
                if (s.is_optional) {
                    optionalTotal += dc;
                } else {
                    baseTotal += dc;
                }
            });

            const rows = scopes.map(s => {
                const link = frappe.utils.get_url_to_form("Estimate Scope", s.name);
                const optFlag = s.is_optional ? "&#10003;" : "";
                const dc = format_currency(flt(s.direct_cost), "PHP");
                return `<tr>
                    <td><a href="${link}">${frappe.utils.escape_html(s.scope_name || s.name)}</a></td>
                    <td>${frappe.utils.escape_html(s.scope_group || "")}</td>
                    <td style="text-align:center;">${optFlag}</td>
                    <td style="text-align:right;">${dc}</td>
                </tr>`;
            }).join("");

            const html = `
<table class="table table-bordered table-condensed" style="margin:0;font-size:13px;">
  <thead>
    <tr>
      <th>${__("Scope Name")}</th>
      <th>${__("Group")}</th>
      <th style="text-align:center;">${__("Opt")}</th>
      <th style="text-align:right;">${__("Direct Cost")}</th>
    </tr>
  </thead>
  <tbody>${rows}</tbody>
  <tfoot>
    <tr style="font-weight:bold;">
      <td colspan="3">${__("Base Total")}</td>
      <td style="text-align:right;">${format_currency(baseTotal, "PHP")}</td>
    </tr>
    <tr style="font-weight:bold;">
      <td colspan="3">${__("Optional Total")}</td>
      <td style="text-align:right;">${format_currency(optionalTotal, "PHP")}</td>
    </tr>
  </tfoot>
</table>`;

            wrapper.html(html);
        },
    });
}
