"""
Shared Jinja macro functions for SolidWurth Estimate print formats.

Called as methods.* in Jinja2 templates via Frappe's jinja.methods hook.
Both 'Cost Proposal' and 'Cost Proposal (BP)' print formats use these functions.

Registered in hooks.py:
    jinja = {"methods": "solidwurth_estimate.utils.jinja_methods"}
"""

import os
import base64
import math


# ---------------------------------------------------------------------------
# Amount in Words (Philippine peso format)
# ---------------------------------------------------------------------------

def amount_in_words(amount):
    """Convert numeric amount to words in Philippine peso format.

    E.g. 642390.00 → "Six Hundred Forty-Two Thousand Three Hundred Ninety Pesos and 00/100"

    Args:
        amount: Numeric value
    Returns:
        str: Amount spelled out in words
    """
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        return ""

    if value < 0:
        return "Negative " + amount_in_words(-value)

    pesos = int(math.floor(value))
    centavos = int(round((value - pesos) * 100))

    if pesos == 0:
        words = "Zero"
    else:
        words = _int_to_words(pesos)

    return "{} Pesos and {:02d}/100".format(words, centavos)


def _int_to_words(n):
    """Convert a non-negative integer to English words (up to trillions)."""
    if n == 0:
        return "Zero"

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]
    scales = [(1_000_000_000_000, "Trillion"), (1_000_000_000, "Billion"),
              (1_000_000, "Million"), (1_000, "Thousand"), (100, "Hundred")]

    parts = []
    for scale_val, scale_name in scales:
        if n >= scale_val:
            chunk = n // scale_val
            n %= scale_val
            parts.append("{} {}".format(_int_to_words(chunk), scale_name))

    if n >= 20:
        part = tens[n // 10]
        if n % 10:
            part += "-" + ones[n % 10]
        parts.append(part)
    elif n > 0:
        parts.append(ones[n])

    return " ".join(parts)


# ---------------------------------------------------------------------------
# WBS Numbering (Scope Group → Scope → Item)
# ---------------------------------------------------------------------------

def _to_roman(n):
    """Convert integer to Roman numeral string (1-50 range)."""
    vals = [(50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    result = ""
    for value, numeral in vals:
        while n >= value:
            result += numeral
            n -= value
    return result


def build_scope_wbs(base_scopes, optional_scopes):
    """Build hierarchical WBS numbering for scopes.

    Groups get Roman numerals (I, II, III...) to avoid conflict with
    DLIA section letters (A-Labor, B-Equipment, C-Materials).
    Scopes: I.1, II.2... Materials: I.1.1, I.1.2... via wbs_prefix.

    Args:
        base_scopes: List of base scope dicts (from DB query, ordered by group)
        optional_scopes: List of optional scope dicts (continue numbering after base)

    Returns:
        dict: Mapping scope name -> {"group_numeral": "I", "scope_num": "I.1"}
              Also includes "_group_numerals" key: scope_group name -> Roman numeral
    """
    result = {}
    group_numerals = {}  # scope_group name -> Roman numeral
    group_scope_counts = {}  # scope_group name -> running count
    numeral_index = 0

    for scope in list(base_scopes or []) + list(optional_scopes or []):
        grp = scope.get("scope_group", "Uncategorized")
        if grp not in group_numerals:
            numeral_index += 1
            group_numerals[grp] = _to_roman(numeral_index)
            group_scope_counts[grp] = 0

        group_scope_counts[grp] += 1
        numeral = group_numerals[grp]
        scope_idx = group_scope_counts[grp]

        result[scope.get("name", "")] = {
            "group_numeral": numeral,
            "scope_num": "{}.{}".format(numeral, scope_idx),
        }

    result["_group_numerals"] = group_numerals
    return result


# ---------------------------------------------------------------------------
# Currency & Number Formatting (D41, D42)
# ---------------------------------------------------------------------------

def php_format(amount):
    """Format a number as 'PHP 1,234,567.89' (D41: ISO code, comma thousands, dot decimal).

    Args:
        amount: Numeric value or None/empty
    Returns:
        str: Formatted currency string e.g. 'PHP 1,234,567.89'
    """
    if amount is None or amount == "" or amount == 0:
        # Handle falsy values — check for actual zero separately
        try:
            if float(amount or 0) == 0:
                return "PHP 0.00"
        except (TypeError, ValueError):
            return "PHP 0.00"
    try:
        value = float(amount)
        # Format with comma thousands separator, 2 decimal places
        formatted = "{:,.2f}".format(value)
        return "PHP {}".format(formatted)
    except (TypeError, ValueError):
        return "PHP 0.00"


def num_format(value):
    """Format a number to fixed 2 decimal places (D42).

    Args:
        value: Numeric value or None
    Returns:
        str: Fixed 2 dp string e.g. '150.00'
    """
    if value is None or value == "":
        return "0.00"
    try:
        return "{:.2f}".format(float(value))
    except (TypeError, ValueError):
        return "0.00"


def int_format(value):
    """Format a number as integer (no decimals) for counts like persons, units.

    Args:
        value: Numeric value or None
    Returns:
        str: Integer string e.g. '5', or '2.5' if not whole
    """
    if value is None or value == "":
        return "0"
    try:
        f = float(value)
        if f == int(f):
            return str(int(f))
        return "{:.1f}".format(f)
    except (TypeError, ValueError):
        return "0"


# ---------------------------------------------------------------------------
# Font Embedding (D40, AC-7)
# ---------------------------------------------------------------------------

def get_fonts():
    """Read base64-encoded .woff2 font files from the app's public/fonts/ directory.

    Returns dict with keys: montserrat_bold, inter_regular, roboto_mono.
    If a font file is missing, returns empty string for that key (graceful degradation —
    CSS font-family falls back to system font; print still works, just with wrong typeface).

    Font files expected at:
        {APP_DIR}/public/fonts/Montserrat-Bold.woff2
        {APP_DIR}/public/fonts/Inter-Regular.woff2
        {APP_DIR}/public/fonts/RobotoMono-Regular.woff2
    """
    # Navigate from this file (utils/jinja_methods.py) up to the app package root
    # jinja_methods.py -> utils/ -> solidwurth_estimate/ -> apps/solidwurth_estimate/ (app root)
    app_package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(app_package_dir, "public", "fonts")

    font_map = {
        "montserrat_bold": "Montserrat-Bold.woff2",
        "inter_regular": "Inter-Regular.woff2",
        "roboto_mono": "RobotoMono-Regular.woff2",
    }

    result = {}
    for key, filename in font_map.items():
        path = os.path.join(fonts_dir, filename)
        try:
            with open(path, "rb") as f:
                data = f.read()
            result[key] = base64.b64encode(data).decode("ascii")
        except (IOError, OSError):
            # Font file missing — graceful degradation, CSS fallback to system font
            result[key] = ""

    return result


# ---------------------------------------------------------------------------
# Waterfall Block (D15, D21, D35)
# ---------------------------------------------------------------------------

def render_waterfall_block(direct_cost, ocm_percent, profit_percent, vat_inclusive, vat_percent, accent_color):
    """Render G->K waterfall table HTML for a scope's cost breakdown.

    Mirrors estimate.py._calculate_totals() waterfall formula exactly.

    Args:
        direct_cost: Scope direct cost (G row)
        ocm_percent: OCM percentage (for H row)
        profit_percent: Profit percentage (for I row)
        vat_inclusive: Boolean — apply VAT if True
        vat_percent: VAT percentage (for J row)
        accent_color: CSS color string for total row background (e.g. '#A52422')

    Returns:
        str: Complete HTML table string
    """
    # Handle None/empty inputs
    dc = float(direct_cost or 0)
    ocm_pct = float(ocm_percent or 0)
    profit_pct = float(profit_percent or 0)
    vat_pct = float(vat_percent or 0)

    # Waterfall formula (matches estimate.py._calculate_totals)
    ocm = dc * ocm_pct / 100
    profit = (dc + ocm) * profit_pct / 100
    subtotal = dc + ocm + profit
    vat = subtotal * vat_pct / 100 if vat_inclusive else 0
    total = subtotal + vat

    rows_html = ""

    def _row(label, letter, amount, pct_str="", style=""):
        """Render a 3-column waterfall row: Component | % | Amount.

        The style param is applied to <tr> — child <td> elements inherit color/font-weight
        so the total row (white text on accent bg) renders correctly without per-cell overrides.
        """
        return (
            '<tr style="{style}">'
            '<td style="padding: 5px 8px; font-size: 9pt;">{letter}&nbsp;&nbsp;{label}</td>'
            '<td style="text-align: center; padding: 5px 8px; font-size: 9pt;">{pct}</td>'
            '<td style="font-family: \'Roboto Mono\', \'Courier New\', monospace; text-align: right; padding: 5px 8px; font-size: 9pt;">{amount}</td>'
            "</tr>"
        ).format(label=label, letter=letter, amount=php_format(amount), pct=pct_str, style=style)

    rows_html += _row("Direct Cost", "G", dc)
    rows_html += _row("Overhead, Contingencies &amp; Misc.", "H", ocm, pct_str="{:.2f}%".format(ocm_pct))
    rows_html += _row("Profit", "I", profit, pct_str="{:.2f}%".format(profit_pct))
    if vat_inclusive:
        rows_html += _row("VAT", "J", vat, pct_str="{:.2f}%".format(vat_pct))
    else:
        rows_html += _row("VAT (exempt)", "J", 0)

    # Total row — accent color background, white text, bold
    total_style = "background-color: {color}; color: #ffffff; font-weight: bold;".format(color=accent_color)
    rows_html += _row("TOTAL", "K", total, style=total_style)

    return (
        '<table class="waterfall-table" style="width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 9pt; font-family: Inter, \'Helvetica Neue\', Arial, sans-serif;">'
        "<thead>"
        '<tr style="background-color: #3B5998; color: #ffffff;">'
        '<th style="text-align: left; padding: 6px 8px; font-family: Inter, \'Helvetica Neue\', Arial, sans-serif; font-weight: bold;">Cost Component</th>'
        '<th style="text-align: center; padding: 6px 8px; font-family: Inter, \'Helvetica Neue\', Arial, sans-serif; font-weight: bold;">%</th>'
        '<th style="text-align: right; padding: 6px 8px; font-family: Inter, \'Helvetica Neue\', Arial, sans-serif; font-weight: bold;">Amount</th>'
        "</tr>"
        "</thead>"
        "<tbody>"
        "{rows}"
        "</tbody>"
        "</table>"
    ).format(rows=rows_html)


# ---------------------------------------------------------------------------
# Section A: Labor Table (D17, D23)
# ---------------------------------------------------------------------------

def render_labor_table(labor_rows, duration_days):
    """Render Section A (Labor Gang) HTML table.

    Args:
        labor_rows: List of dicts with keys: role, persons, daily_rate, total_rate, total_cost
        duration_days: Scope duration in days (shown as table caption)

    Returns:
        str: Complete HTML section with <div class="dlia-section section-a"> wrapper
    """
    header_style = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: left;"'
    header_right = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: right;"'

    header_row = (
        "<tr>"
        "<th {h}>Role</th>"
        "<th {h}>Persons</th>"
        "<th {hr}>Daily Rate</th>"
        "<th {hr}>Total Daily Rate</th>"
        "<th {hr}>Total Cost</th>"
        "</tr>"
    ).format(h=header_style, hr=header_right)

    rows_html = ""
    labor_total = 0
    for i, row in enumerate(labor_rows or []):
        bg = "#F4F6F9" if i % 2 == 0 else "#ffffff"
        row_style = 'style="background-color: {bg};"'.format(bg=bg)
        td = 'style="padding: 5px 8px;"'
        td_right = 'style="padding: 5px 8px; text-align: right; font-family: \'Roboto Mono\', monospace;"'
        labor_total += float(row.get("total_cost", 0) or 0)
        rows_html += (
            "<tr {row}>"
            "<td {td}>{role}</td>"
            "<td {td}>{persons}</td>"
            "<td {tdr}>{daily_rate}</td>"
            "<td {tdr}>{total_rate}</td>"
            "<td {tdr}>{total_cost}</td>"
            "</tr>"
        ).format(
            row=row_style,
            td=td,
            tdr=td_right,
            role=row.get("role", ""),
            persons=int_format(row.get("persons", 0)),
            daily_rate=php_format(row.get("daily_rate", 0)),
            total_rate=php_format(row.get("total_rate", 0)),
            total_cost=php_format(row.get("total_cost", 0)),
        )

    # Subtotal row
    rows_html += (
        '<tr style="border-top: 2px solid #2E5FA3; background-color: #dde4f0;">'
        '<td colspan="4" style="padding: 5px 8px; font-weight: bold; text-align: right;">Labor Subtotal</td>'
        '<td style="padding: 5px 8px; text-align: right; font-family: \'Roboto Mono\', monospace; font-weight: bold;">{total}</td>'
        '</tr>'
    ).format(total=php_format(labor_total))

    table_html = (
        '<table class="dlia-table" style="width: 100%; border-collapse: collapse; font-size: 0.9em;">'
        "<thead>{header}</thead>"
        "<tbody>{rows}</tbody>"
        "</table>"
    ).format(
        header=header_row,
        rows=rows_html,
    )

    return '<div class="dlia-section section-a">{}</div>'.format(table_html)


# ---------------------------------------------------------------------------
# Section B: Equipment Table (D18, D23)
# ---------------------------------------------------------------------------

def render_equipment_table(equipment_rows, duration_days):
    """Render Section B (Equipment) HTML table.

    NOTE: ownership_type column is intentionally hidden from print (D18).

    Args:
        equipment_rows: List of dicts with keys: item_code, item_name, units, daily_rate, total_rate, total_cost
        duration_days: Scope duration in days

    Returns:
        str: Complete HTML section with <div class="dlia-section section-b"> wrapper
    """
    header_style = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: left;"'
    header_right = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: right;"'

    header_row = (
        "<tr>"
        "<th {h}>Item</th>"
        "<th {h}>Equipment Name</th>"
        "<th {h}>Units</th>"
        "<th {hr}>Daily Rate</th>"
        "<th {hr}>Total Daily Rate</th>"
        "<th {hr}>Total Cost</th>"
        "</tr>"
    ).format(h=header_style, hr=header_right)

    rows_html = ""
    equip_total = 0
    for i, row in enumerate(equipment_rows or []):
        bg = "#F4F6F9" if i % 2 == 0 else "#ffffff"
        row_style = 'style="background-color: {bg};"'.format(bg=bg)
        td = 'style="padding: 5px 8px;"'
        td_right = 'style="padding: 5px 8px; text-align: right; font-family: \'Roboto Mono\', monospace;"'
        equip_total += float(row.get("total_cost", 0) or 0)
        rows_html += (
            "<tr {row}>"
            "<td {td}>{item_code}</td>"
            "<td {td}>{item_name}</td>"
            "<td {td}>{units}</td>"
            "<td {tdr}>{daily_rate}</td>"
            "<td {tdr}>{total_rate}</td>"
            "<td {tdr}>{total_cost}</td>"
            "</tr>"
        ).format(
            row=row_style,
            td=td,
            tdr=td_right,
            item_code=row.get("item_code", ""),
            item_name=row.get("item_name", ""),
            units=int_format(row.get("units", 0)),
            daily_rate=php_format(row.get("daily_rate", 0)),
            total_rate=php_format(row.get("total_rate", 0)),
            total_cost=php_format(row.get("total_cost", 0)),
        )

    # Subtotal row
    rows_html += (
        '<tr style="border-top: 2px solid #2E5FA3; background-color: #dde4f0;">'
        '<td colspan="5" style="padding: 5px 8px; font-weight: bold; text-align: right;">Equipment Subtotal</td>'
        '<td style="padding: 5px 8px; text-align: right; font-family: \'Roboto Mono\', monospace; font-weight: bold;">{total}</td>'
        '</tr>'
    ).format(total=php_format(equip_total))

    table_html = (
        '<table class="dlia-table" style="width: 100%; border-collapse: collapse; font-size: 0.9em; table-layout: fixed;">'
        "<colgroup>"
        '<col style="width: 12%;">'
        '<col style="width: 28%;">'
        '<col style="width: 8%;">'
        '<col style="width: 17%;">'
        '<col style="width: 17%;">'
        '<col style="width: 18%;">'
        "</colgroup>"
        "<thead>{header}</thead>"
        "<tbody>{rows}</tbody>"
        "</table>"
    ).format(
        header=header_row,
        rows=rows_html,
    )

    return '<div class="dlia-section section-b">{}</div>'.format(table_html)


# ---------------------------------------------------------------------------
# Section F: Material Table (D19, D23)
# ---------------------------------------------------------------------------

def render_material_table(material_rows, wbs_prefix=""):
    """Render Section C (Materials) HTML table with WBS numbering and descriptions.

    NOTE: buying_rate IS the Rate column (D19). margin, wastage_percent are hidden from print.
    Columns: No. | Material Name | Qty | UOM | Rate | Amount
    Description appears as a sub-row indented under Material Name column.

    Args:
        material_rows: List of dicts with keys: item_code, item_name, adjusted_qty, uom,
                       buying_rate, amount, item_description (optional HTML from Item master)
        wbs_prefix: Scope WBS number e.g. "A.1" — items become "A.1.1", "A.1.2", etc.
                    If empty, falls back to simple 1, 2, 3 numbering.

    Returns:
        str: Complete HTML section with <div class="dlia-section section-c"> wrapper
    """
    header_style = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: left;"'
    header_right = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: right;"'
    header_center = 'style="background-color: #3B5998; color: #ffffff; padding: 6px 8px; text-align: center;"'

    header_row = (
        "<tr>"
        "<th {hc}>No.</th>"
        "<th {h}>Material Name</th>"
        "<th {hr}>Qty</th>"
        "<th {h}>UOM</th>"
        "<th {hr}>Rate</th>"
        "<th {hr}>Amount</th>"
        "</tr>"
    ).format(h=header_style, hr=header_right, hc=header_center)

    rows_html = ""
    mat_total = 0
    for i, row in enumerate(material_rows or []):
        bg = "#F4F6F9" if i % 2 == 0 else "#ffffff"
        row_style = 'style="background-color: {bg};"'.format(bg=bg)
        # Data rows: bold weight, dark color for emphasis over descriptions
        td = 'style="padding: 5px 8px; font-weight: 600; color: #2D3142;"'
        td_center = 'style="padding: 5px 8px; text-align: center; font-weight: 600; color: #2D3142;"'
        td_right = 'style="padding: 5px 8px; text-align: right; font-family: \'Roboto Mono\', monospace; font-weight: 600; color: #2D3142;"'

        # WBS item number: "A.1.1" or fallback to "1"
        item_num = "{}.{}".format(wbs_prefix, i + 1) if wbs_prefix else str(i + 1)

        # Zero rate with nonzero amount = lump sum → show "—" instead of "PHP 0.00"
        rate_val = float(row.get("buying_rate", 0) or 0)
        amt_val = float(row.get("amount", 0) or 0)
        rate_display = "&mdash;" if rate_val == 0 and amt_val != 0 else php_format(rate_val)

        mat_total += amt_val
        rows_html += (
            "<tr {row}>"
            "<td {tdc}>{row_num}</td>"
            "<td {td}>{item_name}</td>"
            "<td {tdr}>{adjusted_qty}</td>"
            "<td {td}>{uom}</td>"
            "<td {tdr}>{buying_rate}</td>"
            "<td {tdr}>{amount}</td>"
            "</tr>"
        ).format(
            row=row_style,
            td=td,
            tdc=td_center,
            tdr=td_right,
            row_num=item_num,
            item_name=row.get("item_name", ""),
            adjusted_qty=num_format(row.get("adjusted_qty", 0)),
            uom=row.get("uom", ""),
            buying_rate=rate_display,
            amount=php_format(amt_val),
        )

        # Description sub-row — skips No. column, indented under Material Name
        desc = row.get("item_description") or ""
        if desc and desc.strip():
            rows_html += (
                '<tr style="background-color: {bg};">'
                '<td style="border-top: none;"></td>'
                '<td colspan="5" style="padding: 2px 8px 6px 20px; font-size: 7.5pt; color: #555555; '
                'border-top: none; line-height: 1.4; font-weight: 400;">'
                '{desc}'
                '</td>'
                '</tr>'
            ).format(bg=bg, desc=desc)

    # Subtotal row
    rows_html += (
        '<tr style="border-top: 2px solid #2E5FA3; background-color: #dde4f0;">'
        '<td colspan="5" style="padding: 5px 8px; font-weight: bold; text-align: right;">Materials Subtotal</td>'
        '<td style="padding: 5px 8px; text-align: right; font-family: \'Roboto Mono\', monospace; font-weight: bold;">{total}</td>'
        '</tr>'
    ).format(total=php_format(mat_total))

    table_html = (
        '<table class="dlia-table" style="width: 100%; border-collapse: collapse; font-size: 0.9em; table-layout: fixed;">'
        "<colgroup>"
        '<col style="width: 8%;">'
        '<col style="width: 28%;">'
        '<col style="width: 8%;">'
        '<col style="width: 10%;">'
        '<col style="width: 22%;">'
        '<col style="width: 24%;">'
        "</colgroup>"
        "<thead>{header}</thead>"
        "<tbody>{rows}</tbody>"
        "</table>"
    ).format(
        header=header_row,
        rows=rows_html,
    )

    return '<div class="dlia-section section-c">{}</div>'.format(table_html)
