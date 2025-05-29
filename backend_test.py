
import requests
import sys
import json
from datetime import datetime

class WeatherRoutePlannerTester:
    def __init__(self, base_url="https://bd541f5b-875a-4a6c-a12a-2cf1296be15e.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.text:
                    try:
                        return success, response.json()
                    except json.JSONDecodeError:
                        return success, response.text
                return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    try:
                        print(f"Response: {response.json()}")
                    except json.JSONDecodeError:
                        print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_endpoint(self):
        """Test the health endpoint"""
        return self.run_test(
            "Health Endpoint",
            "GET",
            "api/health",
            200
        )

    def test_calculate_route_missing_fields(self):
        """Test route calculation with missing fields"""
        return self.run_test(
            "Calculate Route - Missing Fields",
            "POST",
            "api/calculate-route",
            422,  # Validation error
            data={}
        )

    def test_calculate_route_invalid_api_keys(self):
        """Test route calculation with invalid API keys"""
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M")
        return self.run_test(
            "Calculate Route - Invalid API Keys",
            "POST",
            "api/calculate-route",
            400,  # Bad request
            data={
                "source": "New York",
                "destination": "Boston",
                "transport_mode": "driving",
                "start_time": current_time,
                "tomtom_api_key": "invalid_key",
                "weather_api_key": "invalid_key"
            }
        )

def main():
    # Setup
    tester = WeatherRoutePlannerTester()
    
    # Run tests
    health_success, health_response = tester.test_health_endpoint()
    if not health_success:
        print("❌ Health endpoint failed, backend may not be running properly")
    else:
        print(f"Health endpoint response: {health_response}")
    
    missing_fields_success, _ = tester.test_calculate_route_missing_fields()
    if not missing_fields_success:
        print("❌ Missing fields validation test failed")
    
    invalid_keys_success, invalid_keys_response = tester.test_calculate_route_invalid_api_keys()
    if not invalid_keys_success:
        print("❌ Invalid API keys test failed")
    else:
        print(f"Invalid API keys response: {invalid_keys_response}")

    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
