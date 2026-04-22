# test_api_key.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_ENDPOINT")
api_key  = os.getenv("AZURE_API_KEY")

# Test direct REST call with api-key header
url = f"{endpoint}/connections"
headers = {
    "api-key": api_key,
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")