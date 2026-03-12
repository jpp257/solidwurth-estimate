"""
create_scope_templates.py
Idempotent script to create all standard Scope Templates for SolidWurth Estimate.
Run via: bench --site <site> execute solidwurth_estimate.setup.create_scope_templates.create_all
"""

import frappe


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------

def make_template(name, dpwh_pay_item, uom, output_per_day, description="",
                  labor=None, equipment=None, materials=None):
    return {
        "template_name": name,
        "description": description,
        "dpwh_pay_item": dpwh_pay_item,
        "uom": uom,
        "output_per_day": output_per_day,
        "labor_rows": labor or [],
        "equipment_rows": equipment or [],
        "material_rows": materials or [],
    }


def L(role, persons, daily_rate):
    """Labor row helper."""
    return {"role": role, "persons": persons, "daily_rate": daily_rate}


def E(units, daily_rate, ownership_type="Owned"):
    """Equipment row helper."""
    return {"item": None, "units": units, "daily_rate": daily_rate, "ownership_type": ownership_type}


def M(qty, wastage_percent, uom, rate=0):
    """Material row helper."""
    return {"item": None, "qty": qty, "wastage_percent": wastage_percent, "uom": uom, "rate": rate}


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

SCOPE_TEMPLATES = [

    # =====================================================================
    # EARTHWORK (3 templates)
    # =====================================================================
    make_template(
        "Earthwork - Manual Excavation",
        dpwh_pay_item="802(1)b",
        uom="Cubic Meter",
        output_per_day=4.0,
        description="Manual excavation of rock material for roadway and drainage works",
        labor=[
            L("Foreman", 1, 1400),
            L("Laborer", 4, 645),
        ],
    ),

    make_template(
        "Earthwork - Backhoe Excavation",
        dpwh_pay_item="802(1)a",
        uom="Cubic Meter",
        output_per_day=80.0,
        description="Machine excavation using backhoe/excavator for common material",
        labor=[
            L("Foreman", 1, 1400),
            L("Heavy Equipment Operator", 1, 1300),
            L("Helper", 1, 700),
        ],
        equipment=[
            E(units=1, daily_rate=7500, ownership_type="Rented"),
        ],
    ),

    make_template(
        "Compacted Embankment / Fill",
        dpwh_pay_item="804(4)",
        uom="Cubic Meter",
        output_per_day=50.0,
        description="Compacted embankment using plate compactor or roller",
        labor=[
            L("Foreman", 1, 1400),
            L("Equipment Operator", 1, 1200),
            L("Laborer", 4, 645),
        ],
        equipment=[
            E(units=1, daily_rate=1500, ownership_type="Owned"),
        ],
    ),

    # =====================================================================
    # CONCRETE WORKS (8 templates)
    # =====================================================================
    make_template(
        "Concrete Pouring - Footing",
        dpwh_pay_item="900(1)",
        uom="Cubic Meter",
        output_per_day=6.0,
        description="Structural concrete pouring for isolated/combined footings",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Concrete Pourer", 4, 645),
            L("Helper", 2, 700),
        ],
        equipment=[
            E(units=1, daily_rate=500, ownership_type="Owned"),
        ],
        materials=[
            M(qty=9.5, wastage_percent=3, uom="Bag"),
            M(qty=0.5, wastage_percent=5, uom="Cubic Meter"),
            M(qty=1.0, wastage_percent=5, uom="Cubic Meter"),
        ],
    ),

    make_template(
        "Concrete Pouring - Column/Beam",
        dpwh_pay_item="900(1)",
        uom="Cubic Meter",
        output_per_day=4.0,
        description="Structural concrete pouring for columns and beams",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Concrete Pourer", 4, 645),
            L("Helper", 2, 700),
        ],
        equipment=[
            E(units=1, daily_rate=500, ownership_type="Owned"),
        ],
        materials=[
            M(qty=10.0, wastage_percent=3, uom="Bag"),
            M(qty=0.5, wastage_percent=5, uom="Cubic Meter"),
            M(qty=1.0, wastage_percent=5, uom="Cubic Meter"),
        ],
    ),

    make_template(
        "Concrete Pouring - Slab on Grade",
        dpwh_pay_item="900(1)",
        uom="Cubic Meter",
        output_per_day=10.0,
        description="Structural concrete slab on grade — includes vibration and finishing",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 3, 950),
            L("Concrete Pourer", 6, 645),
            L("Helper", 3, 700),
        ],
        equipment=[
            E(units=2, daily_rate=500, ownership_type="Owned"),
        ],
        materials=[
            M(qty=9.5, wastage_percent=3, uom="Bag"),
            M(qty=0.5, wastage_percent=5, uom="Cubic Meter"),
            M(qty=1.0, wastage_percent=5, uom="Cubic Meter"),
        ],
    ),

    make_template(
        "Lean Concrete Subbase",
        dpwh_pay_item="901(1)",
        uom="Cubic Meter",
        output_per_day=12.0,
        description="Lean concrete subbase/blinding layer",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Laborer", 4, 645),
        ],
    ),

    make_template(
        "Formworks - Footing",
        dpwh_pay_item="903(1)",
        uom="Square Meter",
        output_per_day=25.0,
        description="Formworks and falseworks for isolated/combined footings",
        labor=[
            L("Foreman", 1, 1400),
            L("Formworks Carpenter", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Formworks - Column/Beam",
        dpwh_pay_item="903(1)",
        uom="Square Meter",
        output_per_day=18.0,
        description="Formworks and falseworks for columns and beams",
        labor=[
            L("Foreman", 1, 1400),
            L("Formworks Carpenter", 3, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Masonry - CHB 100mm",
        dpwh_pay_item="920(1)",
        uom="Square Meter",
        output_per_day=9.0,
        description="Concrete hollow block laying — 100mm thick wall",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Masonry - CHB 150mm",
        dpwh_pay_item="920(2)",
        uom="Square Meter",
        output_per_day=8.0,
        description="Concrete hollow block laying — 150mm thick wall",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # REBAR (2 templates)
    # =====================================================================
    make_template(
        "Rebar Installation - Grade 40 (Footing)",
        dpwh_pay_item="1000(2)",
        uom="Kilogram",
        output_per_day=600.0,
        description="Reinforcing steel Grade 40 cutting, bending, and tying for footings",
        labor=[
            L("Foreman", 1, 1400),
            L("Steel Worker", 2, 1000),
            L("Rebar Cutter/Bender", 2, 750),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Rebar Installation - Grade 60 (Slab)",
        dpwh_pay_item="1000(3)",
        uom="Kilogram",
        output_per_day=500.0,
        description="Reinforcing steel Grade 60 cutting, bending, and tying for slabs",
        labor=[
            L("Foreman", 1, 1400),
            L("Steel Worker", 2, 1000),
            L("Rebar Cutter/Bender", 2, 750),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # STRUCTURAL STEEL (2 templates)
    # =====================================================================
    make_template(
        "Structural Steel Erection",
        dpwh_pay_item="1100(1)",
        uom="Kilogram",
        output_per_day=600.0,
        description="Structural steel erection including crane lifting and bolting",
        labor=[
            L("Foreman", 1, 1400),
            L("Steel Worker", 4, 1000),
            L("Ironworker", 2, 1000),
            L("Welder", 2, 1050),
            L("Helper", 2, 700),
        ],
        equipment=[
            E(units=1, daily_rate=12000, ownership_type="Rented"),
        ],
    ),

    make_template(
        "Steel Roofing - Purlins",
        dpwh_pay_item="1909(1)",
        uom="Kilogram",
        output_per_day=800.0,
        description="Steel purlin installation (Z-type and C-type) for roof framing",
        labor=[
            L("Foreman", 1, 1400),
            L("Steel Worker", 3, 1000),
            L("Welder", 2, 1050),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # ROOFING (3 templates)
    # =====================================================================
    make_template(
        "Roof Sheeting - Long Span G.I.",
        dpwh_pay_item="1901(1)",
        uom="Square Meter",
        output_per_day=60.0,
        description="Long span corrugated GI roof sheeting installation",
        labor=[
            L("Foreman", 1, 1400),
            L("Carpenter", 2, 950),
            L("Helper", 3, 700),
        ],
    ),

    make_template(
        "Roof Sheeting - Insulated Panel",
        dpwh_pay_item="1903(1)",
        uom="Square Meter",
        output_per_day=40.0,
        description="Insulated metal roofing panel installation (PIR core)",
        labor=[
            L("Foreman", 1, 1400),
            L("Insulation Worker", 3, 1000),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Cold Room Panel Installation",
        dpwh_pay_item="1914(1)",
        uom="Square Meter",
        output_per_day=20.0,
        description="Cold room PIR insulated panel installation for walls and ceilings",
        labor=[
            L("Foreman", 1, 1400),
            L("Insulation Worker", 4, 1000),
            L("Carpenter", 2, 950),
        ],
    ),

    # =====================================================================
    # FINISHES (5 templates)
    # =====================================================================
    make_template(
        "Floor Tiling - Ceramic 300x300",
        dpwh_pay_item="1703(1)",
        uom="Square Meter",
        output_per_day=10.0,
        description="Ceramic floor tile 300x300mm installation with adhesive and grout",
        labor=[
            L("Foreman", 1, 1400),
            L("Tile Setter", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Wall Tiling - Ceramic",
        dpwh_pay_item="1705(1)",
        uom="Square Meter",
        output_per_day=8.0,
        description="Ceramic wall tile 250x375mm installation with adhesive and grout",
        labor=[
            L("Foreman", 1, 1400),
            L("Tile Setter", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Ceiling - Gypsum Board",
        dpwh_pay_item="1706(1)",
        uom="Square Meter",
        output_per_day=20.0,
        description="Gypsum board ceiling on metal furring grid",
        labor=[
            L("Foreman", 1, 1400),
            L("Carpenter", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Painting - Interior Latex",
        dpwh_pay_item="1602(1)",
        uom="Square Meter",
        output_per_day=40.0,
        description="Interior acrylic latex painting — putty, primer, 2 finish coats",
        labor=[
            L("Foreman", 1, 1400),
            L("Painter", 2, 800),
            L("Helper", 1, 700),
        ],
    ),

    make_template(
        "Epoxy Floor Coating",
        dpwh_pay_item="1603(1)",
        uom="Square Meter",
        output_per_day=25.0,
        description="Standard epoxy floor coating 2-coat system",
        labor=[
            L("Foreman", 1, 1400),
            L("Painter", 2, 800),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # ELECTRICAL (2 templates)
    # =====================================================================
    make_template(
        "Electrical Rough-in (Conduit + Wiring)",
        dpwh_pay_item="1402(1)",
        uom="Lot",
        output_per_day=1.0,
        description="Electrical rough-in works — conduit installation and wiring",
        labor=[
            L("Foreman", 1, 1400),
            L("Electrician", 2, 1050),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Electrical Fixtures and Devices",
        dpwh_pay_item="1401(1)",
        uom="Lot",
        output_per_day=1.0,
        description="Electrical fixture installation — lighting, receptacles, switches",
        labor=[
            L("Foreman", 1, 1400),
            L("Electrician", 2, 1050),
            L("Helper", 1, 700),
        ],
    ),

    # =====================================================================
    # PLUMBING (2 templates)
    # =====================================================================
    make_template(
        "Plumbing Rough-in (PVC Supply + Drain)",
        dpwh_pay_item="1504(1)",
        uom="Lot",
        output_per_day=1.0,
        description="Plumbing rough-in — water supply and drainage rough works",
        labor=[
            L("Foreman", 1, 1400),
            L("Plumber", 2, 1050),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Sanitary Fixtures Installation",
        dpwh_pay_item="1506(1)",
        uom="Lot",
        output_per_day=1.0,
        description="Sanitary fixtures installation — WC, lavatory, shower sets",
        labor=[
            L("Foreman", 1, 1400),
            L("Plumber", 2, 1050),
            L("Helper", 1, 700),
        ],
    ),

    # =====================================================================
    # FOOD PROCESSING (5 templates)
    # =====================================================================
    make_template(
        "Food Processing - Concrete Floor Slab (High-spec)",
        dpwh_pay_item="900(1)",
        uom="Cubic Meter",
        output_per_day=8.0,
        description="Structural concrete slab for food processing — Class AA (40MPa), power-troweled",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Mason", 3, 950),
            L("Concrete Pourer", 6, 645),
            L("Helper", 3, 700),
        ],
        equipment=[
            E(units=2, daily_rate=500, ownership_type="Owned"),
            E(units=1, daily_rate=1200, ownership_type="Rented"),
        ],
    ),

    make_template(
        "Food Processing - Epoxy Food-Grade Floor",
        dpwh_pay_item="1603(1)",
        uom="Square Meter",
        output_per_day=20.0,
        description="Food-grade epoxy floor coating — 4-coat system, coved skirting",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Painter", 3, 800),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Food Processing - FRP Wall Cladding",
        dpwh_pay_item="1309(1)",
        uom="Square Meter",
        output_per_day=15.0,
        description="Fiberglass Reinforced Plastic (FRP) wall cladding for food processing facility",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Carpenter", 3, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Food Processing - Stainless Steel Drain Trench",
        dpwh_pay_item="1503(1)",
        uom="Meter",
        output_per_day=8.0,
        description="Stainless steel drain trench with grating for food processing areas",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Pipefitter", 2, 1100),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Food Processing - Hygienic Door and Frame",
        dpwh_pay_item="1301(1)",
        uom="Nos",
        output_per_day=3.0,
        description="Hygienic door and frame installation — stainless steel or FRP, food-grade",
        labor=[
            L("Carpenter", 2, 950),
            L("Helper", 1, 700),
        ],
    ),

    # =====================================================================
    # COLD STORAGE (4 templates)
    # =====================================================================
    make_template(
        "Cold Storage - PIR Insulated Wall Panel",
        dpwh_pay_item="1914(1)",
        uom="Square Meter",
        output_per_day=18.0,
        description="PIR insulated cold room wall panel installation",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Insulation Worker", 4, 1000),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Cold Storage - Refrigeration System",
        dpwh_pay_item="1512(1)",
        uom="TR",
        output_per_day=1.0,
        description="Cold storage refrigeration system — compressor, condenser, evaporator installation",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Refrigeration Mechanic", 3, 1100),
            L("Instrument Technician", 1, 1200),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Cold Storage - Cold Room Door",
        dpwh_pay_item="1915(1)",
        uom="Nos",
        output_per_day=2.0,
        description="Cold room insulated swing door installation with cam-action hinges",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Insulation Worker", 2, 1000),
            L("Helper", 1, 700),
        ],
    ),

    make_template(
        "Cold Storage - Vapor Barrier and Insulation",
        dpwh_pay_item="1914(1)",
        uom="Square Meter",
        output_per_day=30.0,
        description="Vapor barrier membrane and insulation installation for cold storage",
        labor=[
            L("Insulation Worker", 3, 1000),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # WASTEWATER TREATMENT (3 templates)
    # =====================================================================
    make_template(
        "Wastewater - Concrete Equalization Tank",
        dpwh_pay_item="900(1)",
        uom="Cubic Meter",
        output_per_day=5.0,
        description="Reinforced concrete equalization tank for wastewater treatment",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Mason", 3, 950),
            L("Concrete Pourer", 6, 645),
            L("Rebar Cutter/Bender", 3, 750),
        ],
        equipment=[
            E(units=2, daily_rate=500, ownership_type="Owned"),
        ],
    ),

    make_template(
        "Wastewater - HDPE Liner Installation",
        dpwh_pay_item="1203(1)",
        uom="Square Meter",
        output_per_day=50.0,
        description="HDPE geomembrane liner installation for wastewater lagoon/pond",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Waterproofing Applicator", 3, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Wastewater - Process Piping (UPVC)",
        dpwh_pay_item="1503(2)",
        uom="Meter",
        output_per_day=15.0,
        description="UPVC process piping for wastewater treatment system",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Pipefitter", 3, 1100),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # POULTRY (3 templates)
    # =====================================================================
    make_template(
        "Poultry - Ventilation System (Evap Cooling)",
        dpwh_pay_item="1510(1)",
        uom="Lot",
        output_per_day=1.0,
        description="Evaporative cooling ventilation system for poultry house",
        labor=[
            L("Civil Works Foreman", 1, 1500),
            L("Electrician", 2, 1050),
            L("Pipefitter", 1, 1100),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Poultry - Wire Mesh Caging System",
        dpwh_pay_item="1106(1)",
        uom="Square Meter",
        output_per_day=20.0,
        description="Galvanized wire mesh battery cage system for poultry layers",
        labor=[
            L("Foreman", 1, 1400),
            L("Steel Worker", 3, 1000),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Poultry - Concrete Feed/Water Trough",
        dpwh_pay_item="906(1)",
        uom="Meter",
        output_per_day=10.0,
        description="Concrete feed and water trough construction for poultry",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    # =====================================================================
    # SITE DEVELOPMENT (2 templates)
    # =====================================================================
    make_template(
        "Perimeter Fence - CHB",
        dpwh_pay_item="1801(1)",
        uom="Meter",
        output_per_day=5.0,
        description="CHB perimeter fence 2.4m high with CHB, plaster, and capping",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Concrete Paving - Parking",
        dpwh_pay_item="1803(1)",
        uom="Square Meter",
        output_per_day=30.0,
        description="Concrete paving for parking area — 150mm thick, broom finish",
        labor=[
            L("Foreman", 1, 1400),
            L("Mason", 2, 950),
            L("Concrete Pourer", 4, 645),
            L("Helper", 2, 700),
        ],
        equipment=[
            E(units=1, daily_rate=1200, ownership_type="Owned"),
        ],
    ),

    # =====================================================================
    # WATERPROOFING (2 templates)
    # =====================================================================
    make_template(
        "Crystalline Waterproofing - Concrete Surfaces",
        dpwh_pay_item="1203(1)",
        uom="Square Meter",
        output_per_day=40.0,
        description="Crystalline cementitious waterproofing applied to concrete surfaces",
        labor=[
            L("Foreman", 1, 1400),
            L("Waterproofing Applicator", 2, 950),
            L("Helper", 2, 700),
        ],
    ),

    make_template(
        "Torch-applied Bituminous Membrane",
        dpwh_pay_item="1201(1)",
        uom="Square Meter",
        output_per_day=30.0,
        description="Torch-applied modified bitumen membrane waterproofing for roofs and slabs",
        labor=[
            L("Foreman", 1, 1400),
            L("Waterproofing Applicator", 3, 950),
            L("Helper", 2, 700),
        ],
    ),

]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

REQUIRED_UOMS = [
    "Bag", "Cubic Meter", "Kilogram", "Lot", "Meter", "Nos", "Set", "Square Meter", "TR",
]


def ensure_uoms():
    """Ensure required UOM records exist (needed in bare Frappe dev environments)."""
    for uom_name in REQUIRED_UOMS:
        if not frappe.db.exists("UOM", uom_name):
            doc = frappe.new_doc("UOM")
            doc.uom_name = uom_name
            doc.insert(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def create_all():
    """
    Idempotent: creates Scope Template records that do not yet exist.
    Safe to run multiple times — existing records are skipped.
    Also ensures required UOMs exist in the database first.
    """
    ensure_uoms()

    created = 0
    skipped = 0

    for tmpl in SCOPE_TEMPLATES:
        name = tmpl["template_name"]

        if frappe.db.exists("Scope Template", name):
            skipped += 1
            continue

        doc = frappe.new_doc("Scope Template")
        doc.template_name = name
        doc.description = tmpl.get("description", "")
        doc.dpwh_pay_item = tmpl.get("dpwh_pay_item")
        doc.uom = tmpl.get("uom")
        doc.output_per_day = tmpl.get("output_per_day", 0)

        for row in tmpl.get("labor_rows", []):
            doc.append("labor_rows", row)

        # Equipment and material rows require Item records (project-specific).
        # Rows with item=None are skipped; they can be added per-project in production.
        for row in tmpl.get("equipment_rows", []):
            if row.get("item") is not None:
                doc.append("equipment_rows", row)

        for row in tmpl.get("material_rows", []):
            if row.get("item") is not None:
                doc.append("material_rows", row)

        doc.insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()
    print(f"Scope Templates: {created} created, {skipped} skipped.")
    return {"created": created, "skipped": skipped}
