import React, { useState } from 'react';
import './App.css';

function App() {
  const [formData, setFormData] = useState({
    source: '',
    destination: '',
    transportMode: 'driving',
    startTime: '',
    tomtomApiKey: '',
    weatherApiKey: ''
  });
  
  const [routeData, setRouteData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const transportModes = [
    { value: 'driving', label: 'Driving 🚗', icon: '🚗' },
    { value: 'walking', label: 'Walking 🚶', icon: '🚶' },
    { value: 'cycling', label: 'Cycling 🚴', icon: '🚴' },
    { value: 'transit', label: 'Transit 🚌', icon: '🚌' }
  ];

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/calculate-route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source: formData.source,
          destination: formData.destination,
          transport_mode: formData.transportMode,
          start_time: formData.startTime,
          tomtom_api_key: formData.tomtomApiKey,
          weather_api_key: formData.weatherApiKey
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to calculate route');
      }

      const data = await response.json();
      setRouteData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatDistance = (meters) => {
    const km = (meters / 1000).toFixed(1);
    return `${km} km`;
  };

  const getWeatherIcon = (iconUrl) => {
    return iconUrl.startsWith('//') ? `https:${iconUrl}` : iconUrl;
  };

  const formatTime = (isoString) => {
    return new Date(isoString).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getCurrentDateTime = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-800 mb-4">
            🌤️ Weather Route Planner
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Plan your journey and see exactly what weather conditions you'll encounter 
            when you reach each point along your route
          </p>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {/* API Keys Section */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8 border border-gray-200">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4 flex items-center">
              🔑 API Configuration
            </h2>
            <p className="text-gray-600 mb-4">
              Enter your API keys to enable routing and weather services:
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  TomTom API Key
                </label>
                <input
                  type="password"
                  name="tomtomApiKey"
                  value={formData.tomtomApiKey}
                  onChange={handleInputChange}
                  placeholder="Get free key at developer.tomtom.com"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  WeatherAPI Key
                </label>
                <input
                  type="password"
                  name="weatherApiKey"
                  value={formData.weatherApiKey}
                  onChange={handleInputChange}
                  placeholder="Get free key at weatherapi.com"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>
            </div>
          </div>

          {/* Route Planning Form */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8 border border-gray-200">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center">
              🗺️ Plan Your Route
            </h2>
            
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Source and Destination */}
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Starting Location
                  </label>
                  <input
                    type="text"
                    name="source"
                    value={formData.source}
                    onChange={handleInputChange}
                    placeholder="Enter starting address or city"
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Destination
                  </label>
                  <input
                    type="text"
                    name="destination"
                    value={formData.destination}
                    onChange={handleInputChange}
                    placeholder="Enter destination address or city"
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              {/* Transport Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Mode of Transport
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {transportModes.map((mode) => (
                    <label
                      key={mode.value}
                      className={`cursor-pointer p-4 border-2 rounded-lg text-center transition-all ${
                        formData.transportMode === mode.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="transportMode"
                        value={mode.value}
                        checked={formData.transportMode === mode.value}
                        onChange={handleInputChange}
                        className="hidden"
                      />
                      <div className="text-2xl mb-2">{mode.icon}</div>
                      <div className="text-sm font-medium">{mode.label.split(' ')[0]}</div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Start Time */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Departure Time
                </label>
                <input
                  type="datetime-local"
                  name="startTime"
                  value={formData.startTime}
                  onChange={handleInputChange}
                  min={getCurrentDateTime()}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading || !formData.tomtomApiKey || !formData.weatherApiKey}
                className={`w-full py-4 px-6 rounded-lg font-semibold text-lg transition-all transform ${
                  loading || !formData.tomtomApiKey || !formData.weatherApiKey
                    ? 'bg-gray-400 text-gray-600 cursor-not-allowed opacity-50'
                    : 'bg-gradient-to-r from-blue-600 to-green-600 text-white hover:from-blue-700 hover:to-green-700 hover:scale-105'
                }`}
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                    Calculating Route...
                  </div>
                ) : (
                  '🚀 Plan My Weather Journey'
                )}
              </button>
            </form>

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700 font-medium">❌ {error}</p>
              </div>
            )}
          </div>

          {/* Results */}
          {routeData && (
            <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
              <h2 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center">
                📊 Your Weather Journey
              </h2>

              {/* Trip Summary */}
              <div className="bg-gradient-to-r from-blue-50 to-green-50 rounded-lg p-6 mb-6">
                <div className="grid md:grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-blue-600">
                      {formatDuration(routeData.total_duration)}
                    </div>
                    <div className="text-gray-600">Total Duration</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-green-600">
                      {formatDistance(routeData.total_distance)}
                    </div>
                    <div className="text-gray-600">Total Distance</div>
                  </div>
                  <div>
                    <div className="text-2xl">
                      {transportModes.find(m => m.value === routeData.transport_mode)?.icon}
                    </div>
                    <div className="text-gray-600 capitalize">{routeData.transport_mode}</div>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div className="space-y-4">
                {routeData.points.map((point, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                    <div className="flex items-start space-x-4">
                      {/* Timeline indicator */}
                      <div className="flex flex-col items-center">
                        <div className={`w-4 h-4 rounded-full ${
                          point.point_type === 'start' ? 'bg-green-500' : 
                          point.point_type === 'destination' ? 'bg-red-500' : 
                          'bg-blue-500'
                        }`}></div>
                        {index < routeData.points.length - 1 && (
                          <div className="w-0.5 h-12 bg-gray-300 mt-2"></div>
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1">
                        <div className="flex flex-col md:flex-row md:items-center md:justify-between">
                          <div className="mb-4 md:mb-0">
                            <h3 className="text-lg font-semibold text-gray-800">
                              {point.point_type === 'start' ? '🏁 Start' : 
                               point.point_type === 'destination' ? '🏁 Destination' : 
                               `📍 Checkpoint ${index}`}
                            </h3>
                            <p className="text-gray-600">{point.address}</p>
                            <p className="text-sm text-blue-600 font-medium">
                              {point.point_type === 'start' ? 'Departure time' : 'Estimated arrival'}: {formatTime(point.estimated_time)}
                            </p>
                            <p className="text-xs text-gray-500">
                              📍 {point.lat.toFixed(4)}, {point.lng.toFixed(4)}
                            </p>
                          </div>

                          {/* Weather */}
                          <div className="bg-gray-50 rounded-lg p-4 min-w-[200px]">
                            <div className="flex items-center space-x-3">
                              <img 
                                src={getWeatherIcon(point.weather.icon)} 
                                alt={point.weather.condition}
                                className="w-12 h-12"
                              />
                              <div>
                                <div className="text-2xl font-bold text-gray-800">
                                  {Math.round(point.weather.temperature)}°C
                                </div>
                                <div className="text-sm text-gray-600">
                                  {point.weather.condition}
                                </div>
                              </div>
                            </div>
                            
                            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600">
                              <div>💧 {point.weather.humidity}%</div>
                              <div>💨 {Math.round(point.weather.wind_speed)} km/h</div>
                              <div>👁️ {point.weather.visibility} km</div>
                              <div className="text-blue-500">
                                {point.weather.forecast_type === 'current' ? '🕐 Current' : '📅 Forecast'}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;