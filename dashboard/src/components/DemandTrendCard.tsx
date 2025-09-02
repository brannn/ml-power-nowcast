'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Minus, Clock, Zap } from 'lucide-react'
import { useTheme } from './ThemeProvider'

interface DemandTrendData {
  zone: string
  current_load: number
  trend_direction: string
  trend_percentage: number
  next_peak_time: string
  next_peak_load: number
  hours_to_peak: number
  is_peak_hours: boolean
  timestamp: string
}

interface DemandTrendCardProps {
  trendData: DemandTrendData | null
  loading?: boolean
}

export default function DemandTrendCard({ trendData, loading }: DemandTrendCardProps) {
  const { theme } = useTheme()

  if (loading || !trendData) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Demand Trend</CardTitle>
          <div className={`p-1.5 rounded-md ${
            theme === 'dark' ? 'bg-blue-900/50' : 'bg-blue-100'
          }`}>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const getTrendIcon = () => {
    switch (trendData.trend_direction) {
      case 'rising':
        return TrendingUp
      case 'falling':
        return TrendingDown
      default:
        return Minus
    }
  }

  const getTrendColor = () => {
    switch (trendData.trend_direction) {
      case 'rising':
        return theme === 'dark' ? 'text-green-400' : 'text-green-600'
      case 'falling':
        return theme === 'dark' ? 'text-red-400' : 'text-red-600'
      default:
        return theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
    }
  }

  const getTrendBadgeColor = () => {
    switch (trendData.trend_direction) {
      case 'rising':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'falling':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200'
    }
  }

  const formatHoursToPeak = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)}m`
    } else if (hours < 24) {
      return `${Math.round(hours)}h`
    } else {
      const days = Math.floor(hours / 24)
      const remainingHours = Math.round(hours % 24)
      return `${days}d ${remainingHours}h`
    }
  }

  const formatPeakTime = (isoString: string) => {
    const date = new Date(isoString)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()
    const isTomorrow = date.toDateString() === new Date(now.getTime() + 24 * 60 * 60 * 1000).toDateString()
    
    const timeStr = date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    })
    
    if (isToday) return `Today ${timeStr}`
    if (isTomorrow) return `Tomorrow ${timeStr}`
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  const TrendIcon = getTrendIcon()

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Demand Trend</CardTitle>
        <div className={`p-1.5 rounded-md ${
          trendData.is_peak_hours 
            ? (theme === 'dark' ? 'bg-orange-900/50' : 'bg-orange-100')
            : (theme === 'dark' ? 'bg-blue-900/50' : 'bg-blue-100')
        }`}>
          <Zap className={`h-4 w-4 ${
            trendData.is_peak_hours ? 'text-orange-600' : 'text-blue-600'
          }`} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Current Trend */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendIcon className={`h-4 w-4 ${getTrendColor()}`} />
            <span className="text-sm font-medium capitalize">
              {trendData.trend_direction}
            </span>
          </div>
          <Badge variant="outline" className={`text-xs ${getTrendBadgeColor()} ${
            theme === 'dark' ? 'bg-opacity-20' : ''
          }`}>
            {trendData.trend_percentage >= 0 ? '+' : ''}{trendData.trend_percentage.toFixed(1)}%
          </Badge>
        </div>

        {/* Peak Prediction */}
        <div className="border-t pt-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className={`h-4 w-4 ${
                theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
              }`} />
              <span className="text-sm font-medium">Next Peak</span>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium">
                {formatHoursToPeak(trendData.hours_to_peak)}
              </div>
              <div className={`text-xs ${
                theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
              }`}>
                {formatPeakTime(trendData.next_peak_time)}
              </div>
            </div>
          </div>
          
          {/* Peak Load Estimate */}
          <div className="mt-2 text-center">
            <div className={`text-xs ${
              theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
            }`}>
              Estimated peak: {(trendData.next_peak_load / 1000).toFixed(1)} GW
            </div>
          </div>
        </div>

        {/* Peak Hours Indicator */}
        {trendData.is_peak_hours && (
          <div className={`text-center py-1 px-2 rounded text-xs font-medium ${
            theme === 'dark' 
              ? 'bg-orange-900/30 text-orange-300' 
              : 'bg-orange-100 text-orange-800'
          }`}>
            🔥 Peak Hours Active
          </div>
        )}
      </CardContent>
    </Card>
  )
}
