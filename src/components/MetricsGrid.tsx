'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Target, 
  TrendingUp, 
  BarChart3, 
  Clock,
  CheckCircle,
  AlertCircle
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
}

export default function MetricsGrid({ metrics }: MetricsGridProps) {
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

  const performance = getPerformanceLevel(metrics.mape)
  const r2Performance = getR2Level(metrics.r2)
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
            <PerformanceIcon className="h-5 w-5" />
            Model Performance Summary
          </CardTitle>
          <CardDescription>
            Overall assessment of your power demand forecasting model
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold">{metrics.mape.toFixed(1)}%</div>
              <div className="text-sm text-muted-foreground">Mean Absolute Percentage Error</div>
            </div>
            <div className="text-right">
              <Badge className={`${performance.color} text-white`}>
                {performance.level}
              </Badge>
              <div className="text-sm text-muted-foreground mt-1">
                Performance Level
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Mean Absolute Error */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mean Absolute Error</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
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
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
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
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
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
            <Clock className="h-4 w-4 text-muted-foreground" />
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
            What these metrics mean for your power demand forecasting
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold mb-2">Accuracy Assessment</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 flex-shrink-0"></div>
                  <span>
                    <strong>MAPE {metrics.mape.toFixed(1)}%:</strong> Your model predicts within {metrics.mape.toFixed(1)}% of actual demand on average
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0"></div>
                  <span>
                    <strong>MAE {metrics.mae.toFixed(0)} MW:</strong> Typical prediction error is ±{metrics.mae.toFixed(0)} MW
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500 mt-1.5 flex-shrink-0"></div>
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
                  <div className="w-2 h-2 rounded-full bg-yellow-500 mt-1.5 flex-shrink-0"></div>
                  <span>
                    Grid operators can rely on predictions for capacity planning
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500 mt-1.5 flex-shrink-0"></div>
                  <span>
                    Accurate forecasts help prevent blackouts and optimize costs
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5 flex-shrink-0"></div>
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
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <div className="font-semibold text-green-700">Excellent</div>
                <div className="text-green-600">MAPE &lt; 3%</div>
                <div className="text-xs text-green-500 mt-1">Research-grade accuracy</div>
              </div>
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <div className="font-semibold text-blue-700">Production Ready</div>
                <div className="text-blue-600">MAPE 3-5%</div>
                <div className="text-xs text-blue-500 mt-1">Commercial deployment</div>
              </div>
              <div className="text-center p-3 bg-yellow-50 rounded-lg">
                <div className="font-semibold text-yellow-700">Acceptable</div>
                <div className="text-yellow-600">MAPE 5-10%</div>
                <div className="text-xs text-yellow-500 mt-1">Operational with monitoring</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
