'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Zap,
  TrendingUp,
  Thermometer,
  Wind,
  Droplets,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Activity,
  BarChart3,
  Clock,
  Database,
  Settings,
  Wifi,
  WifiOff,
  Sun,
  Moon,
  Gauge
} from 'lucide-react'
import PredictionChart from '@/components/PredictionChart'
import HistoricalChart from '@/components/HistoricalChart'
import MetricsGrid from '@/components/MetricsGrid'
import DemandTrendCard from '@/components/DemandTrendCard'
import ModelSelector from '@/components/ModelSelector'
import { useTheme } from '@/components/ThemeProvider'
import { useUnits } from '@/components/UnitsProvider'
import { useRegional } from '@/components/RegionalProvider'
import RegionalSelector from '@/components/RegionalSelector'
import Toggle from '@/components/ui/toggle'

interface PredictionPoint {
  timestamp: string
  predicted_load: number
  confidence_lower: number
  confidence_upper: number
  hour_ahead: number
}

interface SystemStatus {
  status: string
  last_prediction: string
  model_accuracy: number
  data_freshness: string
  alerts: string[]
}

interface ModelMetrics {
  mae: number
  rmse: number
  r2: number
  mape: number
  last_updated: string
}

export default function Dashboard() {
  const [predictions, setPredictions] = useState<PredictionPoint[]>([])
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [modelMetrics, setModelMetrics] = useState<any>(null)
  const [currentWeather, setCurrentWeather] = useState<any>(null)
  const [demandTrend, setDemandTrend] = useState<ModelMetrics | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('xgboost')
  const [currentModelInfo, setCurrentModelInfo] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Use context providers
  const { theme, toggleTheme } = useTheme()
  const { unitSystem, toggleUnits, formatTemperature, formatWindSpeed } = useUnits()
  const { selectedZone, currentZone, isStatewide } = useRegional()
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Configuration for API endpoint
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

  const fetchPredictions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Use real current weather conditions for the selected zone
      const weatherData = {
        temperature: currentWeather?.temperature || 28.5,
        humidity: currentWeather?.humidity || 65,
        wind_speed: currentWeather?.wind_speed || 3.2,
        zone: selectedZone,
        region_info: {
          name: currentZone.name,
          full_name: currentZone.full_name,
          major_city: currentZone.major_city,
          climate_region: currentZone.climate_region,
          load_weight: currentZone.load_weight
        }
      }

      const response = await fetch(`${API_BASE}/predict?model_id=${selectedModel}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(weatherData)
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data = await response.json()
      setPredictions(data)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch predictions')
    } finally {
      setLoading(false)
    }
  }

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/status?zone=${selectedZone}&model_id=${selectedModel}`)
      if (response.ok) {
        const data = await response.json()
        setSystemStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch system status:', err)
    }
  }

  const fetchModelMetrics = async () => {
    try {
      const response = await fetch(`${API_BASE}/metrics?zone=${selectedZone}&model_id=${selectedModel}`)
      if (response.ok) {
        const data = await response.json()
        setModelMetrics(data)
      }
    } catch (err) {
      console.error('Failed to fetch model metrics:', err)
    }
  }

  const fetchCurrentWeather = async () => {
    try {
      const response = await fetch(`${API_BASE}/weather/${selectedZone}`)
      if (response.ok) {
        const data = await response.json()
        setCurrentWeather(data)
      }
    } catch (err) {
      console.error('Failed to fetch current weather:', err)
    }
  }

  const fetchDemandTrend = async () => {
    try {
      const response = await fetch(`${API_BASE}/trend/${selectedZone}`)
      if (response.ok) {
        const data = await response.json()
        setDemandTrend(data)
      }
    } catch (err) {
      console.error('Failed to fetch demand trend:', err)
    }
  }

  const fetchCurrentModelInfo = async () => {
    try {
      const response = await fetch(`${API_BASE}/models/current`)
      if (response.ok) {
        const data = await response.json()
        setCurrentModelInfo(data.model_info)
      }
    } catch (err) {
      console.error('Failed to fetch current model info:', err)
    }
  }

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId)
    // Immediately fetch new data with the selected model
    fetchPredictions()
    fetchModelMetrics()
    fetchSystemStatus()
    fetchCurrentModelInfo()
  }

  useEffect(() => {
    // Initial data fetch
    fetchPredictions()
    fetchSystemStatus()
    fetchModelMetrics()
    fetchCurrentWeather()
    fetchDemandTrend()
    fetchCurrentModelInfo()

    // Set up auto-refresh every 5 minutes
    const interval = setInterval(() => {
      fetchPredictions()
      fetchSystemStatus()
      fetchCurrentWeather()
      fetchDemandTrend()
    }, 5 * 60 * 1000)

    return () => clearInterval(interval)
  }, [selectedZone, selectedModel]) // Re-fetch when region or model changes

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational': return 'bg-green-500'
      case 'warning': return 'bg-yellow-500'
      case 'error': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const currentLoad = predictions.length > 0 ? predictions[0].predicted_load : 0
  const peakLoad = predictions.length > 0 ? Math.max(...predictions.map(p => p.predicted_load)) : 0

  return (
    <div className={`min-h-screen transition-colors duration-300 p-4 ${
      theme === 'dark'
        ? 'bg-gradient-to-br from-slate-900 to-slate-800 text-white'
        : 'bg-gradient-to-br from-slate-50 to-slate-100 text-slate-900'
    }`}>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={`text-4xl font-bold flex items-center gap-3 ${
                theme === 'dark' ? 'text-white' : 'text-slate-900'
              }`}>
                <div className={`p-2 rounded-lg ${
                  theme === 'dark' ? 'bg-blue-900/50' : 'bg-blue-100'
                }`}>
                  <Activity className="h-6 w-6 text-blue-600" />
                </div>
                The Grid Ahead
              </h1>
              <p className={`mt-2 text-base ${
                theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
              }`}>
                Predicting power demand on the California Independent System Operator (CAISO) with ML
              </p>
            </div>
          </div>
          

          {/* Controls Section - Under Title */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Regional Selector */}
            <RegionalSelector />

            {/* Model Selector */}
            <ModelSelector
              onModelChange={handleModelChange}
            />

            {/* Unit Toggle */}
            <Toggle
              leftLabel="Metric"
              rightLabel="Imperial"
              isRight={unitSystem === 'imperial'}
              onToggle={toggleUnits}
            />

            {/* Theme Toggle */}
            <Toggle
              leftLabel="Light"
              rightLabel="Dark"
              isRight={theme === 'dark'}
              onToggle={toggleTheme}
            />
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {systemStatus?.alerts && systemStatus.alerts.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {systemStatus.alerts.join(', ')}
            </AlertDescription>
          </Alert>
        )}

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Current Demand</CardTitle>
              <div className={`p-1.5 rounded-md ${
                theme === 'dark' ? 'bg-blue-900/50' : 'bg-blue-100'
              }`}>
                <Zap className="h-4 w-4 text-blue-600" />
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-2xl font-bold">{currentLoad.toFixed(0)} MW</div>
              <p className="text-xs text-muted-foreground">
                Next hour prediction
              </p>
              <div className="border-t pt-2">
                <div className="text-sm font-medium">
                  {((currentLoad / 1000)).toFixed(1)} GW
                </div>
                <div className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                }`}>
                  Gigawatt equivalent
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">6-Hour Peak</CardTitle>
              <div className={`p-1.5 rounded-md ${
                theme === 'dark' ? 'bg-green-900/50' : 'bg-green-100'
              }`}>
                <TrendingUp className="h-4 w-4 text-green-600" />
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-2xl font-bold">{peakLoad.toFixed(0)} MW</div>
              <p className="text-xs text-muted-foreground">
                Maximum expected demand
              </p>
              <div className="border-t pt-2">
                <div className="text-sm font-medium">
                  +{((peakLoad - currentLoad) / currentLoad * 100).toFixed(1)}%
                </div>
                <div className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                }`}>
                  Above current demand
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Model Accuracy</CardTitle>
              <div className={`p-1.5 rounded-md ${
                theme === 'dark' ? 'bg-purple-900/50' : 'bg-purple-100'
              }`}>
                <BarChart3 className="h-4 w-4 text-purple-600" />
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="text-2xl font-bold">
                {modelMetrics ? `${modelMetrics.mape.toFixed(1)}%` : 'N/A'}
              </div>
              <p className="text-xs text-muted-foreground">
                Mean absolute error
              </p>
              <div className="border-t pt-2">
                <div className="text-sm font-medium">
                  {modelMetrics ? `${(modelMetrics.r2 * 100).toFixed(1)}%` : 'N/A'}
                </div>
                <div className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                }`}>
                  R² variance explained
                </div>
              </div>
            </CardContent>
          </Card>

          <DemandTrendCard
            trendData={demandTrend}
            loading={loading}
          />
        </div>

        {/* Main Dashboard */}
        <Tabs defaultValue="predictions" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="predictions" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Live Predictions
            </TabsTrigger>
            <TabsTrigger value="historical" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Historical Data
            </TabsTrigger>
            <TabsTrigger value="metrics" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Model Performance
            </TabsTrigger>
          </TabsList>

          <TabsContent value="predictions" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Prediction Chart */}
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <div className="p-1.5 bg-blue-100 rounded-md">
                        <TrendingUp className="h-4 w-4 text-blue-600" />
                      </div>
                      6-Hour Demand Forecast
                    </CardTitle>
                    <CardDescription>
                      Predicted power demand with confidence intervals
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <PredictionChart predictions={predictions} />
                  </CardContent>
                </Card>
              </div>

              {/* Prediction Details */}
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <div className="p-1.5 bg-slate-100 rounded-md">
                        <Settings className="h-4 w-4 text-slate-600" />
                      </div>
                      Current Conditions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className={`flex items-center justify-between p-3 rounded-lg border ${
                      theme === 'dark'
                        ? 'bg-orange-900/20 border-orange-800/30'
                        : 'bg-orange-50 border-orange-200'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-md ${
                          theme === 'dark' ? 'bg-orange-900/40' : 'bg-orange-100'
                        }`}>
                          <Thermometer className="h-4 w-4 text-orange-600" />
                        </div>
                        <span className="text-sm font-medium">Temperature</span>
                      </div>
                      <Badge variant="secondary" className={`${
                        theme === 'dark'
                          ? 'bg-orange-900/40 text-orange-300 border-orange-800'
                          : 'bg-orange-100 text-orange-800'
                      }`}>
                        {currentWeather ? formatTemperature(currentWeather.temperature) : formatTemperature(28.5)}
                      </Badge>
                    </div>

                    <div className={`flex items-center justify-between p-3 rounded-lg border ${
                      theme === 'dark'
                        ? 'bg-blue-900/20 border-blue-800/30'
                        : 'bg-blue-50 border-blue-200'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-md ${
                          theme === 'dark' ? 'bg-blue-900/40' : 'bg-blue-100'
                        }`}>
                          <Droplets className="h-4 w-4 text-blue-600" />
                        </div>
                        <span className="text-sm font-medium">Humidity</span>
                      </div>
                      <Badge variant="secondary" className={`${
                        theme === 'dark'
                          ? 'bg-blue-900/40 text-blue-300 border-blue-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {currentWeather ? `${currentWeather.humidity.toFixed(0)}%` : '65%'}
                      </Badge>
                    </div>

                    <div className={`flex items-center justify-between p-3 rounded-lg border ${
                      theme === 'dark'
                        ? 'bg-green-900/20 border-green-800/30'
                        : 'bg-green-50 border-green-200'
                    }`}>
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-md ${
                          theme === 'dark' ? 'bg-green-900/40' : 'bg-green-100'
                        }`}>
                          <Wind className="h-4 w-4 text-green-600" />
                        </div>
                        <span className="text-sm font-medium">Wind Speed</span>
                      </div>
                      <Badge variant="secondary" className={`${
                        theme === 'dark'
                          ? 'bg-green-900/40 text-green-300 border-green-800'
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {currentWeather ? formatWindSpeed(currentWeather.wind_speed) : formatWindSpeed(3.2)}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Hourly Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {predictions.slice(0, 6).map((pred, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">
                            +{pred.hour_ahead}h ({formatTime(pred.timestamp)})
                          </span>
                          <span className="font-medium">
                            {pred.predicted_load.toFixed(0)} MW
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="historical">
            <Card>
              <CardHeader>
                <CardTitle>Historical Performance</CardTitle>
                <CardDescription>
                  Actual vs predicted demand over the past week
                </CardDescription>
              </CardHeader>
              <CardContent>
                <HistoricalChart apiBase={API_BASE} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="metrics">
            <MetricsGrid metrics={modelMetrics} modelInfo={currentModelInfo} />
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="text-center text-sm text-muted-foreground">
          {lastUpdate && (
            <p>Last updated: {lastUpdate.toLocaleString()}</p>
          )}
          <p className="mt-1">
            © 2025 Brandon Huey
          </p>
        </div>
      </div>
    </div>
  )
}
