from enum import StrEnum


class WeatherSource(StrEnum):
    OPEN_METEO = "open-meteo"
    OPENWEATHER = "openweather"
    CACHE_HIT = "CACHE_HIT"


class LocationSource(StrEnum):
    DISTRICT_CENTROID = "DISTRICT_CENTROID"
