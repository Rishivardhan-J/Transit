import numpy as np
from typing import List, Tuple, Dict, Optional
import math

class DistanceMatrix:
    def __init__(self):
        # We cache matrices keyed by a hash of the coordinates.
        # This is a naive in-memory cache for Phase 3.
        # Key: tuple of (lat, lng) tuples
        # Value: 2D numpy array of distances in km
        self._cache: Dict[Tuple[Tuple[float, float], ...], np.ndarray] = {}

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance in kilometers between two points on the earth."""
        R = 6371.0 # Radius of earth in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) * math.sin(dlon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance

    def build_matrix(self, coordinates: List[Tuple[float, float]], use_euclidean: bool = False) -> np.ndarray:
        """
        Builds an N x N distance matrix (in km) using Haversine approximation or Euclidean.
        The first coordinate is typically the depot.
        """
        cache_key = tuple(coordinates) + (use_euclidean,)
        if cache_key in self._cache:
            return self._cache[cache_key]

        n = len(coordinates)
        matrix = np.zeros((n, n), dtype=float)
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    if use_euclidean:
                        matrix[i, j] = math.sqrt((coordinates[i][0] - coordinates[j][0])**2 + (coordinates[i][1] - coordinates[j][1])**2)
                    else:
                        matrix[i, j] = self._haversine(
                            coordinates[i][0], coordinates[i][1],
                            coordinates[j][0], coordinates[j][1]
                        )

        self._cache[cache_key] = matrix
        return matrix

    def clear_cache(self):
        self._cache.clear()

# Global singleton for use across the application
distance_matrix_service = DistanceMatrix()
