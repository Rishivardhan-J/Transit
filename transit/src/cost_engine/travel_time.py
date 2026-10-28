"""Travel-time providers: turn a distance matrix into a travel-time matrix (minutes).

The optimizer only ever sees a minutes matrix, so swapping providers (benchmark
Euclidean, speed profile, ML leg model) never touches solver code.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import numpy as np


class TravelTimeProvider(ABC):
    @abstractmethod
    def matrix(self, coords: List[Tuple[float, float]], dist: np.ndarray,
               depart_hour: float = 12.0) -> np.ndarray:
        """Return an NxN matrix of travel minutes (zero diagonal)."""


class EuclideanTime(TravelTimeProvider):
    """Solomon convention: 1 distance unit == 1 minute."""

    def matrix(self, coords, dist, depart_hour: float = 12.0) -> np.ndarray:
        return np.array(dist, dtype=float)


class SpeedProfileTime(TravelTimeProvider):
    """distance / speed(hour). Fallback when no ML model is available."""

    def __init__(self, base_speed_kmh: float = 35.0, peak_slowdown: float = 0.6):
        self.base_speed_kmh = base_speed_kmh
        self.peak_slowdown = peak_slowdown

    def speed_kmh(self, hour: float) -> float:
        peak = 7 <= hour < 10 or 16 <= hour < 20
        return self.base_speed_kmh * (self.peak_slowdown if peak else 1.0)

    def matrix(self, coords, dist, depart_hour: float = 12.0) -> np.ndarray:
        return np.asarray(dist, dtype=float) / self.speed_kmh(depart_hour) * 60.0
