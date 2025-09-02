'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Brain,
  Zap,
  Layers,
  CheckCircle,
  TrendingUp,
  ChevronDown
} from 'lucide-react'
import { useTheme } from './ThemeProvider'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface ModelInfo {
  model_id: string
  name: string
  type: string
  description: string
  version: string
  accuracy: number
  training_date: string
  is_active: boolean
}

interface ModelSelectorProps {
  onModelChange: (modelId: string) => void
  className?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001'

export default function ModelSelector({ onModelChange, className = '' }: ModelSelectorProps) {
  const { theme } = useTheme()
  const [models, setModels] = useState<ModelInfo[]>([])
  const [currentModel, setCurrentModel] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    fetchModels()
    fetchCurrentModel()
  }, [])

  const fetchModels = async () => {
    try {
      const response = await fetch(`${API_BASE}/models`)
      if (response.ok) {
        const data = await response.json()
        setModels(data)
      }
    } catch (err) {
      console.error('Failed to fetch models:', err)
    }
  }

  const fetchCurrentModel = async () => {
    try {
      const response = await fetch(`${API_BASE}/models/current`)
      if (response.ok) {
        const data = await response.json()
        setCurrentModel(data.current_model)
      }
    } catch (err) {
      console.error('Failed to fetch current model:', err)
    }
  }

  const selectModel = async (modelId: string) => {
    if (modelId === currentModel) return

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/models/select/${modelId}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        setCurrentModel(modelId)
        onModelChange(modelId)
        setIsOpen(false)
      }
    } catch (err) {
      console.error('Failed to select model:', err)
    } finally {
      setLoading(false)
    }
  }

  const getModelIcon = (type: string) => {
    switch (type) {
      case 'xgboost':
        return TrendingUp
      case 'lightgbm':
        return Zap
      case 'lstm':
        return Brain
      case 'ensemble':
        return Layers
      default:
        return Zap
    }
  }

  const getModelColor = (type: string) => {
    switch (type) {
      case 'xgboost':
        return theme === 'dark' ? 'text-green-400' : 'text-green-600'
      case 'lightgbm':
        return theme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
      case 'lstm':
        return theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
      case 'ensemble':
        return theme === 'dark' ? 'text-purple-400' : 'text-purple-600'
      default:
        return theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
    }
  }

  const getModelBadgeColor = (type: string) => {
    switch (type) {
      case 'xgboost':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'lightgbm':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'lstm':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'ensemble':
        return 'bg-purple-100 text-purple-800 border-purple-200'
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200'
    }
  }



  const currentModelInfo = models.find(m => m.model_id === currentModel)

  return (
    <div className={`flex items-center ${className}`}>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 h-[32px] min-w-[140px] justify-between text-xs px-2"
            disabled={loading}
          >
            {currentModelInfo ? (
              <>
                {(() => {
                  const Icon = getModelIcon(currentModelInfo.type)
                  return <Icon className={`h-3 w-3 ${getModelColor(currentModelInfo.type)}`} />
                })()}
                <span className="flex-1 text-left">{currentModelInfo.name}</span>
              </>
            ) : (
              <>
                <Zap className="h-3 w-3" />
                <span className="flex-1 text-left">Select Model</span>
              </>
            )}
            <ChevronDown className="h-3 w-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80 p-0" align="start">
          <div className={`p-3 border-b ${
            theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
          }`}>
            <h3 className="font-semibold text-xs">Select ML Model</h3>
            <p className={`text-xs mt-1 ${
              theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
            }`}>
              Choose the model for power demand predictions
            </p>
          </div>
          
          <div className="max-h-80 overflow-y-auto">
            {models.map((model) => {
              const Icon = getModelIcon(model.type)
              const isSelected = model.model_id === currentModel
              
              return (
                <div
                  key={model.model_id}
                  className={`p-4 border-b cursor-pointer transition-colors ${
                    theme === 'dark' ? 'border-slate-700 hover:bg-slate-800' : 'border-slate-200 hover:bg-slate-50'
                  } ${isSelected ? (theme === 'dark' ? 'bg-slate-800' : 'bg-slate-50') : ''}`}
                  onClick={() => selectModel(model.model_id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <div className={`p-2 rounded-md ${
                        theme === 'dark' ? 'bg-slate-700' : 'bg-slate-100'
                      }`}>
                        <Icon className={`h-4 w-4 ${getModelColor(model.type)}`} />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium text-sm">{model.name}</h4>
                          {isSelected && (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          )}
                        </div>
                        
                        <p className={`text-xs mb-2 ${
                          theme === 'dark' ? 'text-slate-400' : 'text-slate-500'
                        }`}>
                          {model.description}
                        </p>
                        
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline" className={`text-xs ${getModelBadgeColor(model.type)} ${
                            theme === 'dark' ? 'bg-opacity-20' : ''
                          }`}>
                            {model.type.toUpperCase()}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            v{model.version}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center text-xs">
                          <div className="flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" />
                            <span>{model.accuracy.toFixed(1)}% accuracy</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
