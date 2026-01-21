import requests
import json

# Test the conversation endpoint
url = "http://localhost:8000/api/conversation"
data = {
    "message": "I need a quote from New York to London for 5 tonnes of general cargo"
}

print("Testing conversation endpoint...")
print(f"Request: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
