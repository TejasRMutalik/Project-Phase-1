import sys
import os
import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("Testing REST API endpoints...")
    try:
        # 1. /api/status
        res = requests.get(f"{BASE_URL}/api/status")
        print("GET /api/status      ->", res.status_code, res.json())

        # 2. /api/config
        res = requests.get(f"{BASE_URL}/api/config")
        print("GET /api/config      ->", res.status_code, "model config:", res.json().get("model"))

        # 3. /api/violations
        res = requests.get(f"{BASE_URL}/api/violations")
        print(f"GET /api/violations  -> {res.status_code}, total recorded violations: {len(res.json())}")

        print("\nAll REST API endpoints responded successfully!")
    except Exception as e:
        print("API test failed:", e)

if __name__ == "__main__":
    main()
