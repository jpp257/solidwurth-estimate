import frappe


def execute():
    """Switch from naming_series: to direct autoname format.

    bench migrate doesn't reliably sync naming_series field options on Frappe Cloud.
    Direct autoname format bypasses the naming_series field entirely.
    """
    for doctype, autoname_format in [
        ("Estimate", "EST-.YY.-.####"),
        ("Estimate Scope", "ESC-.YY.-.####"),
    ]:
        # Set autoname directly on the DocType record
        frappe.db.sql(
            """UPDATE `tabDocType`
            SET `autoname` = %s
            WHERE `name` = %s""",
            (autoname_format, doctype),
        )

        # Clean up all stale Series counter entries from old format
        frappe.db.sql(
            """DELETE FROM `tabSeries` WHERE `name` LIKE %s""",
            (autoname_format.replace(".####", "") + "%",),
        )

    frappe.clear_cache()
