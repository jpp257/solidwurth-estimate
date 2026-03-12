import frappe


def execute():
    """Fix naming series: switch from naming_series: to direct autoname format.

    Previous approach used autoname="naming_series:" which reads the format from
    the naming_series field. But bench migrate doesn't reliably sync field options
    for naming_series Select fields on Frappe Cloud.

    New approach: autoname="EST-.YY.-.####" directly on DocType. The naming_series
    field is kept (hidden) but no longer drives naming.

    Also fixes the old #### format and cleans up stale Series counters.
    """
    for doctype, old_series, new_series in [
        ("Estimate", "EST-.YY.-####", "EST-.YY.-.####"),
        ("Estimate Scope", "ESC-.YY.-####", "ESC-.YY.-.####"),
    ]:
        # Update autoname on the DocType record itself
        frappe.db.sql(
            """UPDATE `tabDocType`
            SET `autoname` = %s
            WHERE `name` = %s""",
            (new_series, doctype),
        )

        # Update the DocField options (for display consistency)
        frappe.db.sql(
            """UPDATE `tabDocField`
            SET `options` = %s
            WHERE `parent` = %s AND `fieldname` = 'naming_series' AND `options` = %s""",
            (new_series, doctype, old_series),
        )

        # Also handle case where autoname was still "naming_series:"
        frappe.db.sql(
            """UPDATE `tabDocType`
            SET `autoname` = %s
            WHERE `name` = %s AND `autoname` = 'naming_series:'""",
            (new_series, doctype),
        )

        # Update any existing documents that have the old naming_series value
        frappe.db.sql(
            """UPDATE `tab{doctype}`
            SET `naming_series` = %s
            WHERE `naming_series` = %s""".format(doctype=doctype),
            (new_series, old_series),
        )

        # Clean up old Series counter entries
        for series in [old_series, "EST-.YY.-####", "ESC-.YY.-####"]:
            frappe.db.sql(
                """DELETE FROM `tabSeries` WHERE `name` = %s""",
                (series,),
            )

    frappe.clear_cache()
