#!/usr/bin/env python3
"""
Test script to verify detailed reporting functionality in validate_dynamodb_data.py

This test verifies that the enhanced reporting includes:
- JSON report with record identifiers
- Severity levels (error, warning, info)
- Fix suggestions
- Detailed statistics and groupings
"""

import json
import sys
import os

def test_report_structure():
    """Test that the validation report has the expected structure"""
    
    # Check if test report exists
    if not os.path.exists("test_validation_report.json"):
        print("ERROR: test_validation_report.json not found")
        print("Run: python3 scripts/validate_dynamodb_data.py --output test_validation_report.json")
        return False
    
    # Load the report
    with open("test_validation_report.json", "r") as f:
        report = json.load(f)
    
    print("Testing report structure...")
    
    # Test 1: Check top-level structure
    required_keys = ["timestamp", "validation_metadata", "summary", "statistics", "issues", "recommendations"]
    for key in required_keys:
        if key not in report:
            print(f"  ❌ Missing required key: {key}")
            return False
    print("  ✅ All required top-level keys present")
    
    # Test 2: Check summary structure
    summary_keys = ["total_issues", "errors", "warnings", "info", "critical_issues", "unresolved_issues", "tables_with_issues", "unique_issue_types"]
    for key in summary_keys:
        if key not in report["summary"]:
            print(f"  ❌ Missing summary key: {key}")
            return False
    print("  ✅ Summary structure correct")
    
    # Test 3: Check statistics structure
    if "by_table" not in report["statistics"] or "by_issue_type" not in report["statistics"]:
        print("  ❌ Missing statistics groupings")
        return False
    print("  ✅ Statistics groupings present")
    
    # Test 4: Check issues structure
    issues_keys = ["all", "by_severity", "by_table", "by_type", "critical", "unresolved"]
    for key in issues_keys:
        if key not in report["issues"]:
            print(f"  ❌ Missing issues grouping: {key}")
            return False
    print("  ✅ Issues groupings present")
    
    # Test 5: Check severity levels in by_severity
    severity_levels = ["errors", "warnings", "info"]
    for level in severity_levels:
        if level not in report["issues"]["by_severity"]:
            print(f"  ❌ Missing severity level: {level}")
            return False
    print("  ✅ All severity levels present")
    
    # Test 6: Check individual issue structure
    if report["issues"]["all"]:
        issue = report["issues"]["all"][0]
        issue_keys = ["severity", "table", "issue_type", "description", "record_id", "fix_suggestion", "timestamp"]
        for key in issue_keys:
            if key not in issue:
                print(f"  ❌ Missing issue field: {key}")
                return False
        print("  ✅ Individual issue structure correct")
    
    # Test 7: Check recommendations structure
    if report["recommendations"]:
        rec = report["recommendations"][0]
        rec_keys = ["priority", "category", "action", "description"]
        for key in rec_keys:
            if key not in rec:
                print(f"  ❌ Missing recommendation field: {key}")
                return False
        print("  ✅ Recommendations structure correct")
    
    # Test 8: Verify severity levels are valid
    valid_severities = {"error", "warning", "info"}
    for issue in report["issues"]["all"]:
        if issue["severity"] not in valid_severities:
            print(f"  ❌ Invalid severity level: {issue['severity']}")
            return False
    print("  ✅ All severity levels are valid")
    
    # Test 9: Verify fix suggestions exist for critical issues
    critical_with_fixes = sum(1 for i in report["issues"]["critical"] if i["fix_suggestion"])
    if critical_with_fixes != len(report["issues"]["critical"]):
        print(f"  ⚠️  Warning: Not all critical issues have fix suggestions ({critical_with_fixes}/{len(report['issues']['critical'])})")
    else:
        print("  ✅ All critical issues have fix suggestions")
    
    # Test 10: Verify record identifiers exist where appropriate
    issues_with_records = [i for i in report["issues"]["all"] if i["record_id"] is not None]
    if issues_with_records:
        print(f"  ✅ Found {len(issues_with_records)} issues with record identifiers")
    else:
        print("  ℹ️  No issues with record identifiers (may be expected)")
    
    print("\n✅ All tests passed!")
    return True

def print_report_summary():
    """Print a summary of the report contents"""
    
    with open("test_validation_report.json", "r") as f:
        report = json.load(f)
    
    print("\n" + "=" * 60)
    print("REPORT SUMMARY")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Region: {report['validation_metadata']['region']}")
    print(f"Tables Validated: {len(report['validation_metadata']['tables_validated'])}")
    print(f"\nTotal Issues: {report['summary']['total_issues']}")
    print(f"  - Errors: {report['summary']['errors']}")
    print(f"  - Warnings: {report['summary']['warnings']}")
    print(f"  - Info: {report['summary']['info']}")
    print(f"\nCritical Issues: {report['summary']['critical_issues']}")
    print(f"Unresolved Issues: {report['summary']['unresolved_issues']}")
    print(f"Tables with Issues: {report['summary']['tables_with_issues']}")
    print(f"Unique Issue Types: {report['summary']['unique_issue_types']}")
    
    print(f"\nRecommendations: {len(report['recommendations'])}")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. [{rec['priority'].upper()}] {rec['action']}")
    
    print("=" * 60)

if __name__ == "__main__":
    success = test_report_structure()
    if success:
        print_report_summary()
        sys.exit(0)
    else:
        print("\n❌ Tests failed")
        sys.exit(1)
