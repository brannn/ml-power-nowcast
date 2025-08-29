'use client'

import { createContext, useContext, useEffect, useState } from 'react'

// CAISO Zone definitions based on your existing config
export interface CAISOZone {
  name: string
  full_name: string
  latitude: number
  longitude: number
  major_city: string
  description: string
  load_weight: number
  climate_region: string
}

export const CAISO_ZONES: Record<string, CAISOZone> = {
  STATEWIDE: {
    name: 'STATEWIDE',
    full_name: 'California Statewide',
    latitude: 36.7783,
    longitude: -119.4179,
    major_city: 'California',
    description: 'Aggregated statewide power demand across all CAISO zones',
    load_weight: 1.0,
    climate_region: 'Mixed'
  },
  NP15: {
    name: 'NP15',
    full_name: 'North of Path 15',
    latitude: 37.7749,
    longitude: -122.4194,
    major_city: 'San Francisco',
    description: 'Northern California including SF Bay Area, Sacramento Valley',
    load_weight: 0.25,
    climate_region: 'Mediterranean coastal'
  },
  ZP26: {
    name: 'ZP26',
    full_name: 'Fresno/Central Valley',
    latitude: 36.7378,
    longitude: -119.7871,
    major_city: 'Fresno',
    description: 'Central Valley region, agricultural areas',
    load_weight: 0.08,
    climate_region: 'Hot semi-arid'
  },
  SP15: {
    name: 'SP15',
    full_name: 'South of Path 15',
    latitude: 34.0522,
    longitude: -118.2437,
    major_city: 'Los Angeles',
    description: 'Southern California including LA Basin, Orange County',
    load_weight: 0.35,
    climate_region: 'Mediterranean/semi-arid'
  },
  SDGE: {
    name: 'SDGE',
    full_name: 'San Diego Gas & Electric',
    latitude: 32.7157,
    longitude: -117.1611,
    major_city: 'San Diego',
    description: 'San Diego County and Imperial Valley',
    load_weight: 0.08,
    climate_region: 'Semi-arid coastal'
  },
  SCE: {
    name: 'SCE',
    full_name: 'Southern California Edison',
    latitude: 34.1478,
    longitude: -117.8265,
    major_city: 'San Bernardino',
    description: 'Inland Empire, Riverside, San Bernardino counties',
    load_weight: 0.15,
    climate_region: 'Hot semi-arid inland'
  },
  PGE_BAY: {
    name: 'PGE_BAY',
    full_name: 'PG&E Bay Area',
    latitude: 37.4419,
    longitude: -122.1430,
    major_city: 'Palo Alto',
    description: 'SF Peninsula, South Bay, Silicon Valley',
    load_weight: 0.05,
    climate_region: 'Mediterranean coastal'
  },
  PGE_VALLEY: {
    name: 'PGE_VALLEY',
    full_name: 'PG&E Central Valley',
    latitude: 37.6391,
    longitude: -120.9969,
    major_city: 'Modesto',
    description: 'Central Valley within PG&E territory',
    load_weight: 0.02,
    climate_region: 'Hot semi-arid'
  },
  SMUD: {
    name: 'SMUD',
    full_name: 'Sacramento Municipal Utility District',
    latitude: 38.5816,
    longitude: -121.4944,
    major_city: 'Sacramento',
    description: 'Sacramento metropolitan area',
    load_weight: 0.02,
    climate_region: 'Mediterranean inland'
  }
}

// Zone categories for better organization
export const ZONE_CATEGORIES = {
  'Major Regions': ['STATEWIDE', 'NP15', 'SP15', 'SDGE', 'SCE'],
  'Utility Territories': ['PGE_BAY', 'PGE_VALLEY', 'SMUD'],
  'Geographic Areas': ['ZP26']
}

interface RegionalContextType {
  selectedZone: string
  setSelectedZone: (zone: string) => void
  currentZone: CAISOZone
  allZones: Record<string, CAISOZone>
  zoneCategories: typeof ZONE_CATEGORIES
  isStatewide: boolean
}

const RegionalContext = createContext<RegionalContextType | undefined>(undefined)

export function RegionalProvider({ children }: { children: React.ReactNode }) {
  const [selectedZone, setSelectedZone] = useState<string>('STATEWIDE')

  useEffect(() => {
    // Check for saved zone preference
    const savedZone = localStorage.getItem('selectedZone')
    if (savedZone && CAISO_ZONES[savedZone]) {
      setSelectedZone(savedZone)
    }
  }, [])

  useEffect(() => {
    // Save zone preference
    localStorage.setItem('selectedZone', selectedZone)
  }, [selectedZone])

  const currentZone = CAISO_ZONES[selectedZone]
  const isStatewide = selectedZone === 'STATEWIDE'

  return (
    <RegionalContext.Provider value={{
      selectedZone,
      setSelectedZone,
      currentZone,
      allZones: CAISO_ZONES,
      zoneCategories: ZONE_CATEGORIES,
      isStatewide
    }}>
      {children}
    </RegionalContext.Provider>
  )
}

export function useRegional() {
  const context = useContext(RegionalContext)
  if (context === undefined) {
    throw new Error('useRegional must be used within a RegionalProvider')
  }
  return context
}
