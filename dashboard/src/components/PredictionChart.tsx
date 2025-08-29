'use client'

import { useEffect, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface PredictionPoint {
  timestamp: string
  predicted_load: number
  confidence_lower: number
  confidence_upper: number
  hour_ahead: number
}

interface PredictionChartProps {
  predictions: PredictionPoint[]
}

export default function PredictionChart({ predictions }: PredictionChartProps) {
  const chartRef = useRef<ChartJS<'line'>>(null)

  if (!predictions || predictions.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <div className="text-center">
          <div className="text-lg font-medium">No prediction data available</div>
          <div className="text-sm">Click refresh to load predictions</div>
        </div>
      </div>
    )
  }

  // Prepare data for Chart.js
  const labels = predictions.map(p => {
    const date = new Date(p.timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  })

  const predictedData = predictions.map(p => p.predicted_load)
  const confidenceLower = predictions.map(p => p.confidence_lower)
  const confidenceUpper = predictions.map(p => p.confidence_upper)

  const data = {
    labels,
    datasets: [
      {
        label: 'Predicted Demand',
        data: predictedData,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 3,
        pointBackgroundColor: 'rgb(59, 130, 246)',
        pointBorderColor: 'white',
        pointBorderWidth: 2,
        pointRadius: 6,
        tension: 0.4,
      },
      {
        label: 'Confidence Upper',
        data: confidenceUpper,
        borderColor: 'rgba(59, 130, 246, 0.3)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: '+1',
        tension: 0.4,
      },
      {
        label: 'Confidence Lower',
        data: confidenceLower,
        borderColor: 'rgba(59, 130, 246, 0.3)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false,
        tension: 0.4,
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
          filter: (legendItem: any) => {
            // Hide confidence bound labels from legend
            return legendItem.text === 'Predicted Demand'
          },
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
            
            if (datasetLabel === 'Predicted Demand') {
              return `${datasetLabel}: ${value.toFixed(0)} MW`
            }
            return null // Hide confidence bounds from tooltip
          },
          afterBody: function(tooltipItems: any[]) {
            const index = tooltipItems[0].dataIndex
            const pred = predictions[index]
            const range = pred.confidence_upper - pred.confidence_lower
            return [
              '',
              `Confidence Range: ±${(range/2).toFixed(0)} MW`,
              `Time: +${pred.hour_ahead} hour${pred.hour_ahead > 1 ? 's' : ''}`
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
        hoverRadius: 8,
      },
    },
    animation: {
      duration: 1000,
      easing: 'easeInOutQuart',
    },
  }

  return (
    <div className="h-80 w-full">
      <Line ref={chartRef} data={data} options={options} />
    </div>
  )
}
