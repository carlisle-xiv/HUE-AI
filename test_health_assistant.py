"""
Test script for Health Assistant API
Demonstrates basic usage of the chat endpoints
"""

import requests
import base64
import json
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:8000"
HEALTH_ASSISTANT_URL = f"{BASE_URL}/api/v1/health-assistant"


def test_health_check():
    """Test if models are loaded and ready"""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    response = requests.get(f"{HEALTH_ASSISTANT_URL}/health")
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")

    return data


def test_text_chat():
    """Test text-only medical query"""
    print("\n" + "=" * 60)
    print("TEST 2: Text-Only Chat (BioMistral)")
    print("=" * 60)

    payload = {
        "prompt": "I've been experiencing persistent headaches for the past 3 days, especially in the morning. What could be causing this?",
        "user_id": "test_user_123",
        "temperature": 0.7,
        "max_tokens": 300,
    }

    print(f"Sending request: {payload['prompt'][:50]}...")

    response = requests.post(f"{HEALTH_ASSISTANT_URL}/chat", json=payload)
    data = response.json()

    print(f"\nStatus: {response.status_code}")
    print(f"Session ID: {data.get('session_id')}")
    print(f"Model Used: {data.get('model_used')}")
    print(f"Response: {data.get('response')[:200]}...")

    return data


def test_continue_conversation(session_id):
    """Test continuing a conversation with session ID"""
    print("\n" + "=" * 60)
    print("TEST 3: Continue Conversation")
    print("=" * 60)

    payload = {
        "prompt": "Should I see a doctor about this? Is it urgent?",
        "session_id": session_id,
        "user_id": "test_user_123",
        "temperature": 0.7,
    }

    print(f"Continuing session: {session_id}")
    print(f"Follow-up question: {payload['prompt']}")

    response = requests.post(f"{HEALTH_ASSISTANT_URL}/chat", json=payload)
    data = response.json()

    print(f"\nStatus: {response.status_code}")
    print(f"Session ID: {data.get('session_id')}")
    print(f"Response: {data.get('response')[:200]}...")

    return data


def test_get_conversation_history(session_id):
    """Test retrieving conversation history"""
    print("\n" + "=" * 60)
    print("TEST 4: Get Conversation History")
    print("=" * 60)

    response = requests.get(f"{HEALTH_ASSISTANT_URL}/sessions/{session_id}")
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Session ID: {data['session']['id']}")
    print(f"Created: {data['session']['created_at']}")
    print(f"Total Messages: {len(data['messages'])}")

    print("\nConversation:")
    for i, msg in enumerate(data["messages"], 1):
        role = msg["role"].upper()
        content = msg["content"][:100]
        print(f"\n{i}. {role}: {content}...")

    return data


def test_image_chat():
    """Test image analysis (if image available)"""
    print("\n" + "=" * 60)
    print("TEST 5: Image Analysis (LLaVA)")
    print("=" * 60)

    # Check if a test image exists
    test_image_path = Path("test_image.jpg")

    if not test_image_path.exists():
        print("⚠ No test image found. Skipping image test.")
        print("To test image analysis, place a test image as 'test_image.jpg'")
        return None

    # Read and encode image
    with open(test_image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    payload = {
        "prompt": "What do you see in this image? Can you describe any medical concerns?",
        "image_base64": image_base64,
        "user_id": "test_user_456",
        "temperature": 0.7,
    }

    print(f"Sending image for analysis...")
    print(f"Prompt: {payload['prompt']}")

    response = requests.post(f"{HEALTH_ASSISTANT_URL}/chat", json=payload)
    data = response.json()

    print(f"\nStatus: {response.status_code}")
    print(f"Session ID: {data.get('session_id')}")
    print(f"Model Used: {data.get('model_used')}")
    print(f"Has Image: {data.get('has_image')}")
    print(f"Response: {data.get('response')[:200]}...")

    return data


def test_list_sessions():
    """Test listing user sessions"""
    print("\n" + "=" * 60)
    print("TEST 6: List User Sessions")
    print("=" * 60)

    response = requests.get(
        f"{HEALTH_ASSISTANT_URL}/sessions",
        params={"user_id": "test_user_123", "active_only": True},
    )
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Total Sessions: {data.get('total')}")

    if data.get("sessions"):
        print("\nSessions:")
        for session in data["sessions"]:
            print(
                f"  - ID: {session['id'][:8]}... | Active: {session['is_active']} | Created: {session['created_at']}"
            )

    return data


def test_end_session(session_id):
    """Test ending a session"""
    print("\n" + "=" * 60)
    print("TEST 7: End Session")
    print("=" * 60)

    response = requests.delete(f"{HEALTH_ASSISTANT_URL}/sessions/{session_id}")
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Session ID: {data.get('id')}")
    print(f"Is Active: {data.get('is_active')}")
    print(f"Ended At: {data.get('ended_at')}")

    return data


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("HEALTH ASSISTANT API TEST SUITE")
    print("=" * 60)
    print("\nMake sure the server is running at http://localhost:8000")
    print("Starting tests in 3 seconds...")

    import time

    time.sleep(3)

    try:
        # Test 1: Health check
        health_status = test_health_check()

        if health_status.get("status") != "healthy":
            print("\n⚠ WARNING: Models are not fully loaded. Some tests may fail.")
            print("Please wait for models to load and try again.")
            return

        # Test 2: Text chat
        chat_response = test_text_chat()
        session_id = chat_response.get("session_id")

        # Test 3: Continue conversation
        test_continue_conversation(session_id)

        # Test 4: Get conversation history
        test_get_conversation_history(session_id)

        # Test 5: Image analysis (optional)
        test_image_chat()

        # Test 6: List sessions
        test_list_sessions()

        # Test 7: End session
        test_end_session(session_id)

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Could not connect to server.")
        print("Please make sure the server is running:")
        print("  python main.py")
        print("  or")
        print("  uvicorn main:app --reload")

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
