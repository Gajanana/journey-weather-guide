from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from typing import List, Optional
import asyncio
from datetime import datetime, timedelta
import json

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RouteRequest(BaseModel):
    source: str
    destination: str
    transport_mode: str  # driving, walking, cycling, transit
    start_time: str  # ISO format
    tomtom_api_key: str
    weather_api_key: str

class LocationPoint(BaseModel):
    lat: float
    lng: float
    address: str
    estimated_time: str
    weather: dict

class RouteResponse(BaseModel):
    points: List[LocationPoint]
    total_duration: int  # seconds
    total_distance: int  # meters
    transport_mode: str

# TomTom transport mode mapping
TOMTOM_TRANSPORT_MODES = {
    "driving": "car",
    "walking": "pedestrian", 
    "cycling": "bicycle",
    "transit": "car"  # TomTom doesn't have transit, fallback to car
}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/calculate-route", response_model=RouteResponse)
async def calculate_route(request: RouteRequest):
    try:
        # Step 1: Get coordinates for source and destination
        source_coords = await geocode_location(request.source, request.tomtom_api_key)
        dest_coords = await geocode_location(request.destination, request.tomtom_api_key)
        
        # Step 2: Calculate route
        route_data = await get_route(
            source_coords, dest_coords, 
            request.transport_mode, request.tomtom_api_key
        )
        
        # Step 3: Generate timeline points along the route
        timeline_points = await generate_timeline_points(
            route_data, request.start_time, request.transport_mode, request.tomtom_api_key
        )
        
        # Step 4: Get weather for each point
        points_with_weather = []
        for point in timeline_points:
            weather_data = await get_weather_forecast(
                point["lat"], point["lng"], 
                point["estimated_time"], request.weather_api_key
            )
            
            points_with_weather.append(LocationPoint(
                lat=point["lat"],
                lng=point["lng"],
                address=point["address"],
                estimated_time=point["estimated_time"],
                weather=weather_data
            ))
        
        return RouteResponse(
            points=points_with_weather,
            total_duration=route_data["total_duration"],
            total_distance=route_data["total_distance"],
            transport_mode=request.transport_mode,
            route_geometry=route_data["route_points"]  # Add route geometry for map
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def geocode_location(address: str, api_key: str):
    """Get coordinates for an address using TomTom Geocoding API"""
    async with httpx.AsyncClient() as client:
        url = f"https://api.tomtom.com/search/2/geocode/{address}.json"
        params = {"key": api_key, "limit": 1}
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if not data["results"]:
            raise HTTPException(status_code=404, detail=f"Location not found: {address}")
        
        result = data["results"][0]
        return {
            "lat": result["position"]["lat"],
            "lng": result["position"]["lon"],
            "address": result["address"]["freeformAddress"]
        }

async def get_route(source_coords, dest_coords, transport_mode, api_key):
    """Get route from TomTom Routing API"""
    async with httpx.AsyncClient() as client:
        tomtom_mode = TOMTOM_TRANSPORT_MODES.get(transport_mode, "car")
        
        start_point = f"{source_coords['lat']},{source_coords['lng']}"
        end_point = f"{dest_coords['lat']},{dest_coords['lng']}"
        
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_point}:{end_point}/json"
        params = {
            "key": api_key,
            "travelMode": tomtom_mode,
            "instructionsType": "coded",
            "computeBestOrder": "false",
            "routeRepresentation": "polyline",
            "computeTravelTimeFor": "all",
            "sectionType": "traffic"
        }
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        route = data["routes"][0]
        
        # Extract route geometry points
        route_points = []
        if "legs" in route and len(route["legs"]) > 0:
            leg = route["legs"][0]
            if "points" in leg:
                route_points = [(point["latitude"], point["longitude"]) for point in leg["points"]]
            else:
                # Fallback: use start and end points
                route_points = [
                    (source_coords['lat'], source_coords['lng']),
                    (dest_coords['lat'], dest_coords['lng'])
                ]
        else:
            route_points = [
                (source_coords['lat'], source_coords['lng']),
                (dest_coords['lat'], dest_coords['lng'])
            ]
        
        return {
            "total_duration": route["summary"]["travelTimeInSeconds"],
            "total_distance": route["summary"]["lengthInMeters"],
            "route_points": route_points,
            "source_coords": source_coords,
            "dest_coords": dest_coords,
            "instructions": route["guidance"]["instructions"] if "guidance" in route else []
        }

async def generate_timeline_points(route_data, start_time_str, transport_mode, api_key):
    """Generate points along the route with estimated arrival times"""
    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    total_duration = route_data["total_duration"]
    total_distance = route_data["total_distance"]
    route_points = route_data["route_points"]
    source_coords = route_data["source_coords"]
    dest_coords = route_data["dest_coords"]
    
    # Always include start and end points
    timeline_points = []
    
    # Add starting point
    timeline_points.append({
        "lat": source_coords["lat"],
        "lng": source_coords["lng"],
        "address": source_coords["address"],
        "estimated_time": start_time.isoformat(),
        "point_type": "start",
        "distance_from_source": 0,
        "distance_to_destination": total_distance
    })
    
    # For longer routes, add intermediate checkpoints
    if len(route_points) > 2 and total_duration > 1800:  # More than 30 minutes
        # Calculate how many intermediate points to show (max 8 between start and end)
        num_intermediate = min(8, max(2, total_duration // 3600))  # Roughly every hour
        
        for i in range(1, num_intermediate + 1):
            progress = i / (num_intermediate + 1)
            point_index = int(progress * (len(route_points) - 1))
            
            if point_index < len(route_points):
                lat, lng = route_points[point_index]
                time_offset = int(total_duration * progress)
                distance_from_source = int(total_distance * progress)
                estimated_time = start_time + timedelta(seconds=time_offset)
                
                # Get address for this point
                address = await reverse_geocode(lat, lng, api_key)
                
                # Get traffic/road conditions for this point
                road_conditions = await get_road_conditions(lat, lng, api_key)
                
                timeline_points.append({
                    "lat": lat,
                    "lng": lng,
                    "address": address,
                    "estimated_time": estimated_time.isoformat(),
                    "point_type": "checkpoint",
                    "distance_from_source": distance_from_source,
                    "distance_to_destination": total_distance - distance_from_source,
                    "road_conditions": road_conditions
                })
    
    # Add ending point
    timeline_points.append({
        "lat": dest_coords["lat"],
        "lng": dest_coords["lng"],
        "address": dest_coords["address"],
        "estimated_time": (start_time + timedelta(seconds=total_duration)).isoformat(),
        "point_type": "destination",
        "distance_from_source": total_distance,
        "distance_to_destination": 0
    })
    
    return timeline_points

async def get_road_conditions(lat, lng, api_key):
    """Get traffic and road conditions for a location"""
    try:
        async with httpx.AsyncClient() as client:
            # Get traffic flow data
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
            params = {
                "key": api_key,
                "point": f"{lat},{lng}",
                "unit": "KMPH"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            flow_data = data.get("flowSegmentData", {})
            
            # Calculate congestion level
            current_speed = flow_data.get("currentSpeed", 0)
            free_flow_speed = flow_data.get("freeFlowSpeed", current_speed)
            
            if free_flow_speed > 0:
                speed_ratio = current_speed / free_flow_speed
                if speed_ratio >= 0.8:
                    condition = "Good"
                    color = "green"
                elif speed_ratio >= 0.5:
                    condition = "Moderate"
                    color = "yellow"
                else:
                    condition = "Congested"
                    color = "red"
            else:
                condition = "Unknown"
                color = "gray"
            
            return {
                "condition": condition,
                "current_speed": current_speed,
                "free_flow_speed": free_flow_speed,
                "confidence": flow_data.get("confidence", 0),
                "color": color
            }
            
    except Exception as e:
        return {
            "condition": "Unknown",
            "current_speed": 0,
            "free_flow_speed": 0,
            "confidence": 0,
            "color": "gray"
        }

async def reverse_geocode(lat, lng, api_key):
    """Get address for coordinates using TomTom Reverse Geocoding"""
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lng}.json"
            params = {"key": api_key, "returnSpeedLimit": "false", "radius": 100}
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data["addresses"]:
                address_data = data["addresses"][0]["address"]
                # Build a nice address string
                parts = []
                if "streetName" in address_data and address_data["streetName"]:
                    parts.append(address_data["streetName"])
                if "municipality" in address_data and address_data["municipality"]:
                    parts.append(address_data["municipality"])
                elif "localName" in address_data and address_data["localName"]:
                    parts.append(address_data["localName"])
                if "countrySubdivision" in address_data and address_data["countrySubdivision"]:
                    parts.append(address_data["countrySubdivision"])
                    
                return ", ".join(parts) if parts else f"Location at {lat:.4f}, {lng:.4f}"
            else:
                return f"Location at {lat:.4f}, {lng:.4f}"
                
    except Exception as e:
        return f"Location at {lat:.4f}, {lng:.4f}"

async def get_weather_forecast(lat, lng, target_time_str, api_key):
    """Get weather forecast for specific location and time"""
    async with httpx.AsyncClient() as client:
        # Convert target time to timestamp for API
        target_time = datetime.fromisoformat(target_time_str.replace('Z', '+00:00'))
        now = datetime.now()
        
        if target_time <= now:
            # Current weather
            url = "http://api.weatherapi.com/v1/current.json"
            params = {
                "key": api_key,
                "q": f"{lat},{lng}",
                "aqi": "no"
            }
        else:
            # Forecast weather (up to 10 days)
            days_ahead = max(1, (target_time - now).days + 1)
            url = "http://api.weatherapi.com/v1/forecast.json"
            params = {
                "key": api_key,
                "q": f"{lat},{lng}",
                "days": min(days_ahead, 10),
                "aqi": "no",
                "alerts": "no"
            }
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if "current" in data:
            # Current weather
            weather = data["current"]
            return {
                "temperature": weather["temp_c"],
                "condition": weather["condition"]["text"],
                "icon": weather["condition"]["icon"],
                "humidity": weather["humidity"],
                "wind_speed": weather["wind_kph"],
                "visibility": weather["vis_km"],
                "forecast_type": "current"
            }
        else:
            # Forecast weather - find closest hour
            target_hour = target_time.hour
            forecast_day = data["forecast"]["forecastday"][0]
            
            # Try to get hourly data for better accuracy
            if "hour" in forecast_day:
                hourly_data = forecast_day["hour"]
                closest_hour = min(hourly_data, 
                                 key=lambda x: abs(int(x["time"].split(" ")[1].split(":")[0]) - target_hour))
                weather = closest_hour
            else:
                weather = forecast_day["day"]
            
            return {
                "temperature": weather.get("temp_c", weather.get("avgtemp_c")),
                "condition": weather["condition"]["text"],
                "icon": weather["condition"]["icon"],
                "humidity": weather.get("humidity", weather.get("avghumidity")),
                "wind_speed": weather.get("wind_kph", weather.get("maxwind_kph")),
                "visibility": weather.get("vis_km", weather.get("avgvis_km")),
                "forecast_type": "forecast"
            }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)