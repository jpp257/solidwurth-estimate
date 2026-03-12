# Test module for bench execute
# Run via: bench --site dev.localhost execute solidwurth_estimate.tests.test_estimate_behavior.run_cascade_delete_test

import frappe


def run_cascade_delete_test():
    """AC4: Deleting an Estimate deletes all linked Estimate Scopes (no orphans)."""
    # Create Estimate
    est = frappe.new_doc("Estimate")
    est.estimate_title = "Delete Test 11-02"
    est.ocm_percent = 5
    est.profit_percent = 15
    est.insert()
    est_name = est.name

    # Create Estimate Scope linked to it
    scope = frappe.new_doc("Estimate Scope")
    scope.estimate = est_name
    scope.scope_name = "Test Scope 11-02"
    scope.insert()
    scope_name = scope.name
    frappe.db.commit()

    print("Created: {} with scope {}".format(est_name, scope_name))

    # Delete Estimate — on_trash should cascade to Scope
    frappe.delete_doc("Estimate", est_name)
    frappe.db.commit()

    # Verify scope is gone
    remaining = frappe.get_all("Estimate Scope", filters={"estimate": est_name}, pluck="name")
    print("Remaining scopes after delete: {}".format(remaining))
    assert len(remaining) == 0, "CASCADE DELETE FAILED — {} orphan scopes found".format(len(remaining))
    print("CASCADE DELETE: PASS")
    return "PASS"


def run_status_validation_test():
    """AC5: Status transitions enforce valid paths; invalid transitions throw error."""
    # Create a test Estimate
    est = frappe.new_doc("Estimate")
    est.estimate_title = "Status Test 11-02"
    est.ocm_percent = 5
    est.profit_percent = 15
    est.insert()
    name = est.name
    print("Created: {} in Draft status".format(name))

    # Valid transition: Draft -> Under Review (should succeed)
    est.status = "Under Review"
    est.save()
    print("Draft -> Under Review: PASS")

    # Invalid transition: Under Review -> Converted (skip Approved — should fail)
    try:
        est.status = "Converted"
        est.save()
        frappe.delete_doc("Estimate", name)
        assert False, "FAIL: Should have thrown for Under Review -> Converted"
    except frappe.exceptions.ValidationError as e:
        print("Under Review -> Converted blocked correctly: PASS")

    # Cleanup
    # Reload doc to get current DB state before delete
    est = frappe.get_doc("Estimate", name)
    frappe.delete_doc("Estimate", name)
    frappe.db.commit()
    print("STATUS VALIDATION: PASS")
    return "PASS"


def run_whitelist_copy_test():
    """AC3: create_scope_from_template works via direct API (bot pathway)."""
    from solidwurth_estimate.estimate.doctype.estimate.estimate import (
        create_scope_from_template,
        create_scopes_from_templates,
    )

    # Create a Scope Template
    tmpl = frappe.new_doc("Scope Template")
    tmpl.template_name = "API Test Template 11-02"
    tmpl.output_per_day = 20
    tmpl.insert()
    tmpl_name = tmpl.name

    # Create Estimate
    est = frappe.new_doc("Estimate")
    est.estimate_title = "Whitelist Test 11-02"
    est.ocm_percent = 5
    est.profit_percent = 15
    est.insert()
    est_name = est.name
    frappe.db.commit()

    # Call whitelist method directly (AC3 — bot pathway)
    scope_name = create_scope_from_template(est_name, tmpl_name, "Test Group")
    print("Created scope: {}".format(scope_name))
    assert scope_name.startswith("ESC-"), "Wrong naming: {}".format(scope_name)

    # Test same template with different scope_group (AC6)
    scope2_name = create_scope_from_template(est_name, tmpl_name, "Second Group")
    assert scope_name != scope2_name, "Should create separate scopes for different groups"
    print("Second scope: {}".format(scope2_name))

    # Verify both exist
    scopes = frappe.get_all("Estimate Scope", filters={"estimate": est_name}, pluck="name")
    assert len(scopes) == 2, "Expected 2 scopes, got {}".format(len(scopes))
    print("Two independent scopes created: PASS")

    # Cleanup — cascade delete both scopes
    frappe.delete_doc("Estimate", est_name)
    frappe.delete_doc("Scope Template", tmpl_name)
    frappe.db.commit()
    print("WHITELIST COPY: PASS")
    return "PASS"


def run_all_tests():
    """Run all three behavior tests."""
    results = {}
    for test_fn in [run_cascade_delete_test, run_status_validation_test, run_whitelist_copy_test]:
        try:
            result = test_fn()
            results[test_fn.__name__] = result
        except Exception as e:
            import traceback
            results[test_fn.__name__] = "FAIL: {}".format(e)
            traceback.print_exc()
            try:
                frappe.db.rollback()
            except Exception:
                pass

    print("\n=== RESULTS ===")
    all_pass = True
    for name, result in results.items():
        print("{}: {}".format(name, result))
        if result != "PASS":
            all_pass = False

    if all_pass:
        print("ALL TESTS PASS")
    else:
        print("SOME TESTS FAILED")
    return results
