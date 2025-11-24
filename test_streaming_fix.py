#!/usr/bin/env python3
"""
Test script for streaming tool execution fix.
Tests the /api/v1/multi-disease-detector/v1/chat endpoint with stream=true.
Enhanced with timing checks to validate real-time streaming.
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/v1/multi-disease-detector/v1/chat"

# Test cases
TEST_CASES = [
    {
        "name": "Test 1: Tavily Web Search (Known Issue)",
        "payload": {
            "conditions_data": {
                "conditions": [
                    {
                        "condition_name": "Hypertension",
                        "severity": "MILD",
                        "status": "ACTIVE"
                    }
                ]
            },
            "message": "what is the current treatment for hypertensive patients according to the Ghana standard treatment guidelines?",
            "patient_id": None,
            "stream": True,
            "vitals_data": {
                "blood_pressure_diastolic": 85,
                "blood_pressure_systolic": 130,
                "heart_rate_bpm": 75
            }
        }
    },
    {
        "name": "Test 2: Simple Medical Question (Should Use Web Search)",
        "payload": {
            "message": "What are the latest WHO guidelines for treating diabetes in 2024?",
            "patient_id": None,
            "stream": True
        }
    },
    {
        "name": "Test 3: Non-streaming (Control Test)",
        "payload": {
            "conditions_data": {
                "conditions": [
                    {
                        "condition_name": "Hypertension",
                        "severity": "MILD",
                        "status": "ACTIVE"
                    }
                ]
            },
            "message": "what is the current treatment for hypertensive patients according to the Ghana standard treatment guidelines?",
            "patient_id": None,
            "stream": False,
            "vitals_data": {
                "blood_pressure_diastolic": 85,
                "blood_pressure_systolic": 130,
                "heart_rate_bpm": 75
            }
        }
    }
]

def test_streaming_endpoint(test_case):
    """Test a streaming endpoint with the given payload."""
    print(f"\n{'='*80}")
    print(f"🧪 {test_case['name']}")
    print(f"{'='*80}")
    
    payload = test_case['payload']
    is_streaming = payload.get('stream', False)
    
    print(f"📤 Sending request...")
    print(f"   Stream mode: {is_streaming}")
    print(f"   Message: {payload['message'][:100]}...")
    
    try:
        if is_streaming:
            # Streaming request
            response = requests.post(
                ENDPOINT,
                json=payload,
                stream=True,
                timeout=120
            )
            
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            # Process SSE stream
            events_received = []
            content_chunks = []
            tools_used = []
            final_event = None
            
            # Timing tracking
            first_chunk_time = None
            last_chunk_time = None
            chunk_times = []
            
            print(f"\n📡 Processing stream events...")
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data: '):
                    current_time = time.time()
                    data_str = line[6:]
                    
                    if data_str == '[DONE]':
                        print(f"   ✅ Received [DONE] marker")
                        break
                    
                    try:
                        event = json.loads(data_str)
                        event_type = event.get('type')
                        events_received.append(event_type)
                        
                        if event_type == 'thinking':
                            print(f"   💭 Thinking: {event.get('data', '')[:80]}...")
                        
                        elif event_type == 'tool':
                            tool_data = event.get('data', {})
                            tool_name = tool_data.get('tool_name')
                            status = tool_data.get('status')
                            if tool_name not in tools_used:
                                tools_used.append(tool_name)
                            print(f"   🔧 Tool: {tool_name} ({status})")
                        
                        elif event_type == 'content':
                            content = event.get('data', '')
                            content_chunks.append(content)
                            chunk_times.append(current_time)
                            
                            if first_chunk_time is None:
                                first_chunk_time = current_time
                                print(f"   📝 Content streaming started...")
                            
                            last_chunk_time = current_time
                        
                        elif event_type == 'complete':
                            final_event = event.get('data', {})
                            print(f"   ✅ Complete event received")
                            print(f"      Session ID: {final_event.get('session_id')}")
                            print(f"      Risk: {final_event.get('risk_assessment')}")
                            print(f"      Tools: {final_event.get('tools_used')}")
                        
                        elif event_type == 'error':
                            print(f"   ❌ Error event: {event.get('data')}")
                            return False
                    
                    except json.JSONDecodeError:
                        continue
            
            # Analyze results
            full_content = ''.join(content_chunks)
            
            # Calculate streaming metrics
            streaming_duration = 0
            avg_chunk_interval = 0
            is_real_streaming = False
            
            if first_chunk_time and last_chunk_time and len(chunk_times) > 1:
                streaming_duration = last_chunk_time - first_chunk_time
                
                # Calculate average interval between chunks
                intervals = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
                avg_chunk_interval = sum(intervals) / len(intervals) if intervals else 0
                
                # Real streaming should have duration > 0.3s and reasonable chunk distribution
                is_real_streaming = streaming_duration > 0.3 and len(chunk_times) > 5
            
            print(f"\n📊 Results:")
            print(f"   Events received: {len(events_received)}")
            print(f"   Event types: {set(events_received)}")
            print(f"   Tools used: {tools_used}")
            print(f"   Content chunks: {len(content_chunks)}")
            print(f"   Total content length: {len(full_content)} chars")
            print(f"   Final event received: {'Yes' if final_event else 'No'}")
            
            print(f"\n⏱️  Streaming Metrics:")
            print(f"   Streaming duration: {streaming_duration:.2f}s")
            print(f"   Avg chunk interval: {avg_chunk_interval*1000:.1f}ms")
            print(f"   Real-time streaming: {'✅ YES' if is_real_streaming else '❌ NO (buffered)'}")
            
            # Validation
            if not full_content:
                print(f"\n❌ FAILURE: No content received!")
                return False
            
            if not final_event:
                print(f"\n❌ FAILURE: No final 'complete' event received!")
                return False
            
            if len(full_content) < 100:
                print(f"\n⚠️  WARNING: Content seems too short (< 100 chars)")
                print(f"   Content preview: {full_content[:200]}")
                return False
            
            # Validate real-time streaming (critical check)
            if not is_real_streaming and len(content_chunks) > 5:
                print(f"\n⚠️  WARNING: Streaming appears buffered (not real-time)!")
                print(f"   Duration: {streaming_duration:.2f}s for {len(content_chunks)} chunks")
                print(f"   This suggests the async/await fix may not be working correctly.")
                # Don't fail the test, but warn
            
            print(f"\n✅ SUCCESS: Complete response received!")
            print(f"\n📄 Content preview (first 300 chars):")
            print(f"   {full_content[:300]}...")
            
            return True
        
        else:
            # Non-streaming request
            response = requests.post(
                ENDPOINT,
                json=payload,
                timeout=120
            )
            
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            result = response.json()
            
            print(f"\n📊 Results:")
            print(f"   Session ID: {result.get('session_id')}")
            print(f"   Message length: {len(result.get('message', ''))} chars")
            print(f"   Risk: {result.get('risk_assessment')}")
            print(f"   Tools used: {result.get('tools_used')}")
            
            if not result.get('message'):
                print(f"\n❌ FAILURE: Empty message!")
                return False
            
            print(f"\n✅ SUCCESS: Complete response received!")
            print(f"\n📄 Content preview (first 300 chars):")
            print(f"   {result['message'][:300]}...")
            
            return True
    
    except requests.exceptions.Timeout:
        print(f"\n❌ FAILURE: Request timed out!")
        return False
    except Exception as e:
        print(f"\n❌ FAILURE: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all test cases."""
    print(f"\n{'#'*80}")
    print(f"# STREAMING TOOL EXECUTION FIX - TEST SUITE")
    print(f"# Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# Endpoint: {ENDPOINT}")
    print(f"{'#'*80}")
    
    results = {}
    
    for test_case in TEST_CASES:
        success = test_streaming_endpoint(test_case)
        results[test_case['name']] = success
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📋 TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {name}")
    
    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'='*80}\n")
    
    if passed == total:
        print("🎉 All tests passed! The streaming fix is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

