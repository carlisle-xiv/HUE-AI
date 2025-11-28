#!/usr/bin/env python3
"""
Python client test for validating real-time streaming.
Measures timing between chunks to verify progressive delivery.
"""

import requests
import time
import json
import sys

url = "http://localhost:8000/api/v1/multi-disease_detector/v1/chat"
payload = {
    "message": "What are the symptoms of diabetes?",
    "stream": True
}

print("=" * 70)
print("REAL-TIME STREAMING VALIDATION TEST")
print("=" * 70)
print(f"\nEndpoint: {url}")
print(f"Testing streaming with timing measurements...\n")

try:
    print("Starting stream...\n")
    start_time = time.time()
    last_chunk_time = start_time
    chunk_count = 0
    total_content = ""
    intervals = []

    with requests.post(url, json=payload, stream=True, timeout=60) as response:
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                current_time = time.time()
                
                data = line[6:]
                if data == '[DONE]':
                    print("\n✅ [DONE] marker received")
                    break
                
                try:
                    event = json.loads(data)
                    if event.get('type') == 'content':
                        interval = current_time - last_chunk_time
                        intervals.append(interval)
                        chunk_count += 1
                        content = event['data']
                        total_content += content
                        
                        # Print with timing (first 5 chunks detailed)
                        if chunk_count <= 5:
                            print(f"[+{interval*1000:6.1f}ms] Chunk {chunk_count:3d}: {content[:40]}")
                        elif chunk_count % 50 == 0:
                            print(f"[+{interval*1000:6.1f}ms] Chunk {chunk_count:3d}: ... ({len(content)} chars)")
                        
                        last_chunk_time = current_time
                
                except json.JSONDecodeError:
                    pass

    total_time = time.time() - start_time
    
    # Analysis
    print("\n" + "=" * 70)
    print("📊 STREAMING ANALYSIS")
    print("=" * 70)
    print(f"\n✓ Stream completed successfully")
    print(f"  Total chunks:        {chunk_count}")
    print(f"  Total content:       {len(total_content)} characters")
    print(f"  Total duration:      {total_time:.2f}s")
    
    if intervals:
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        
        print(f"\n⏱️  Timing Metrics:")
        print(f"  Average interval:    {avg_interval*1000:.1f}ms")
        print(f"  Min interval:        {min_interval*1000:.1f}ms")
        print(f"  Max interval:        {max_interval*1000:.1f}ms")
        
        # Validation
        print(f"\n🎯 Validation:")
        if total_time > 1.0 and chunk_count > 10:
            print(f"  ✅ Real-time streaming: YES")
            print(f"     (Duration: {total_time:.1f}s, Chunks distributed over time)")
        else:
            print(f"  ❌ Real-time streaming: NO")
            print(f"     (All chunks arrived too quickly - possible buffering)")
        
        if avg_interval < 0.1:  # Less than 100ms average
            print(f"  ✅ Low latency: YES ({avg_interval*1000:.1f}ms avg)")
        else:
            print(f"  ⚠️  Latency higher than expected ({avg_interval*1000:.1f}ms avg)")
    
    print(f"\n📄 Content preview (first 200 chars):")
    print(f"   {total_content[:200]}...")
    print("\n" + "=" * 70)
    
except requests.exceptions.ConnectionError:
    print("\n❌ Connection refused! Is the server running?")
    print("   Start server with: python main.py")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

