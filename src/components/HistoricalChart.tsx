'use client'

import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface HistoricalDataPoint {
  timestamp: string
  actual_load: number
  predicted_load: number
  temperature: number
  humidity: number
}

interface HistoricalChartProps {
  apiBase: string
}

export default function HistoricalChart({ apiBase }: HistoricalChartProps) {
  const [historicalData, setHistoricalData] = useState<HistoricalDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHistoricalData = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const response = await fetch(`${apiBase}/historical?days=7`)
        if (!response.ok) {
          throw new Error(`Failed to fetch historical data: ${response.status}`)
        }
        
        const data = await response.json()
        setHistoricalData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load historical data')
      } finally {
        setLoading(false)
      }
    }

    fetchHistoricalData()
  }, [apiBase])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <div className="mt-2 text-sm text-muted-foreground">Loading historical data...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-600">
        <div className="text-center">
          <div className="text-lg font-medium">Error loading data</div>
          <div className="text-sm">{error}</div>
        </div>
      </div>
    )
  }

  if (!historicalData || historicalData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <div className="text-center">
          <div className="text-lg font-medium">No historical data available</div>
          <div className="text-sm">Historical data will appear here once available</div>
        </div>
      </div>
    )
  }

  // Prepare data for Chart.js
  const labels = historicalData.map(point => {
    const date = new Date(point.timestamp)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit'
    })
  })

  const actualData = historicalData.map(point => point.actual_load)
  const predictedData = historicalData.map(point => point.predicted_load)

  const data = {
    labels,
    datasets: [
      {
        label: 'Actual Demand',
        data: actualData,
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgb(34, 197, 94)',
        pointBorderColor: 'white',
        pointBorderWidth: 2,
        pointRadius: 3,
        tension: 0.4,
      },
      {
        label: 'Predicted Demand',
        data: predictedData,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: 'white',
        pointBorderWidth: 2,
        pointRadius: 3,
        tension: 0.4,
        borderDash: [5, 5],
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
      title: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgba(59, 130, 246, 0.5)',
        borderWidth: 1,
        callbacks: {
          label: function(context: any) {
            const datasetLabel = context.dataset.label
            const value = context.parsed.y
            return `${datasetLabel}: ${value.toFixed(0)} MW`
          },
          afterBody: function(tooltipItems: any[]) {
            const index = tooltipItems[0].dataIndex
            const point = historicalData[index]
            const error = Math.abs(point.actual_load - point.predicted_load)
            const errorPercent = (error / point.actual_load) * 100
            
            return [
              '',
              `Error: ${error.toFixed(0)} MW (${errorPercent.toFixed(1)}%)`,
              `Temperature: ${point.temperature.toFixed(1)}°C`,
              `Humidity: ${point.humidity.toFixed(0)}%`
            ]
          }
        }
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time',
          font: {
            size: 14,
            weight: 'bold',
          },
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          maxTicksLimit: 12,
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Power Demand (MW)',
          font: {
            size: 14,
            weight: 'bold',
          },
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        ticks: {
          callback: function(value: any) {
            return `${value.toLocaleString()} MW`
          },
        },
      },
    },
    elements: {
      point: {
        hoverRadius: 6,
      },
    },
    animation: {
      duration: 1000,
      easing: 'easeInOutQuart',
    },
  }

  // Calculate some statistics
  const errors = historicalData.map(point => 
    Math.abs(point.actual_load - point.predicted_load)
  )
  const meanError = errors.reduce((sum, error) => sum + error, 0) / errors.length
  const maxError = Math.max(...errors)
  const minError = Math.min(...errors)

  return (
    <div className="space-y-4">
      <div className="h-80 w-full">
        <Line data={data} options={options} />
      </div>
      
      {/* Performance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{meanError.toFixed(0)} MW</div>
          <div className="text-sm text-muted-foreground">Average Error</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{maxError.toFixed(0)} MW</div>
          <div className="text-sm text-muted-foreground">Maximum Error</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">{minError.toFixed(0)} MW</div>
          <div className="text-sm text-muted-foreground">Minimum Error</div>
        </div>
      </div>
    </div>
  )
}
