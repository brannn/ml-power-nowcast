#!/usr/bin/env python3
"""
NYISO Load Zone Configuration.

Defines the 11 NYISO load zones with representative weather station coordinates
for zone-based weather data collection that correlates with power demand.
"""

from typing import Dict, Tuple, NamedTuple


class NYISOZone(NamedTuple):
    """NYISO load zone configuration."""
    name: str
    full_name: str
    latitude: float
    longitude: float
    major_city: str
    description: str


# NYISO Load Zones with representative weather station coordinates
# Based on NYISO's 11 load zones and their geographic centers
NYISO_ZONES: Dict[str, NYISOZone] = {
    "WEST": NYISOZone(
        name="WEST",
        full_name="Western New York",
        latitude=42.8864,
        longitude=-78.8784,
        major_city="Buffalo",
        description="Western NY including Buffalo, Niagara Falls area"
    ),
    "GENESE": NYISOZone(
        name="GENESE",
        full_name="Genesee",
        latitude=42.9959,
        longitude=-77.7303,
        major_city="Rochester",
        description="Genesee Valley region, Rochester area"
    ),
    "CENTRL": NYISOZone(
        name="CENTRL",
        full_name="Central",
        latitude=43.0481,
        longitude=-76.1474,
        major_city="Syracuse",
        description="Central NY including Syracuse, Oswego"
    ),
    "NORTH": NYISOZone(
        name="NORTH",
        full_name="North",
        latitude=44.6994,
        longitude=-74.9447,
        major_city="Massena",
        description="Northern NY, St. Lawrence Valley, Adirondacks"
    ),
    "MHK VL": NYISOZone(
        name="MHK VL",
        full_name="Mohawk Valley",
        latitude=43.0409,
        longitude=-74.9131,
        major_city="Utica",
        description="Mohawk Valley region, Utica area"
    ),
    "CAPITL": NYISOZone(
        name="CAPITL",
        full_name="Capital",
        latitude=42.6803,
        longitude=-73.8370,
        major_city="Albany",
        description="Capital District, Albany, Schenectady, Troy"
    ),
    "HUD VL": NYISOZone(
        name="HUD VL",
        full_name="Hudson Valley",
        latitude=41.7003,
        longitude=-73.9209,
        major_city="Poughkeepsie",
        description="Hudson Valley, Poughkeepsie, Newburgh area"
    ),
    "MILLWD": NYISOZone(
        name="MILLWD",
        full_name="Millwood",
        latitude=41.1956,
        longitude=-73.7976,
        major_city="White Plains",
        description="Lower Hudson Valley, Westchester County"
    ),
    "DUNWOD": NYISOZone(
        name="DUNWOD",
        full_name="Dunwoodie",
        latitude=40.9176,
        longitude=-73.8370,
        major_city="Yonkers",
        description="Westchester/Bronx border area"
    ),
    "NYNYC": NYISOZone(
        name="NYNYC",
        full_name="New York City",
        latitude=40.7128,
        longitude=-74.0060,
        major_city="New York City",
        description="New York City (Manhattan, Brooklyn, Queens, Bronx, Staten Island)"
    ),
    "LONGIL": NYISOZone(
        name="LONGIL",
        full_name="Long Island",
        latitude=40.7891,
        longitude=-73.1350,
        major_city="Hempstead",
        description="Long Island (Nassau and Suffolk Counties)"
    ),
}


def get_zone_coordinates(zone_name: str) -> Tuple[float, float]:
    """
    Get latitude and longitude coordinates for a NYISO zone.
    
    Args:
        zone_name: NYISO zone name (e.g., 'WEST', 'CAPITL', 'NYNYC')
        
    Returns:
        Tuple of (latitude, longitude)
        
    Raises:
        KeyError: If zone_name is not a valid NYISO zone
    """
    if zone_name not in NYISO_ZONES:
        valid_zones = list(NYISO_ZONES.keys())
        raise KeyError(f"Unknown NYISO zone '{zone_name}'. Valid zones: {valid_zones}")
    
    zone = NYISO_ZONES[zone_name]
    return (zone.latitude, zone.longitude)


def get_all_zone_coordinates() -> Dict[str, Tuple[float, float]]:
    """
    Get coordinates for all NYISO zones.
    
    Returns:
        Dictionary mapping zone names to (latitude, longitude) tuples
    """
    return {name: (zone.latitude, zone.longitude) for name, zone in NYISO_ZONES.items()}


def get_zone_info(zone_name: str) -> NYISOZone:
    """
    Get complete information for a NYISO zone.
    
    Args:
        zone_name: NYISO zone name
        
    Returns:
        NYISOZone object with complete zone information
        
    Raises:
        KeyError: If zone_name is not a valid NYISO zone
    """
    if zone_name not in NYISO_ZONES:
        valid_zones = list(NYISO_ZONES.keys())
        raise KeyError(f"Unknown NYISO zone '{zone_name}'. Valid zones: {valid_zones}")
    
    return NYISO_ZONES[zone_name]


def list_zones() -> Dict[str, str]:
    """
    List all NYISO zones with their full names.
    
    Returns:
        Dictionary mapping zone names to full names
    """
    return {name: zone.full_name for name, zone in NYISO_ZONES.items()}


# Population-based weights for aggregating zone weather into statewide averages
# Based on approximate population distribution across NYISO zones
ZONE_POPULATION_WEIGHTS: Dict[str, float] = {
    "WEST": 0.06,      # Buffalo area
    "GENESE": 0.05,    # Rochester area  
    "CENTRL": 0.04,    # Syracuse area
    "NORTH": 0.02,     # Rural northern NY
    "MHK VL": 0.02,    # Utica area
    "CAPITL": 0.05,    # Albany area
    "HUD VL": 0.08,    # Mid-Hudson Valley
    "MILLWD": 0.05,    # Westchester
    "DUNWOD": 0.03,    # Westchester/Bronx
    "NYNYC": 0.42,     # NYC (largest population)
    "LONGIL": 0.18,    # Long Island
}


def get_population_weighted_average(zone_values: Dict[str, float]) -> float:
    """
    Calculate population-weighted average across NYISO zones.
    
    Args:
        zone_values: Dictionary mapping zone names to values (e.g., temperature)
        
    Returns:
        Population-weighted average value
        
    Raises:
        ValueError: If zone_values contains unknown zones
    """
    total_weighted_value = 0.0
    total_weight = 0.0
    
    for zone_name, value in zone_values.items():
        if zone_name not in ZONE_POPULATION_WEIGHTS:
            valid_zones = list(ZONE_POPULATION_WEIGHTS.keys())
            raise ValueError(f"Unknown zone '{zone_name}'. Valid zones: {valid_zones}")
        
        weight = ZONE_POPULATION_WEIGHTS[zone_name]
        total_weighted_value += value * weight
        total_weight += weight
    
    if total_weight == 0:
        raise ValueError("No valid zones provided for weighted average")
    
    return total_weighted_value / total_weight
