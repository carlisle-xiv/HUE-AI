"""
Test script for ML-based risk assessment system.

Run this to verify the risk assessment logic works correctly
and produces expected results for various query types.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from multi_disease_detector.risk_assessment import (
    calculate_risk_assessment,
    classify_intent,
    detect_critical_emergency,
    detect_urgent_situation,
    calculate_severity_score,
)

# Test cases
TEST_CASES = [
    # Informational queries (should be LOW risk)
    {
        "user_message": "What is diabetes?",
        "expected_risk": "LOW",
        "description": "Basic medical information query"
    },
    {
        "user_message": "what is the current treatment for hypertensive patients according to the Ghana standard treatment guidelines?",
        "expected_risk": "LOW",
        "description": "Treatment guidelines query (your original example)"
    },
    {
        "user_message": "How does high blood pressure work?",
        "expected_risk": "LOW",
        "description": "Educational query about medical condition"
    },
    {
        "user_message": "Explain the symptoms of malaria",
        "expected_risk": "LOW",
        "description": "Symptom information request"
    },
    {
        "user_message": "What are the side effects of metformin?",
        "expected_risk": "LOW",
        "description": "Medication information query"
    },
    
    # Monitoring queries (should be MEDIUM risk)
    {
        "user_message": "Is my blood pressure of 130/85 normal?",
        "expected_risk": "MEDIUM",
        "description": "Monitoring existing values"
    },
    {
        "user_message": "Are these test results concerning?",
        "expected_risk": "MEDIUM",
        "description": "Test result interpretation"
    },
    
    # Symptom reports (should be MEDIUM to HIGH risk)
    {
        "user_message": "I have a headache that's been going on for 3 days",
        "expected_risk": "MEDIUM",
        "description": "Mild symptom, chronic"
    },
    {
        "user_message": "I'm experiencing chest discomfort after exercise",
        "expected_risk": "HIGH",
        "description": "Chest-related symptom (concerning but not emergency)"
    },
    {
        "user_message": "I have a fever and body aches",
        "expected_risk": "MEDIUM",
        "description": "Common symptoms"
    },
    
    # Urgent situations (should be HIGH risk)
    {
        "user_message": "I have severe abdominal pain that started suddenly",
        "expected_risk": "HIGH",
        "description": "Acute severe pain"
    },
    {
        "user_message": "My blood pressure is 180/120 and I feel dizzy",
        "expected_risk": "HIGH",
        "description": "Hypertensive crisis"
    },
    
    # Emergencies (should be EMERGENCY)
    {
        "user_message": "I can't breathe properly",
        "expected_risk": "EMERGENCY",
        "description": "Respiratory distress"
    },
    {
        "user_message": "I have crushing chest pain radiating to my left arm",
        "expected_risk": "EMERGENCY",
        "description": "Possible heart attack"
    },
    {
        "user_message": "Someone is having a seizure",
        "expected_risk": "EMERGENCY",
        "description": "Seizure emergency"
    },
]

def run_tests():
    """Run all test cases and report results."""
    print("=" * 80)
    print("RISK ASSESSMENT SYSTEM TEST")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    # Dummy AI message and patient context
    dummy_ai_message = "Based on your query, here's some information..."
    dummy_patient_context = "Patient has history of controlled hypertension"
    
    for i, test in enumerate(TEST_CASES, 1):
        user_message = test["user_message"]
        expected_risk = test["expected_risk"]
        description = test["description"]
        
        print(f"Test {i}: {description}")
        print(f"Query: '{user_message}'")
        
        # Test intent classification
        intent = classify_intent(user_message)
        print(f"  Intent: {intent}")
        
        # Test emergency detection
        is_critical = detect_critical_emergency(user_message)
        is_urgent = detect_urgent_situation(user_message)
        print(f"  Critical Emergency: {is_critical}, Urgent: {is_urgent}")
        
        # Test full risk assessment
        risk_level, should_see_doctor = calculate_risk_assessment(
            message=dummy_ai_message,
            patient_context=dummy_patient_context,
            user_message=user_message
        )
        
        print(f"  Risk Assessment: {risk_level} (expected: {expected_risk})")
        print(f"  Should See Doctor: {should_see_doctor}")
        
        # Check if test passed
        if risk_level == expected_risk:
            print("  ✅ PASSED")
            passed += 1
        else:
            print("  ❌ FAILED")
            failed += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(TEST_CASES)}")
    print(f"Passed: {passed} ({passed/len(TEST_CASES)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(TEST_CASES)*100:.1f}%)")
    print()
    
    if failed == 0:
        print("🎉 All tests passed! Risk assessment is working correctly.")
    else:
        print(f"⚠️  {failed} test(s) failed. Review the logic and thresholds.")
    
    print()
    
    # Additional info
    print("=" * 80)
    print("NOTES")
    print("=" * 80)
    print("• If ML model (MiniLM) is not loaded, system falls back to rule-based")
    print("• Install dependencies: pip install sentence-transformers torch")
    print("• To disable ML: export USE_SMART_RISK_ASSESSMENT=false")
    print("• False positives reduced by analyzing user intent, not just keywords")
    print()


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("=" * 80)
    print("EDGE CASE TESTS")
    print("=" * 80)
    print()
    
    edge_cases = [
        {
            "user_message": "",
            "description": "Empty message"
        },
        {
            "user_message": "a" * 1000,
            "description": "Very long message"
        },
        {
            "user_message": "Hello, how are you?",
            "description": "Non-medical query"
        },
        {
            "user_message": "blood pressure diabetes hypertension emergency severe",
            "description": "Multiple high-risk keywords"
        },
    ]
    
    for test in edge_cases:
        user_message = test["user_message"]
        description = test["description"]
        
        print(f"Edge Case: {description}")
        if len(user_message) > 50:
            print(f"Query: '{user_message[:50]}...' (truncated)")
        else:
            print(f"Query: '{user_message}'")
        
        try:
            risk_level, should_see_doctor = calculate_risk_assessment(
                message="Response...",
                patient_context="Patient context...",
                user_message=user_message
            )
            print(f"  Risk: {risk_level}, See Doctor: {should_see_doctor}")
            print("  ✅ No error")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        
        print()


if __name__ == "__main__":
    print("\n")
    run_tests()
    test_edge_cases()
    print("Test completed!\n")

