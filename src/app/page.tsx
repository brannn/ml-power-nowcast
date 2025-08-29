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
  RefreshCw
} from 'lucide-react'
import PredictionChart from '@/components/PredictionChart'
import HistoricalChart from '@/components/HistoricalChart'
import MetricsGrid from '@/components/MetricsGrid'

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
  const [modelMetrics, setModelMetrics] = useState<ModelMetrics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Configuration for API endpoint
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchPredictions = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Simulate current weather conditions (in production, this would come from weather API)
      const weatherData = {
        temperature: 28.5,
        humidity: 65,
        wind_speed: 3.2
      }

      const response = await fetch(`${API_BASE}/predict`, {
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
      const response = await fetch(`${API_BASE}/status`)
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
      const response = await fetch(`${API_BASE}/metrics`)
      if (response.ok) {
        const data = await response.json()
        setModelMetrics(data)
      }
    } catch (err) {
      console.error('Failed to fetch model metrics:', err)
    }
  }

  useEffect(() => {
    // Initial data fetch
    fetchPredictions()
    fetchSystemStatus()
    fetchModelMetrics()

    // Set up auto-refresh every 5 minutes
    const interval = setInterval(() => {
      fetchPredictions()
      fetchSystemStatus()
    }, 5 * 60 * 1000)

    return () => clearInterval(interval)
  }, [])

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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 flex items-center gap-3">
              <Zap className="h-10 w-10 text-blue-600" />
              California Power Demand Forecast
            </h1>
            <p className="text-slate-600 mt-2">Real-time ML-powered electricity demand predictions</p>
          </div>
          
          <div className="flex items-center gap-4">
            {systemStatus && (
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${getStatusColor(systemStatus.status)}`} />
                <span className="text-sm font-medium capitalize">{systemStatus.status}</span>
              </div>
            )}
            
            <Button 
              onClick={fetchPredictions} 
              disabled={loading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
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
              <Zap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{currentLoad.toFixed(0)} MW</div>
              <p className="text-xs text-muted-foreground">
                Next hour prediction
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">6-Hour Peak</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{peakLoad.toFixed(0)} MW</div>
              <p className="text-xs text-muted-foreground">
                Maximum expected demand
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Model Accuracy</CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {modelMetrics ? `${modelMetrics.mape.toFixed(1)}%` : 'N/A'}
              </div>
              <p className="text-xs text-muted-foreground">
                Mean absolute error
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
              <div className={`w-3 h-3 rounded-full ${systemStatus ? getStatusColor(systemStatus.status) : 'bg-gray-500'}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold capitalize">
                {systemStatus?.status || 'Unknown'}
              </div>
              <p className="text-xs text-muted-foreground">
                System operational status
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Dashboard */}
        <Tabs defaultValue="predictions" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="predictions">Live Predictions</TabsTrigger>
            <TabsTrigger value="historical">Historical Data</TabsTrigger>
            <TabsTrigger value="metrics">Model Performance</TabsTrigger>
          </TabsList>

          <TabsContent value="predictions" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Prediction Chart */}
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle>6-Hour Demand Forecast</CardTitle>
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
                    <CardTitle>Current Conditions</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Thermometer className="h-4 w-4 text-orange-500" />
                        <span className="text-sm">Temperature</span>
                      </div>
                      <Badge variant="secondary">28.5°C</Badge>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Droplets className="h-4 w-4 text-blue-500" />
                        <span className="text-sm">Humidity</span>
                      </div>
                      <Badge variant="secondary">65%</Badge>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Wind className="h-4 w-4 text-gray-500" />
                        <span className="text-sm">Wind Speed</span>
                      </div>
                      <Badge variant="secondary">3.2 m/s</Badge>
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
            <MetricsGrid metrics={modelMetrics} />
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <div className="text-center text-sm text-muted-foreground">
          {lastUpdate && (
            <p>Last updated: {lastUpdate.toLocaleString()}</p>
          )}
          <p className="mt-1">
            Powered by ML models running on M4 Mac Mini • Dashboard hosted on Fly.io
          </p>
        </div>
      </div>
    </div>
  )
}
