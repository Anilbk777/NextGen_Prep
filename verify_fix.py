import requests
import json

BASE_URL = "http://localhost:8000"  # Adjust if the port is different

def test_save_answer_invalid_id():
    session_id = 10
    mcq_id = 1
    selected_option_id = 0
    
    url = f"{BASE_URL}/mock-tests/sessions/{session_id}/answers"
    payload = {
        "mcq_id": mcq_id,
        "selected_option_id": selected_option_id
    }
    
    # We need a token for get_current_user. 
    # Usually I'd login first, but since I'm testing local logic,
    # I might just try to hit it and see if I get 401/403 first, 
    # or if I can mock the session.
    # Actually, a better way to test this without auth issues is to check the logs 
    # after the user tries it, or use a script that knows how to login.
    
    print(f"Testing POST {url} with payload {payload}")
    # Note: This will likely fail with 401 if auth is enabled and no token is provided.
    # However, if the server is running, we can see if it crashes or returns 400 vs 500 in the server logs.
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # This script assumes the backend is running at BASE_URL
    test_save_answer_invalid_id()
