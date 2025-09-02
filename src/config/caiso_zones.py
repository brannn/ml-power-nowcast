#!/usr/bin/env python3
"""
CAISO Load Zone Configuration.

Defines the major CAISO load zones with representative weather station coordinates
for zone-based weather data collection that correlates with power demand.

CAISO has many pricing nodes, but for weather correlation we focus on the major
load aggregation points (LAPs) and transmission access charges (TAC) areas.
"""

from typing import Dict, Tuple, NamedTuple


class CAISOZone(NamedTuple):
    """CAISO load zone configuration."""
    name: str
    full_name: str
    latitude: float
    longitude: float
    major_city: str
    description: str


# CAISO Major Load Zones with representative weather station coordinates
# Based on CAISO's major Load Aggregation Points (LAPs) and geographic regions
CAISO_ZONES: Dict[str, CAISOZone] = {
    "NP15": CAISOZone(
        name="NP15",
        full_name="North of Path 15",
        latitude=37.7749,
        longitude=-122.4194,
        major_city="San Francisco",
        description="Northern California including SF Bay Area, Sacramento Valley"
    ),
    "ZP26": CAISOZone(
        name="ZP26",
        full_name="Fresno/Central Valley",
        latitude=36.7378,
        longitude=-119.7871,
        major_city="Fresno",
        description="Central Valley region, agricultural areas"
    ),
    "SP15": CAISOZone(
        name="SP15",
        full_name="South of Path 15",
        latitude=34.0522,
        longitude=-118.2437,
        major_city="Los Angeles",
        description="Southern California including LA Basin, Orange County"
    ),
    "SDGE": CAISOZone(
        name="SDGE",
        full_name="San Diego Gas & Electric",
        latitude=32.7157,
        longitude=-117.1611,
        major_city="San Diego",
        description="San Diego County and Imperial Valley"
    ),
    "SCE": CAISOZone(
        name="SCE",
        full_name="Southern California Edison",
        latitude=34.1478,
        longitude=-117.8265,
        major_city="San Bernardino",
        description="Inland Empire, Riverside, San Bernardino counties"
    ),
    "PGE_BAY": CAISOZone(
        name="PGE_BAY",
        full_name="PG&E Bay Area",
        latitude=37.4419,
        longitude=-122.1430,
        major_city="Palo Alto",
        description="SF Peninsula, South Bay, Silicon Valley"
    ),
    "PGE_VALLEY": CAISOZone(
        name="PGE_VALLEY",
        full_name="PG&E Central Valley",
        latitude=37.6391,
        longitude=-120.9969,
        major_city="Modesto",
        description="Central Valley within PG&E territory"
    ),
    "SMUD": CAISOZone(
        name="SMUD",
        full_name="Sacramento Municipal Utility District",
        latitude=38.5816,
        longitude=-121.4944,
        major_city="Sacramento",
        description="Sacramento metropolitan area"
    ),
}


def get_zone_coordinates(zone_name: str) -> Tuple[float, float]:
    """
    Get latitude and longitude coordinates for a CAISO zone.
    
    Args:
        zone_name: CAISO zone name (e.g., 'NP15', 'SP15', 'SDGE')
        
    Returns:
        Tuple of (latitude, longitude)
        
    Raises:
        KeyError: If zone_name is not a valid CAISO zone
    """
    if zone_name not in CAISO_ZONES:
        valid_zones = list(CAISO_ZONES.keys())
        raise KeyError(f"Unknown CAISO zone '{zone_name}'. Valid zones: {valid_zones}")
    
    zone = CAISO_ZONES[zone_name]
    return (zone.latitude, zone.longitude)


def get_all_zone_coordinates() -> Dict[str, Tuple[float, float]]:
    """
    Get coordinates for all CAISO zones.
    
    Returns:
        Dictionary mapping zone names to (latitude, longitude) tuples
    """
    return {name: (zone.latitude, zone.longitude) for name, zone in CAISO_ZONES.items()}


def get_zone_info(zone_name: str) -> CAISOZone:
    """
    Get complete information for a CAISO zone.
    
    Args:
        zone_name: CAISO zone name
        
    Returns:
        CAISOZone object with complete zone information
        
    Raises:
        KeyError: If zone_name is not a valid CAISO zone
    """
    if zone_name not in CAISO_ZONES:
        valid_zones = list(CAISO_ZONES.keys())
        raise KeyError(f"Unknown CAISO zone '{zone_name}'. Valid zones: {valid_zones}")
    
    return CAISO_ZONES[zone_name]


def list_zones() -> Dict[str, str]:
    """
    List all CAISO zones with their full names.
    
    Returns:
        Dictionary mapping zone names to full names
    """
    return {name: zone.full_name for name, zone in CAISO_ZONES.items()}


# Load-based weights for aggregating zone weather into statewide averages
# Based on approximate load distribution across CAISO zones
# California's load is heavily concentrated in LA Basin and SF Bay Area
ZONE_LOAD_WEIGHTS: Dict[str, float] = {
    "NP15": 0.25,        # Northern CA including Bay Area
    "ZP26": 0.08,        # Central Valley (lower population)
    "SP15": 0.35,        # Southern CA (largest load center)
    "SDGE": 0.08,        # San Diego area
    "SCE": 0.15,         # Inland Empire
    "PGE_BAY": 0.05,     # Additional Bay Area detail
    "PGE_VALLEY": 0.02,  # Additional Central Valley
    "SMUD": 0.02,        # Sacramento area
}


def get_load_weighted_average(zone_values: Dict[str, float]) -> float:
    """
    Calculate load-weighted average across CAISO zones.
    
    Args:
        zone_values: Dictionary mapping zone names to values (e.g., temperature)
        
    Returns:
        Load-weighted average value
        
    Raises:
        ValueError: If zone_values contains unknown zones
    """
    total_weighted_value = 0.0
    total_weight = 0.0
    
    for zone_name, value in zone_values.items():
        if zone_name not in ZONE_LOAD_WEIGHTS:
            valid_zones = list(ZONE_LOAD_WEIGHTS.keys())
            raise ValueError(f"Unknown zone '{zone_name}'. Valid zones: {valid_zones}")
        
        weight = ZONE_LOAD_WEIGHTS[zone_name]
        total_weighted_value += value * weight
        total_weight += weight
    
    if total_weight == 0:
        raise ValueError("No valid zones provided for weighted average")
    
    return total_weighted_value / total_weight


# Climate regions for California - useful for understanding weather patterns
CLIMATE_REGIONS: Dict[str, str] = {
    "NP15": "Mediterranean coastal",
    "ZP26": "Hot semi-arid",
    "SP15": "Mediterranean/semi-arid",
    "SDGE": "Semi-arid coastal",
    "SCE": "Hot semi-arid inland",
    "PGE_BAY": "Mediterranean coastal",
    "PGE_VALLEY": "Hot semi-arid",
    "SMUD": "Mediterranean inland",
}
