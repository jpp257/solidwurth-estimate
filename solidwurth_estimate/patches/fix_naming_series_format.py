import frappe


def execute():
    """Fix naming series format: add missing dot before counter placeholder.

    EST-.YY.-#### (broken: #### treated as literal) → EST-.YY.-.#### (correct: 4-digit counter)
    ESC-.YY.-#### → ESC-.YY.-.####

    Also cleans up any records created with the broken naming series counter.
    """
    for doctype, old_series, new_series in [
        ("Estimate", "EST-.YY.-####", "EST-.YY.-.####"),
        ("Estimate Scope", "ESC-.YY.-####", "ESC-.YY.-.####"),
    ]:
        # Update the DocField options
        frappe.db.sql(
            """UPDATE `tabDocField`
            SET `options` = %s
            WHERE `parent` = %s AND `fieldname` = 'naming_series' AND `options` = %s""",
            (new_series, doctype, old_series),
        )

        # Update any existing documents that have the old naming_series value
        frappe.db.sql(
            """UPDATE `tab{doctype}`
            SET `naming_series` = %s
            WHERE `naming_series` = %s""".format(doctype=doctype),
            (new_series, old_series),
        )

        # Clean up old Series counter entry
        frappe.db.sql(
            """DELETE FROM `tabSeries` WHERE `name` = %s""",
            (old_series,),
        )

    frappe.clear_cache()
