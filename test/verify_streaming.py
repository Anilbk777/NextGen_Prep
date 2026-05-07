import requests
import json
import sys

def test_streaming():
    url = "http://localhost:8000/rag/stream"
    payload = {"query": "What is photosynthesis?"}
    
    print(f"Connecting to {url}...")
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print("Receiving stream:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
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
                    
    except Exception as e:
        print(f"\nError connecting to server: {e}")

if __name__ == "__main__":
    test_streaming()
