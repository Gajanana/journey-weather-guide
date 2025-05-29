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
        timeline_points = generate_timeline_points(
            route_data, request.start_time, request.transport_mode
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
            transport_mode=request.transport_mode
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

def generate_timeline_points(route_data, start_time_str, transport_mode):
    """Generate points along the route with estimated arrival times"""
    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    total_duration = route_data["total_duration"]
    
    # Create timeline points (every 30 minutes or major waypoints)
    points = []
    num_points = min(10, max(3, total_duration // 1800))  # Every 30 min, max 10 points
    
    for i in range(num_points):
        progress = i / (num_points - 1) if num_points > 1 else 0
        time_offset = int(total_duration * progress)
        estimated_time = start_time + timedelta(seconds=time_offset)
        
        # For now, interpolate coordinates (in real implementation, use actual route points)
        # This is a simplified approach - in production you'd use actual route geometry
        points.append({
            "lat": 40.7128 + (progress * 0.5),  # Placeholder coordinates
            "lng": -74.0060 + (progress * 0.5),  # Placeholder coordinates
            "address": f"Point {i+1} along route",
            "estimated_time": estimated_time.isoformat()
        })
    
    return points

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