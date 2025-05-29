
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
    
    def test_calculate_route_with_valid_keys(self, tomtom_api_key, weather_api_key):
        """Test route calculation with valid API keys to check new features"""
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M")
        success, response = self.run_test(
            "Calculate Route - Valid API Keys",
            "POST",
            "api/calculate-route",
            200,
            data={
                "source": "New York",
                "destination": "Boston",
                "transport_mode": "driving",
                "start_time": current_time,
                "tomtom_api_key": tomtom_api_key,
                "weather_api_key": weather_api_key
            }
        )
        
        if success:
            # Test for new features in the response
            self.validate_new_features(response)
            
        return success, response
    
    def validate_new_features(self, response):
        """Validate the new features in the route response"""
        print("\n🔍 Validating new features in the response...")
        
        # Check for route_geometry
        if "route_geometry" not in response:
            print("❌ Missing route_geometry in response")
            self.tests_run += 1
        else:
            print("✅ route_geometry is present in response")
            self.tests_run += 1
            self.tests_passed += 1
            
            # Check if route_geometry is a list of coordinates
            if isinstance(response["route_geometry"], list) and len(response["route_geometry"]) > 0:
                print(f"✅ route_geometry contains {len(response['route_geometry'])} coordinate points")
                self.tests_run += 1
                self.tests_passed += 1
            else:
                print("❌ route_geometry is empty or not a list")
                self.tests_run += 1
        
        # Check for distance information in points
        if "points" in response and len(response["points"]) > 0:
            has_distance_from_source = all("distance_from_source" in point for point in response["points"])
            has_distance_to_destination = all("distance_to_destination" in point for point in response["points"])
            
            if has_distance_from_source:
                print("✅ All points have distance_from_source field")
                self.tests_run += 1
                self.tests_passed += 1
            else:
                print("❌ Some points are missing distance_from_source field")
                self.tests_run += 1
                
            if has_distance_to_destination:
                print("✅ All points have distance_to_destination field")
                self.tests_run += 1
                self.tests_passed += 1
            else:
                print("❌ Some points are missing distance_to_destination field")
                self.tests_run += 1
            
            # Check for road conditions in intermediate points
            intermediate_points = [p for p in response["points"] if p.get("point_type") == "checkpoint"]
            if intermediate_points:
                has_road_conditions = all("road_conditions" in point for point in intermediate_points)
                if has_road_conditions:
                    print("✅ All checkpoint points have road_conditions field")
                    self.tests_run += 1
                    self.tests_passed += 1
                    
                    # Check road conditions structure
                    first_point = intermediate_points[0]
                    if "road_conditions" in first_point and isinstance(first_point["road_conditions"], dict):
                        road_conditions = first_point["road_conditions"]
                        required_fields = ["condition", "current_speed", "free_flow_speed", "color"]
                        missing_fields = [field for field in required_fields if field not in road_conditions]
                        
                        if not missing_fields:
                            print("✅ Road conditions contain all required fields")
                            self.tests_run += 1
                            self.tests_passed += 1
                        else:
                            print(f"❌ Road conditions missing fields: {', '.join(missing_fields)}")
                            self.tests_run += 1
                else:
                    print("❌ Some checkpoint points are missing road_conditions field")
                    self.tests_run += 1
            else:
                print("ℹ️ No intermediate points to check for road conditions")

def main():
    # Setup
    tester = WeatherRoutePlannerTester()
    
    # Run basic tests
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
    
    # Test with valid API keys if provided
    # Note: In a real test, you would provide valid API keys here
    # For this test, we'll skip this part as we don't have valid keys
    print("\n⚠️ Skipping tests with valid API keys as they are not provided")
    print("To test the new features completely, valid TomTom and WeatherAPI keys would be needed")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
