# Weather Data Summary

## Overview
Comprehensive weather forecast data for 19 major airports across 8 regions, covering 3 days (Feb 1-3, 2026) with 3-hour intervals.

## Coverage

### Total Statistics
- **Total Records**: 456
- **Total Airports**: 19
- **Date Range**: 2026-02-01 to 2026-02-03 (3 days)
- **Frequency**: Every 3 hours (8 records per day per airport)
- **Records per Airport**: 24

## Airports by Region

### Middle East (2 airports)
- **AUH** - Abu Dhabi, UAE (24 records)
  - Conditions: Clear, Partly Cloudy, Cloudy
  - Temperature: 20-35°C
  - Status: Normal operations (hub)

### Southeast Asia (3 airports)
- **BKK** - Bangkok, Thailand (24 records)
  - Conditions: Typhoon (Day 1), Recovery (Days 2-3)
  - Temperature: 24-30°C
  - Status: Severe disruption Day 1, improving Days 2-3

- **CGK** - Jakarta, Indonesia (24 records)
  - Conditions: Rainy season - Cloudy, Rain, Thunderstorms
  - Temperature: 24-32°C
  - Status: Frequent rain, some delays expected

- **DPS** - Bali Denpasar, Indonesia (24 records)
  - Conditions: Rainy season - Partly Cloudy, Rain
  - Temperature: 25-31°C
  - Status: Tropical weather, occasional delays

### Australia (4 airports)
- **SYD** - Sydney (24 records)
  - Conditions: Summer - Clear, Partly Cloudy, occasional Thunderstorms
  - Temperature: 22-32°C
  - Status: Generally good, occasional storms

- **MEL** - Melbourne (24 records)
  - Conditions: Summer - Variable, some rain
  - Temperature: 18-28°C
  - Status: Changeable weather

- **PER** - Perth (24 records)
  - Conditions: Summer - Mostly clear
  - Temperature: 24-35°C
  - Status: Excellent conditions

- **BNE** - Brisbane (24 records)
  - Conditions: Summer - Clear, occasional storms
  - Temperature: 23-31°C
  - Status: Good conditions

### Japan (3 airports)
- **NRT** - Tokyo Narita (24 records)
  - Conditions: Winter - Clear, Cloudy, occasional Light Snow
  - Temperature: 2-10°C
  - Status: Cold but operational

- **HND** - Tokyo Haneda (24 records)
  - Conditions: Winter - Clear, Cloudy, occasional Light Snow
  - Temperature: 3-11°C
  - Status: Cold but operational

- **KIX** - Osaka Kansai (24 records)
  - Conditions: Winter - Clear, Cloudy, Light Rain
  - Temperature: 4-12°C
  - Status: Mild winter conditions

### United Kingdom (2 airports)
- **LHR** - London Heathrow (24 records)
  - Conditions: Winter - Cloudy, Overcast, Rain, Fog
  - Temperature: 3-10°C
  - Status: Typical UK winter, some delays

- **LGW** - London Gatwick (24 records)
  - Conditions: Winter - Cloudy, Overcast, Rain, Fog
  - Temperature: 3-10°C
  - Status: Typical UK winter, some delays

### France (2 airports)
- **CDG** - Paris Charles de Gaulle (24 records)
  - Conditions: Winter - Cloudy, Overcast, Light Rain, Fog
  - Temperature: 2-9°C
  - Status: Cold, variable conditions

- **ORY** - Paris Orly (24 records)
  - Conditions: Winter - Cloudy, Overcast, Light Rain, Fog
  - Temperature: 2-9°C
  - Status: Cold, variable conditions

### Spain (2 airports)
- **MAD** - Madrid (24 records)
  - Conditions: Mild winter - Clear, Partly Cloudy
  - Temperature: 5-14°C
  - Status: Good conditions

- **BCN** - Barcelona (24 records)
  - Conditions: Mild winter - Clear, Partly Cloudy
  - Temperature: 8-15°C
  - Status: Excellent conditions

### Italy (2 airports)
- **FCO** - Rome Fiumicino (24 records)
  - Conditions: Cool winter - Clear, Partly Cloudy, Cloudy
  - Temperature: 6-14°C
  - Status: Good conditions

- **MXP** - Milan Malpensa (24 records)
  - Conditions: Cool winter - Cloudy, Fog, Light Rain
  - Temperature: 2-10°C
  - Status: Fog possible, some delays

## Weather Attributes

Each weather record includes:
- **airport_code**: IATA airport code
- **forecast_time_zulu**: Forecast timestamp in UTC
- **forecast_valid_from**: Validity start time
- **forecast_valid_to**: Validity end time (3 hours)
- **condition**: Weather condition (Clear, Cloudy, Rain, etc.)
- **visibility_km**: Visibility in kilometers
- **wind_speed_kts**: Wind speed in knots
- **wind_direction**: Wind direction (N, NE, E, SE, S, SW, W, NW)
- **wind_gust_kts**: Wind gust speed in knots
- **temperature_c**: Temperature in Celsius
- **pressure_hpa**: Atmospheric pressure in hectopascals
- **precipitation_mm_per_hour**: Precipitation rate
- **cloud_base_ft**: Cloud base in feet
- **operational_impact**: Impact on operations (NONE, MINOR, MODERATE, SEVERE)
- **runway_condition**: Runway state (DRY, DAMP, WET)
- **crosswind_component_kts**: Crosswind component in knots

## Operational Impact Levels

### NONE - Normal operations
- Clear visibility (>7 km)
- No precipitation or light precipitation
- Normal wind conditions
- Most airports most of the time

### MINOR - Some delays possible
- Moderate visibility (5-7 km)
- Light to moderate precipitation (5-15 mm/hr)
- Increased wind
- Occasional at rainy locations

### MODERATE - Delays expected, monitor closely
- Reduced visibility (2-5 km)
- Moderate to heavy precipitation (15-30 mm/hr)
- Strong winds
- BKK during typhoon recovery, UK/France in winter

### SEVERE - Airport may close, all operations suspended
- Very poor visibility (<2 km)
- Heavy precipitation (>30 mm/hr)
- Very strong winds (>50 kts)
- BKK during typhoon (Day 1), rare at other locations

## Use Cases

1. **Disruption Planning**: Weather impacts on flight operations
2. **Connection Analysis**: Weather at connecting airports
3. **Aircraft Routing**: Weather-based routing decisions
4. **Passenger Communication**: Weather-related delay explanations
5. **Crew Scheduling**: Weather impacts on crew availability
6. **Fuel Planning**: Weather-based fuel requirements
7. **Alternate Airport Selection**: Weather at alternate airports

## Files

- **Generator**: `generators/enrich_weather_global.py`
- **Data File**: `output/weather.csv`
- **Verification**: `verify_weather.py`

## Sample Data

```
SYD - 2026-02-01T00:00:00Z: Partly Cloudy, 30°C, Vis: 8.0km
NRT - 2026-02-01T00:00:00Z: Clear, 7°C, Vis: 6.9km
CGK - 2026-02-01T00:00:00Z: Partly Cloudy, 32°C, Vis: 5.6km
LHR - 2026-02-01T00:00:00Z: Cloudy, 3°C, Vis: 8.7km
MAD - 2026-02-01T00:00:00Z: Clear, 7°C, Vis: 8.8km
FCO - 2026-02-01T00:00:00Z: Clear, 6°C, Vis: 9.6km
```

## Notes

- Weather patterns reflect typical February conditions for each region
- Australia: Summer (hot, occasional storms)
- Japan: Winter (cold, dry, occasional snow)
- Indonesia: Rainy season (hot, humid, frequent rain)
- Europe: Winter (cold, wet, cloudy)
- Middle East: Mild (warm, dry)
- All times in UTC (Zulu time)
- Realistic operational impacts based on visibility and precipitation
