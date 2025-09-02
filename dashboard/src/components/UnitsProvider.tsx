'use client'

import { createContext, useContext, useEffect, useState } from 'react'

type UnitSystem = 'metric' | 'imperial'

interface UnitsContextType {
  unitSystem: UnitSystem
  toggleUnits: () => void
  convertTemperature: (celsius: number) => number
  convertWindSpeed: (kmh: number) => number
  formatTemperature: (celsius: number) => string
  formatWindSpeed: (kmh: number) => string
}

const UnitsContext = createContext<UnitsContextType | undefined>(undefined)

export function UnitsProvider({ children }: { children: React.ReactNode }) {
  const [unitSystem, setUnitSystem] = useState<UnitSystem>('metric')

  useEffect(() => {
    // Check for saved unit preference
    const savedUnits = localStorage.getItem('unitSystem') as UnitSystem
    if (savedUnits) {
      setUnitSystem(savedUnits)
    } else {
      // Default to metric for international users, imperial for US
      const isUS = Intl.DateTimeFormat().resolvedOptions().timeZone?.includes('America')
      setUnitSystem(isUS ? 'imperial' : 'metric')
    }
  }, [])

  useEffect(() => {
    // Save unit preference
    localStorage.setItem('unitSystem', unitSystem)
  }, [unitSystem])

  const toggleUnits = () => {
    setUnitSystem(prev => prev === 'metric' ? 'imperial' : 'metric')
  }

  const convertTemperature = (celsius: number) => {
    return unitSystem === 'metric' ? celsius : (celsius * 9/5) + 32
  }

  const convertWindSpeed = (kmh: number) => {
    return unitSystem === 'metric' ? kmh : kmh * 0.621371 // km/h to mph
  }

  const formatTemperature = (celsius: number) => {
    const converted = convertTemperature(celsius)
    const unit = unitSystem === 'metric' ? '°C' : '°F'
    return `${converted.toFixed(1)}${unit}`
  }

  const formatWindSpeed = (kmh: number) => {
    const converted = convertWindSpeed(kmh)
    const unit = unitSystem === 'metric' ? 'km/h' : 'mph'
    return `${converted.toFixed(1)} ${unit}`
  }

  return (
    <UnitsContext.Provider value={{
      unitSystem,
      toggleUnits,
      convertTemperature,
      convertWindSpeed,
      formatTemperature,
      formatWindSpeed
    }}>
      {children}
    </UnitsContext.Provider>
  )
}

export function useUnits() {
  const context = useContext(UnitsContext)
  if (context === undefined) {
    throw new Error('useUnits must be used within a UnitsProvider')
  }
  return context
}
