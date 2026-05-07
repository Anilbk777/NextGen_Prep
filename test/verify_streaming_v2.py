import requests
import json
import time

def test_streaming():
    url = "http://localhost:8000/rag/stream"
    payload = {"query": "What topics are covered in Chapter 1?"}
    
    print(f"Connecting to {url}...")
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, stream=True, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        if response.status_code != 200:
            print(f"Error Body: {response.text}")
            return

        print("Receiving stream:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"DEBUG: {decoded_line}")
                if decoded_line.startswith('data: '):
                    data_str = decoded_line[6:]
                    try:
                        data = json.loads(data_str)
                        if data['type'] == 'token':
                            print(data['content'], end='', flush=True)
                        elif data['type'] == 'status':
                            print(f"\n[STATUS: {data['content']}]")
                        elif data['type'] == 'error':
                            print(f"\n[ERROR: {data['content']}]")
                    except json.JSONDecodeError:
                        if data_str == "[DONE]":
                            print("\n[STREAM COMPLETE]")
                        else:
                            print(f"\n[RAW DATA: {data_str}]")
                elif decoded_line.startswith('event: '):
                    print(f"\n[EVENT: {decoded_line[7:]}]")
        
        print(f"\nTotal time: {time.time() - start_time:.2f}s")
                    
    except requests.exceptions.Timeout:
        print("\nRequest timed out.")
    except Exception as e:
        print(f"\nError connecting to server: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_streaming()
