"""
Comprehensive test suite for Drug Suggester feature.
Tests 10 different scenarios and analyzes the results.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://localhost:8000"
PATIENT_ID = "541a5903-ab43-44ea-ac90-0e5ff81f4273"  # New test patient with medications & allergies
DOCTOR_ID = "d4b5d223-cf41-4548-ac6a-27847e7158f6"  # New test doctor

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Test 1: Basic Diabetes",
        "diagnosis": "Type 2 Diabetes Mellitus",
        "additional_conditions": None
    },
    {
        "name": "Test 2: Diabetes with Hypertension",
        "diagnosis": "Type 2 Diabetes Mellitus",
        "additional_conditions": ["Hypertension", "Hyperlipidemia"]
    },
    {
        "name": "Test 3: Malaria Treatment",
        "diagnosis": "Uncomplicated Malaria",
        "additional_conditions": None
    },
    {
        "name": "Test 4: Hypertension",
        "diagnosis": "Essential Hypertension",
        "additional_conditions": None
    },
    {
        "name": "Test 5: Pneumonia with Asthma",
        "diagnosis": "Pneumonia",
        "additional_conditions": ["Asthma"]
    },
    {
        "name": "Test 6: Asthma Management",
        "diagnosis": "Asthma",
        "additional_conditions": None
    },
    {
        "name": "Test 7: UTI",
        "diagnosis": "Urinary Tract Infection",
        "additional_conditions": None
    },
    {
        "name": "Test 8: Peptic Ulcer",
        "diagnosis": "Peptic Ulcer Disease",
        "additional_conditions": ["GERD"]
    },
    {
        "name": "Test 9: HIV/AIDS",
        "diagnosis": "HIV infection",
        "additional_conditions": None
    },
    {
        "name": "Test 10: Typhoid Fever",
        "diagnosis": "Typhoid Fever",
        "additional_conditions": None
    }
]


def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_subheader(text: str):
    """Print formatted subheader"""
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80)


def analyze_drug_suggestions(suggestions: List[Dict], label: str):
    """Analyze and display drug suggestions"""
    if not suggestions:
        print(f"  ❌ No {label} suggestions")
        return
    
    print(f"\n  ✅ {len(suggestions)} {label} suggestion(s):")
    for idx, drug in enumerate(suggestions, 1):
        print(f"\n  [{idx}] {drug.get('drug_name', 'Unknown')} ({drug.get('generic_name', 'N/A')})")
        print(f"      Dosage: {drug.get('dosage', 'N/A')}")
        print(f"      Frequency: {drug.get('frequency', 'N/A')}")
        print(f"      Duration: {drug.get('duration', 'N/A')}")
        print(f"      In Inventory: {drug.get('in_facility_inventory', False)}")
        print(f"      Interaction Status: {drug.get('interaction_status', 'unknown')}")
        print(f"      Allergy Safe: {drug.get('allergy_safe', False)}")
        
        # Show rationale (truncated)
        rationale = drug.get('selection_rationale', '')
        if rationale:
            print(f"      Selection: {rationale[:100]}...")
        
        # Show available facilities
        facilities = drug.get('available_facilities', [])
        if facilities:
            print(f"      Available in {len(facilities)} facilities")


def analyze_response(response_data: Dict[str, Any], test_name: str):
    """Analyze a single test response"""
    print_subheader(test_name)
    
    # Basic info
    print(f"\n  Patient: {response_data.get('patient_name', 'Unknown')}")
    print(f"  Diagnosis: {response_data.get('diagnosis', 'Unknown')}")
    print(f"  Processing Time: {response_data.get('processing_time_seconds', 0):.2f}s")
    print(f"  RxNav Used: {response_data.get('rxnav_used', False)} {'✅' if response_data.get('rxnav_used') else '❌'}")
    
    # Patient context
    current_meds = response_data.get('current_medications', [])
    allergies = response_data.get('allergy_alerts', [])
    
    print(f"\n  Patient Context:")
    print(f"    - Current Medications: {len(current_meds)}")
    if current_meds:
        for med in current_meds:
            print(f"      • {med}")
    
    print(f"    - Allergies: {len(allergies)}")
    if allergies:
        for allergy in allergies:
            print(f"      • {allergy}")
    
    # Suggestions
    primary = response_data.get('primary_suggestions', [])
    alternate = response_data.get('alternate_suggestions', [])
    
    analyze_drug_suggestions(primary, "PRIMARY")
    analyze_drug_suggestions(alternate, "ALTERNATE")
    
    # Warnings
    interaction_warnings = response_data.get('interaction_warnings', [])
    contraindication_alerts = response_data.get('contraindication_alerts', [])
    
    if interaction_warnings:
        print(f"\n  ⚠️  Interaction Warnings ({len(interaction_warnings)}):")
        for warning in interaction_warnings:
            print(f"      • {warning}")
    
    if contraindication_alerts:
        print(f"\n  ⚠️  Contraindication Alerts ({len(contraindication_alerts)}):")
        for alert in contraindication_alerts:
            print(f"      • {alert}")
    
    # Ghana guidelines
    guidelines = response_data.get('ghana_guideline_notes', '')
    if guidelines:
        print(f"\n  📚 Ghana Guidelines (truncated):")
        print(f"      {guidelines[:200]}...")


async def run_single_test(client: httpx.AsyncClient, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test scenario"""
    payload = {
        "patient_id": PATIENT_ID,
        "diagnosis": scenario["diagnosis"],
        "doctor_id": DOCTOR_ID
    }
    
    if scenario["additional_conditions"]:
        payload["additional_conditions"] = scenario["additional_conditions"]
    
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/drug-suggester/suggest",
            json=payload,
            timeout=60.0
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "status_code": 200
            }
        else:
            return {
                "success": False,
                "error": response.json(),
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": None
        }


async def run_all_tests():
    """Run all test scenarios"""
    print_header("DRUG SUGGESTER COMPREHENSIVE TEST SUITE")
    print(f"\nPatient ID: {PATIENT_ID}")
    print(f"Doctor ID: {DOCTOR_ID}")
    print(f"Base URL: {BASE_URL}")
    print(f"Total Tests: {len(TEST_SCENARIOS)}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    async with httpx.AsyncClient() as client:
        for idx, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"\n\n{'#' * 80}")
            print(f"  Running Test {idx}/{len(TEST_SCENARIOS)}: {scenario['name']}")
            print(f"{'#' * 80}")
            
            result = await run_single_test(client, scenario)
            results.append({
                "scenario": scenario,
                "result": result
            })
            
            if result["success"]:
                analyze_response(result["data"], scenario["name"])
            else:
                print(f"\n  ❌ TEST FAILED")
                print(f"  Status Code: {result['status_code']}")
                print(f"  Error: {result['error']}")
            
            # Small delay between tests
            await asyncio.sleep(1)
    
    # Summary
    print_header("TEST SUMMARY")
    
    successful_tests = sum(1 for r in results if r["result"]["success"])
    failed_tests = len(results) - successful_tests
    
    print(f"\n✅ Successful: {successful_tests}/{len(results)}")
    print(f"❌ Failed: {failed_tests}/{len(results)}")
    
    # Analyze RxNav usage
    rxnav_used_count = sum(
        1 for r in results 
        if r["result"]["success"] and r["result"]["data"].get("rxnav_used", False)
    )
    print(f"\n🔬 RxNav API Used: {rxnav_used_count}/{successful_tests} successful tests")
    
    if rxnav_used_count == 0:
        print("\n⚠️  WARNING: RxNav was NOT used in any test!")
        print("   Possible reasons:")
        print("   1. Patient has no current medications (nothing to check interactions for)")
        print("   2. RxNav API is unavailable")
        print("   3. Drug names couldn't be normalized to RxCUI codes")
    
    # Analyze drug patterns
    print_header("DRUG PATTERN ANALYSIS")
    
    all_primary_drugs = {}
    all_alternate_drugs = {}
    
    for test_result in results:
        if not test_result["result"]["success"]:
            continue
        
        data = test_result["result"]["data"]
        
        # Count primary drugs
        for drug in data.get("primary_suggestions", []):
            drug_name = drug.get("drug_name", "Unknown")
            all_primary_drugs[drug_name] = all_primary_drugs.get(drug_name, 0) + 1
        
        # Count alternate drugs
        for drug in data.get("alternate_suggestions", []):
            drug_name = drug.get("drug_name", "Unknown")
            all_alternate_drugs[drug_name] = all_alternate_drugs.get(drug_name, 0) + 1
    
    print("\n📊 Most Frequently Suggested PRIMARY Drugs:")
    sorted_primary = sorted(all_primary_drugs.items(), key=lambda x: x[1], reverse=True)
    for drug, count in sorted_primary[:10]:
        print(f"   {drug}: {count} times")
    
    print("\n📊 Most Frequently Suggested ALTERNATE Drugs:")
    sorted_alternate = sorted(all_alternate_drugs.items(), key=lambda x: x[1], reverse=True)
    for drug, count in sorted_alternate[:10]:
        print(f"   {drug}: {count} times")
    
    # Check if same drugs appear repeatedly
    if sorted_primary and sorted_primary[0][1] > 3:
        print(f"\n⚠️  '{sorted_primary[0][0]}' appears {sorted_primary[0][1]} times in primary suggestions")
        print("   This might indicate:")
        print("   - AI is defaulting to common drugs")
        print("   - Inventory database might be empty (no drugs in stock)")
        print("   - Ghana guidelines consistently recommend this drug")
    
    print(f"\n\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🧪 Starting Drug Suggester Comprehensive Tests...")
    print("⚠️  Make sure the server is running at http://localhost:8000\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

