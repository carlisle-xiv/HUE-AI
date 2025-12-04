#!/usr/bin/env python3
"""
Professional Chat Endpoint Test Suite

Tests the /v1/chat/professional endpoint with various scenarios and outputs
a detailed report showing response quality for medical professionals.

Usage:
    python test_files/test_professional_chat.py

Requirements:
    - Server must be running on localhost:8000
    - OPENROUTER_API_KEY must be set in environment
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# Configuration
BASE_URL = "http://localhost:8000/api/v1/multi-disease-detector"
PROFESSIONAL_ENDPOINT = f"{BASE_URL}/v1/chat/professional"

# Report output file
REPORT_FILE = "test_files/professional_chat_report.md"


class TestStatus(Enum):
    PASSED = "✅ PASSED"
    FAILED = "❌ FAILED"
    SKIPPED = "⏭️ SKIPPED"


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    status: TestStatus
    duration_ms: float
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class TestReport:
    """Complete test report."""
    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[TestResult] = field(default_factory=list)
    
    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        else:
            self.skipped += 1


# =============================================================================
# TEST CASES
# =============================================================================

TEST_CASES = [
    # Test 1: Physician - Acute Chest Pain Case
    {
        "name": "Physician - STEMI Case",
        "description": "Test physician consultation for acute STEMI presentation",
        "request": {
            "message": "55M presenting with acute onset crushing substernal chest pain radiating to left arm, diaphoretic. ECG shows ST elevation in V2-V4. Troponin pending. What's the DDx and immediate management?",
            "professional_role": "physician",
            "stream": False,
            "clinical_context": {
                "chief_complaint": "Chest pain",
                "history_present_illness": "Acute onset 2 hours ago, crushing substernal pain with radiation to left arm",
                "past_medical_history": ["Hypertension", "Type 2 Diabetes", "Hyperlipidemia", "Former smoker (quit 5 years ago)"],
                "medications": ["Metformin 1000mg BID", "Lisinopril 20mg daily", "Atorvastatin 40mg daily"],
                "allergies": ["PCN - rash"],
                "vitals": {
                    "BP": "168/95 mmHg",
                    "HR": "102 bpm",
                    "RR": "22/min",
                    "SpO2": "94% on RA",
                    "Temp": "37.1°C"
                },
                "labs": {
                    "Troponin_initial": "pending"
                }
            }
        },
        "expected_elements": ["STEMI", "differential", "aspirin", "cath lab", "anticoagulation"]
    },
    
    # Test 2: Physician - Pulmonary Embolism Workup
    {
        "name": "Physician - PE Evaluation",
        "description": "Test physician consultation for suspected pulmonary embolism",
        "request": {
            "message": "65F post-op day 5 from hip replacement presenting with acute dyspnea and pleuritic chest pain. Unilateral leg swelling noted. Calculate Wells score and recommend workup.",
            "professional_role": "physician",
            "stream": False,
            "clinical_context": {
                "chief_complaint": "Dyspnea and chest pain",
                "history_present_illness": "Sudden onset dyspnea this morning, pleuritic chest pain right side",
                "past_medical_history": ["Osteoarthritis", "Total hip replacement 5 days ago"],
                "vitals": {
                    "HR": "110 bpm",
                    "RR": "24/min",
                    "SpO2": "91% on RA",
                    "BP": "138/88 mmHg"
                },
                "physical_exam": "Right calf swelling and tenderness, clear lungs bilaterally"
            }
        },
        "expected_elements": ["Wells", "D-dimer", "CT-PA", "anticoagulation", "PE"]
    },
    
    # Test 3: Radiologist - Chest X-ray Interpretation (text-based)
    {
        "name": "Radiologist - Chest X-ray",
        "description": "Test radiologist interpretation request",
        "request": {
            "message": "Please provide a standardized radiology report for a PA and lateral chest X-ray showing: cardiomegaly with CTR 0.58, bilateral pleural effusions (R>L), cephalization of pulmonary vasculature, Kerley B lines, and bilateral perihilar haziness.",
            "professional_role": "radiologist",
            "stream": False,
            "clinical_context": {
                "chief_complaint": "Dyspnea",
                "past_medical_history": ["CHF", "CAD", "HTN"],
                "clinical_indication": "Shortness of breath, rule out CHF exacerbation"
            }
        },
        "expected_elements": ["cardiomegaly", "effusion", "CHF", "pulmonary edema", "IMPRESSION", "FINDINGS"]
    },
    
    # Test 4: Nurse - Post-operative Assessment
    {
        "name": "Nurse - Post-op Fever Assessment",
        "description": "Test nursing assessment for post-operative patient",
        "request": {
            "message": "Post-op day 1 after total knee replacement. Patient now febrile to 38.6°C with wound erythema. What should I assess and what's my monitoring plan?",
            "professional_role": "nurse",
            "stream": False,
            "clinical_context": {
                "chief_complaint": "Post-op fever",
                "past_medical_history": ["Osteoarthritis", "DM2"],
                "vitals": {
                    "Temp": "38.6°C",
                    "HR": "95 bpm",
                    "BP": "142/85 mmHg"
                }
            }
        },
        "expected_elements": ["fever", "wound", "infection", "monitor", "vital signs", "notify"]
    },
    
    # Test 5: Pharmacist - Drug Interaction Check
    {
        "name": "Pharmacist - Drug Interaction",
        "description": "Test pharmacist drug interaction analysis",
        "request": {
            "message": "Patient on warfarin for AFib, new prescription for fluconazole for vaginal candidiasis. What are the interactions and dosing considerations?",
            "professional_role": "pharmacist",
            "stream": False,
            "clinical_context": {
                "medications": ["Warfarin 5mg daily", "Metoprolol 50mg BID", "Lisinopril 10mg daily"],
                "labs": {
                    "INR": "2.4",
                    "CrCl": "68 mL/min"
                }
            }
        },
        "expected_elements": ["interaction", "INR", "CYP", "warfarin", "monitoring", "dose"]
    },
    
    # Test 6: Resident - Teaching Case
    {
        "name": "Resident - DKA Management",
        "description": "Test resident-focused educational response",
        "request": {
            "message": "I'm managing my first DKA patient. 32F with T1DM, presenting with AMS, Kussmaul respirations. Labs: glucose 580, pH 7.18, bicarb 10, AG 24, K 5.8. Walk me through the management approach.",
            "professional_role": "resident",
            "stream": False,
            "clinical_context": {
                "chief_complaint": "Altered mental status",
                "past_medical_history": ["Type 1 Diabetes"],
                "vitals": {
                    "HR": "115 bpm",
                    "RR": "28/min (Kussmaul)",
                    "BP": "98/62 mmHg"
                },
                "labs": {
                    "Glucose": "580 mg/dL",
                    "pH": "7.18",
                    "HCO3": "10 mEq/L",
                    "Anion_Gap": "24",
                    "K": "5.8 mEq/L",
                    "Na": "132 mEq/L"
                }
            }
        },
        "expected_elements": ["fluid", "insulin", "potassium", "monitor", "gap", "teaching", "pitfall"]
    },
    
    # Test 7: Simple Question - No Clinical Context
    {
        "name": "Simple Clinical Question",
        "description": "Test response without detailed clinical context",
        "request": {
            "message": "What are the diagnostic criteria for sepsis according to Sepsis-3?",
            "professional_role": "physician",
            "stream": False
        },
        "expected_elements": ["SOFA", "qSOFA", "infection", "organ dysfunction", "criteria"]
    },
    
    # Test 8: Specialist - Cardiology Consultation
    {
        "name": "Specialist - AFib Management",
        "description": "Test specialist-level cardiology response",
        "request": {
            "message": "72M with new-onset AFib with RVR, HFrEF (EF 35%), and CKD stage 3b. What's the rhythm vs rate control strategy and anticoagulation considerations?",
            "professional_role": "specialist",
            "stream": False,
            "clinical_context": {
                "past_medical_history": ["CHF (EF 35%)", "CKD Stage 3b", "HTN", "DM2"],
                "labs": {
                    "Cr": "2.1 mg/dL",
                    "eGFR": "32 mL/min"
                },
                "vitals": {
                    "HR": "142 bpm (irregular)",
                    "BP": "118/72 mmHg"
                }
            }
        },
        "expected_elements": ["rate control", "rhythm", "anticoagulation", "CHA2DS2-VASc", "HAS-BLED", "renal dosing"]
    }
]


# =============================================================================
# TEST RUNNER
# =============================================================================

async def run_test(session: aiohttp.ClientSession, test_case: Dict[str, Any]) -> TestResult:
    """Run a single test case."""
    name = test_case["name"]
    request_data = test_case["request"]
    expected_elements = test_case.get("expected_elements", [])
    
    start_time = time.time()
    
    try:
        async with session.post(PROFESSIONAL_ENDPOINT, json=request_data) as response:
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status != 200:
                error_text = await response.text()
                return TestResult(
                    name=name,
                    status=TestStatus.FAILED,
                    duration_ms=duration_ms,
                    request=request_data,
                    error=f"HTTP {response.status}: {error_text[:500]}"
                )
            
            response_data = await response.json()
            
            # Validate response structure
            notes = []
            required_fields = ["session_id", "message", "risk_stratification", "urgency", "clinical_caveat"]
            missing_fields = [f for f in required_fields if f not in response_data]
            
            if missing_fields:
                notes.append(f"Missing required fields: {missing_fields}")
            
            # Check for expected content elements
            message_lower = response_data.get("message", "").lower()
            found_elements = []
            missing_elements = []
            
            for element in expected_elements:
                if element.lower() in message_lower:
                    found_elements.append(element)
                else:
                    missing_elements.append(element)
            
            if found_elements:
                notes.append(f"Found expected elements: {found_elements}")
            if missing_elements:
                notes.append(f"Missing expected elements: {missing_elements}")
            
            # Check response quality indicators
            if response_data.get("risk_stratification"):
                notes.append(f"Risk: {response_data['risk_stratification']}")
            if response_data.get("urgency"):
                notes.append(f"Urgency: {response_data['urgency']}")
            if response_data.get("tools_used"):
                notes.append(f"Tools used: {response_data['tools_used']}")
            
            # Determine status
            status = TestStatus.PASSED
            if missing_fields:
                status = TestStatus.FAILED
            elif len(missing_elements) > len(expected_elements) / 2:
                # Fail if more than half of expected elements are missing
                status = TestStatus.FAILED
            
            return TestResult(
                name=name,
                status=status,
                duration_ms=duration_ms,
                request=request_data,
                response=response_data,
                notes=notes
            )
            
    except aiohttp.ClientError as e:
        duration_ms = (time.time() - start_time) * 1000
        return TestResult(
            name=name,
            status=TestStatus.FAILED,
            duration_ms=duration_ms,
            request=request_data,
            error=f"Connection error: {str(e)}"
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return TestResult(
            name=name,
            status=TestStatus.FAILED,
            duration_ms=duration_ms,
            request=request_data,
            error=f"Unexpected error: {str(e)}"
        )


async def run_streaming_test(session: aiohttp.ClientSession) -> TestResult:
    """Test streaming endpoint."""
    name = "Streaming Test"
    request_data = {
        "message": "Brief DDx for acute appendicitis presentation",
        "professional_role": "physician",
        "stream": True
    }
    
    start_time = time.time()
    
    try:
        async with session.post(PROFESSIONAL_ENDPOINT, json=request_data) as response:
            if response.status != 200:
                duration_ms = (time.time() - start_time) * 1000
                error_text = await response.text()
                return TestResult(
                    name=name,
                    status=TestStatus.FAILED,
                    duration_ms=duration_ms,
                    request=request_data,
                    error=f"HTTP {response.status}: {error_text[:500]}"
                )
            
            # Collect streaming events
            events = []
            event_types = set()
            content_received = ""
            
            async for line in response.content:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        events.append({"type": "done"})
                        break
                    try:
                        event = json.loads(data_str)
                        events.append(event)
                        event_types.add(event.get("type", "unknown"))
                        if event.get("type") == "content":
                            content_received += event.get("data", "")
                    except json.JSONDecodeError:
                        pass
            
            duration_ms = (time.time() - start_time) * 1000
            
            notes = [
                f"Received {len(events)} events",
                f"Event types: {list(event_types)}",
                f"Content length: {len(content_received)} chars"
            ]
            
            # Check for expected event types
            expected_types = {"content", "clinical_thinking"}
            found_types = event_types & expected_types
            
            if "complete" in event_types or "done" in [e.get("type") for e in events]:
                notes.append("Stream completed properly")
                status = TestStatus.PASSED
            else:
                notes.append("Stream did not complete with 'complete' event")
                status = TestStatus.FAILED
            
            return TestResult(
                name=name,
                status=status,
                duration_ms=duration_ms,
                request=request_data,
                response={"events_count": len(events), "event_types": list(event_types)},
                notes=notes
            )
            
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return TestResult(
            name=name,
            status=TestStatus.FAILED,
            duration_ms=duration_ms,
            request=request_data,
            error=f"Streaming error: {str(e)}"
        )


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(report: TestReport) -> str:
    """Generate markdown report."""
    lines = [
        "# Professional Chat Endpoint Test Report",
        "",
        f"**Generated:** {report.timestamp}",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total Tests | {report.total_tests} |",
        f"| {TestStatus.PASSED.value} | {report.passed} |",
        f"| {TestStatus.FAILED.value} | {report.failed} |",
        f"| {TestStatus.SKIPPED.value} | {report.skipped} |",
        "",
        f"**Pass Rate:** {(report.passed / report.total_tests * 100):.1f}%" if report.total_tests > 0 else "N/A",
        "",
        "---",
        "",
        "## Test Results",
        "",
    ]
    
    for i, result in enumerate(report.results, 1):
        lines.extend([
            f"### {i}. {result.name}",
            "",
            f"**Status:** {result.status.value}",
            f"**Duration:** {result.duration_ms:.0f}ms",
            "",
        ])
        
        if result.error:
            lines.extend([
                "**Error:**",
                "```",
                result.error[:1000],
                "```",
                "",
            ])
        
        if result.notes:
            lines.extend([
                "**Notes:**",
                "",
            ])
            for note in result.notes:
                lines.append(f"- {note}")
            lines.append("")
        
        # Show request summary
        lines.extend([
            "**Request:**",
            "```json",
            json.dumps({
                "message": result.request.get("message", "")[:200] + "..." if len(result.request.get("message", "")) > 200 else result.request.get("message", ""),
                "professional_role": result.request.get("professional_role"),
                "stream": result.request.get("stream", False)
            }, indent=2),
            "```",
            "",
        ])
        
        # Show response summary (if available)
        if result.response and result.status == TestStatus.PASSED:
            response_summary = {
                "risk_stratification": result.response.get("risk_stratification"),
                "urgency": result.response.get("urgency"),
                "tools_used": result.response.get("tools_used"),
                "message_preview": result.response.get("message", "")[:500] + "..." if len(result.response.get("message", "")) > 500 else result.response.get("message", "")
            }
            lines.extend([
                "**Response Summary:**",
                "```json",
                json.dumps(response_summary, indent=2),
                "```",
                "",
            ])
            
            # Show full message in a collapsible section
            if result.response.get("message"):
                lines.extend([
                    "<details>",
                    "<summary>Full AI Response (click to expand)</summary>",
                    "",
                    "```",
                    result.response.get("message", ""),
                    "```",
                    "",
                    "</details>",
                    "",
                ])
        
        lines.append("---")
        lines.append("")
    
    # Add test configuration summary
    lines.extend([
        "## Test Configuration",
        "",
        f"- **Endpoint:** `{PROFESSIONAL_ENDPOINT}`",
        f"- **Total Test Cases:** {len(TEST_CASES)}",
        "",
    ])
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run all tests and generate report."""
    print("=" * 60)
    print("Professional Chat Endpoint Test Suite")
    print("=" * 60)
    print()
    
    report = TestReport(timestamp=datetime.now().isoformat())
    
    # Check if server is running
    print("Checking server connection...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/../health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                print(f"Server responded with status: {response.status}")
        except Exception as e:
            print(f"⚠️  Warning: Could not reach health endpoint: {e}")
            print("Proceeding with tests anyway...")
        
        print()
        print("Running tests...")
        print("-" * 40)
        
        # Run regular tests
        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"[{i}/{len(TEST_CASES) + 1}] Running: {test_case['name']}...", end=" ", flush=True)
            result = await run_test(session, test_case)
            report.add_result(result)
            print(f"{result.status.value} ({result.duration_ms:.0f}ms)")
        
        # Run streaming test
        print(f"[{len(TEST_CASES) + 1}/{len(TEST_CASES) + 1}] Running: Streaming Test...", end=" ", flush=True)
        streaming_result = await run_streaming_test(session)
        report.add_result(streaming_result)
        print(f"{streaming_result.status.value} ({streaming_result.duration_ms:.0f}ms)")
    
    print()
    print("-" * 40)
    print(f"Results: {report.passed} passed, {report.failed} failed, {report.skipped} skipped")
    print()
    
    # Generate and save report
    report_content = generate_report(report)
    
    with open(REPORT_FILE, "w") as f:
        f.write(report_content)
    
    print(f"📄 Report saved to: {REPORT_FILE}")
    print()
    
    # Print quick summary to console
    if report.failed > 0:
        print("❌ Some tests failed. Check the report for details.")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

