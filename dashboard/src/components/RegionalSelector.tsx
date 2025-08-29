'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { 
  MapPin, 
  ChevronDown, 
  Zap, 
  Users, 
  Thermometer,
  Building2,
  Globe,
  CheckCircle
} from 'lucide-react'
import { useRegional } from './RegionalProvider'
import { useTheme } from './ThemeProvider'

export default function RegionalSelector() {
  const [isOpen, setIsOpen] = useState(false)
  const { selectedZone, setSelectedZone, currentZone, allZones, zoneCategories, isStatewide } = useRegional()
  const { theme } = useTheme()

  const handleZoneSelect = (zoneName: string) => {
    setSelectedZone(zoneName)
    setIsOpen(false)
  }

  const getZoneIcon = (zoneName: string) => {
    if (zoneName === 'STATEWIDE') return Globe
    if (zoneName.includes('PGE') || zoneName === 'SMUD') return Building2
    return MapPin
  }

  const getLoadSizeLabel = (weight: number) => {
    if (weight >= 0.3) return 'Major'
    if (weight >= 0.1) return 'Large'
    if (weight >= 0.05) return 'Medium'
    return 'Small'
  }

  const getLoadSizeColor = (weight: number) => {
    if (weight >= 0.3) return 'bg-red-100 text-red-800 border-red-200'
    if (weight >= 0.1) return 'bg-orange-100 text-orange-800 border-orange-200'
    if (weight >= 0.05) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    return 'bg-green-100 text-green-800 border-green-200'
  }

  return (
    <div className="flex items-center">
      {/* Regional Selector Button showing current zone */}
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="gap-2 h-[42px]"
          >
            {isStatewide ? (
              <Globe className="h-4 w-4 text-blue-600" />
            ) : (
              <MapPin className="h-4 w-4 text-green-600" />
            )}
            {isStatewide ? 'California' : `${currentZone.major_city} (${currentZone.name})`}
            <ChevronDown className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-96 p-0" align="end">
          <Card className="border-0 shadow-lg">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <MapPin className="h-5 w-5 text-blue-600" />
                Select California Region
              </CardTitle>
              <CardDescription>
                Choose a CAISO zone or view statewide aggregated data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 max-h-96 overflow-y-auto">
              {Object.entries(zoneCategories).map(([category, zones]) => (
                <div key={category}>
                  <h4 className={`text-sm font-semibold mb-2 ${
                    theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                  }`}>
                    {category}
                  </h4>
                  <div className="space-y-1">
                    {zones.map((zoneName) => {
                      const zone = allZones[zoneName]
                      const ZoneIcon = getZoneIcon(zoneName)
                      const isSelected = selectedZone === zoneName
                      
                      return (
                        <button
                          key={zoneName}
                          onClick={() => handleZoneSelect(zoneName)}
                          className={`w-full p-3 rounded-lg border text-left transition-all hover:shadow-sm ${
                            isSelected
                              ? (theme === 'dark' 
                                  ? 'bg-blue-900/30 border-blue-600 text-blue-300' 
                                  : 'bg-blue-50 border-blue-200 text-blue-900')
                              : (theme === 'dark'
                                  ? 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-white'
                                  : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-900')
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3 flex-1">
                              <div className={`p-1.5 rounded-md mt-0.5 ${
                                isSelected
                                  ? (theme === 'dark' ? 'bg-blue-800/50' : 'bg-blue-100')
                                  : (theme === 'dark' ? 'bg-slate-700' : 'bg-slate-100')
                              }`}>
                                <ZoneIcon className={`h-4 w-4 ${
                                  isSelected ? 'text-blue-600' : (theme === 'dark' ? 'text-slate-400' : 'text-slate-600')
                                }`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-medium text-sm">{zone.full_name}</span>
                                  {isSelected && (
                                    <CheckCircle className="h-4 w-4 text-blue-600 flex-shrink-0" />
                                  )}
                                </div>
                                <p className={`text-xs mb-2 ${
                                  theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
                                }`}>
                                  {zone.description}
                                </p>
                                <div className="flex items-center gap-2 flex-wrap">
                                  {zoneName !== 'STATEWIDE' && (
                                    <Badge 
                                      variant="secondary" 
                                      className={`text-xs ${getLoadSizeColor(zone.load_weight)} ${
                                        theme === 'dark' ? 'bg-opacity-20' : ''
                                      }`}
                                    >
                                      <Zap className="h-3 w-3 mr-1" />
                                      {getLoadSizeLabel(zone.load_weight)} Load
                                    </Badge>
                                  )}
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      theme === 'dark' ? 'border-slate-600 text-slate-300' : 'border-slate-300 text-slate-600'
                                    }`}
                                  >
                                    <Thermometer className="h-3 w-3 mr-1" />
                                    {zone.climate_region}
                                  </Badge>
                                </div>
                              </div>
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </PopoverContent>
      </Popover>
    </div>
  )
}
