'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/components/ThemeProvider'
import {
  Target,
  TrendingUp,
  BarChart3,
  Clock,
  CheckCircle,
  AlertCircle,
  Activity,
  Gauge
} from 'lucide-react'

interface ModelMetrics {
  mae: number
  rmse: number
  r2: number
  mape: number
  last_updated: string
}

interface MetricsGridProps {
  metrics: ModelMetrics | null
  modelInfo?: any
}

export default function MetricsGrid({ metrics, modelInfo }: MetricsGridProps) {
  const { theme } = useTheme()

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <div className="text-center">
          <div className="text-lg font-medium">No metrics available</div>
          <div className="text-sm">Model metrics will appear here once loaded</div>
        </div>
      </div>
    )
  }

  const getPerformanceLevel = (mape: number) => {
    if (mape < 3) return { level: 'Excellent', color: 'bg-green-500', icon: CheckCircle }
    if (mape < 5) return { level: 'Very Good', color: 'bg-blue-500', icon: CheckCircle }
    if (mape < 10) return { level: 'Good', color: 'bg-yellow-500', icon: AlertCircle }
    return { level: 'Needs Improvement', color: 'bg-red-500', icon: AlertCircle }
  }

  const getR2Level = (r2: number) => {
    if (r2 > 0.95) return { level: 'Excellent', color: 'text-green-600' }
    if (r2 > 0.90) return { level: 'Very Good', color: 'text-blue-600' }
    if (r2 > 0.80) return { level: 'Good', color: 'text-yellow-600' }
    return { level: 'Poor', color: 'text-red-600' }
  }

  // Composite performance assessment considering both MAPE and R²
  const getCompositePerformance = (mape: number, r2: number) => {
    const mapeScore = mape < 3 ? 4 : mape < 5 ? 3 : mape < 10 ? 2 : 1
    const r2Score = r2 > 0.95 ? 4 : r2 > 0.90 ? 3 : r2 > 0.80 ? 2 : 1
    const avgScore = (mapeScore + r2Score) / 2

    if (avgScore >= 3.5) return { level: 'Excellent', color: 'bg-green-500', icon: CheckCircle }
    if (avgScore >= 2.5) return { level: 'Very Good', color: 'bg-blue-500', icon: CheckCircle }
    if (avgScore >= 1.5) return { level: 'Good', color: 'bg-yellow-500', icon: AlertCircle }
    return { level: 'Needs Improvement', color: 'bg-red-500', icon: AlertCircle }
  }

  const mapePerformance = getPerformanceLevel(metrics.mape)
  const r2Performance = getR2Level(metrics.r2)
  const performance = getCompositePerformance(metrics.mape, metrics.r2)
  const PerformanceIcon = performance.icon

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="space-y-6">
      {/* Overall Performance Summary */}
      <Card className="border-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${performance.level === 'Excellent' ? 'bg-green-100' : performance.level === 'Very Good' ? 'bg-blue-100' : performance.level === 'Good' ? 'bg-yellow-100' : 'bg-red-100'}`}>
              <PerformanceIcon className={`h-5 w-5 ${performance.level === 'Excellent' ? 'text-green-600' : performance.level === 'Very Good' ? 'text-blue-600' : performance.level === 'Good' ? 'text-yellow-600' : 'text-red-600'}`} />
            </div>
            Model Performance Summary
          </CardTitle>
          <CardDescription>
            Overall assessment of the power demand forecasting model
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div>
                <div className="text-2xl font-bold">{metrics.mape.toFixed(1)}%</div>
                <div className="text-xs text-muted-foreground">MAPE (Real-time)</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{(metrics.r2 * 100).toFixed(1)}%</div>
                <div className="text-xs text-muted-foreground">R² Score</div>
              </div>
            </div>
            <div className="text-right">
              <Badge className={`${performance.color} text-white`}>
                {performance.level}
              </Badge>
              <div className="text-sm text-muted-foreground mt-1">
                Composite Score
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                MAPE: {mapePerformance.level} • R²: {r2Performance.level}
              </div>
            </div>
          </div>

          {/* Model Static Accuracy */}
          {modelInfo && (
            <div className="border-t pt-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-semibold">{modelInfo.accuracy.toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">Model Accuracy (Static)</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">{modelInfo.name}</div>
                  <div className="text-xs text-muted-foreground">v{modelInfo.version}</div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detailed Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Mean Absolute Error */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mean Absolute Error</CardTitle>
            <div className="p-1.5 bg-red-100 rounded-md">
              <Target className="h-4 w-4 text-red-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.mae.toFixed(0)} MW</div>
            <p className="text-xs text-muted-foreground">
              Average prediction error
            </p>
            <div className="mt-2 text-xs">
              <span className="text-muted-foreground">
                Lower is better • Target: &lt;500 MW
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Root Mean Square Error */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Root Mean Square Error</CardTitle>
            <div className="p-1.5 bg-orange-100 rounded-md">
              <BarChart3 className="h-4 w-4 text-orange-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.rmse.toFixed(0)} MW</div>
            <p className="text-xs text-muted-foreground">
              Penalizes large errors more
            </p>
            <div className="mt-2 text-xs">
              <span className="text-muted-foreground">
                Lower is better • Target: &lt;800 MW
              </span>
            </div>
          </CardContent>
        </Card>

        {/* R-squared Score */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">R² Score</CardTitle>
            <div className="p-1.5 bg-green-100 rounded-md">
              <TrendingUp className="h-4 w-4 text-green-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.r2.toFixed(3)}</div>
            <p className="text-xs text-muted-foreground">
              Variance explained by model
            </p>
            <div className="mt-2 text-xs">
              <span className={r2Performance.color}>
                {r2Performance.level} • {(metrics.r2 * 100).toFixed(1)}% explained
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Last Updated */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Updated</CardTitle>
            <div className="p-1.5 bg-blue-100 rounded-md">
              <Clock className="h-4 w-4 text-blue-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">
              {formatDate(metrics.last_updated).split(',')[1]?.trim() || 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatDate(metrics.last_updated).split(',')[0]}
            </p>
            <div className="mt-2 text-xs">
              <span className="text-muted-foreground">
                Model training time
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Interpretation */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Interpretation</CardTitle>
          <CardDescription>
            What these metrics mean for power demand forecasting operations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold mb-2">Accuracy Assessment</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    theme === 'dark' ? 'bg-blue-400' : 'bg-blue-500'
                  }`}></div>
                  <span>
                    <strong>MAPE {metrics.mape.toFixed(1)}%:</strong> This model predicts within {metrics.mape.toFixed(1)}% of actual demand on average
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    theme === 'dark' ? 'bg-green-400' : 'bg-green-500'
                  }`}></div>
                  <span>
                    <strong>MAE {metrics.mae.toFixed(0)} MW:</strong> Typical prediction error is ±{metrics.mae.toFixed(0)} MW
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    theme === 'dark' ? 'bg-purple-400' : 'bg-purple-500'
                  }`}></div>
                  <span>
                    <strong>R² {metrics.r2.toFixed(3)}:</strong> Model explains {(metrics.r2 * 100).toFixed(1)}% of demand variation
                  </span>
                </li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-2">Business Impact</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    theme === 'dark' ? 'bg-yellow-400' : 'bg-yellow-500'
                  }`}></div>
                  <span>
                    Grid operators can rely on predictions for capacity planning
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    theme === 'dark' ? 'bg-red-400' : 'bg-red-500'
                  }`}></div>
                  <span>
                    Accurate forecasts help prevent blackouts and optimize costs
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    theme === 'dark' ? 'bg-indigo-400' : 'bg-indigo-500'
                  }`}></div>
                  <span>
                    {performance.level.toLowerCase()} performance enables real-time operations
                  </span>
                </li>
              </ul>
            </div>
          </div>

          {/* Performance Benchmarks */}
          <div className="border-t pt-4">
            <h4 className="font-semibold mb-2">Industry Benchmarks</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className={`text-center p-3 rounded-lg border ${
                theme === 'dark'
                  ? 'bg-green-900/20 border-green-800/30'
                  : 'bg-green-50 border-green-200'
              }`}>
                <div className={`font-semibold ${
                  theme === 'dark' ? 'text-green-300' : 'text-green-700'
                }`}>Excellent</div>
                <div className={`${
                  theme === 'dark' ? 'text-green-400' : 'text-green-600'
                }`}>MAPE &lt; 3%</div>
                <div className={`text-xs mt-1 ${
                  theme === 'dark' ? 'text-green-500' : 'text-green-500'
                }`}>Research-grade accuracy</div>
              </div>
              <div className={`text-center p-3 rounded-lg border ${
                theme === 'dark'
                  ? 'bg-blue-900/20 border-blue-800/30'
                  : 'bg-blue-50 border-blue-200'
              }`}>
                <div className={`font-semibold ${
                  theme === 'dark' ? 'text-blue-300' : 'text-blue-700'
                }`}>Production Ready</div>
                <div className={`${
                  theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
                }`}>MAPE 3-5%</div>
                <div className={`text-xs mt-1 ${
                  theme === 'dark' ? 'text-blue-500' : 'text-blue-500'
                }`}>Commercial deployment</div>
              </div>
              <div className={`text-center p-3 rounded-lg border ${
                theme === 'dark'
                  ? 'bg-yellow-900/20 border-yellow-800/30'
                  : 'bg-yellow-50 border-yellow-200'
              }`}>
                <div className={`font-semibold ${
                  theme === 'dark' ? 'text-yellow-300' : 'text-yellow-700'
                }`}>Acceptable</div>
                <div className={`${
                  theme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
                }`}>MAPE 5-10%</div>
                <div className={`text-xs mt-1 ${
                  theme === 'dark' ? 'text-yellow-500' : 'text-yellow-500'
                }`}>Operational with monitoring</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
