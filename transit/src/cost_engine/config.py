from pydantic import BaseModel, Field, model_validator
from typing import Dict

class CostWeights(BaseModel):
    w_distance: float = Field(ge=0.0, le=1.0)
    w_time: float = Field(ge=0.0, le=1.0)
    w_fuel: float = Field(ge=0.0, le=1.0)
    w_delay: float = Field(ge=0.0, le=1.0)
    w_constraint: float = Field(default=10000.0, ge=0.0, description="Penalty multiplier outside of the sum-to-1 normalization")

    @model_validator(mode='after')
    def check_sum_to_one(self) -> 'CostWeights':
        total = self.w_distance + self.w_time + self.w_fuel + self.w_delay
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Weights must sum to 1.0. Current sum: {total:.4f}")
        return self

    @classmethod
    def auto_normalize(cls, w_distance: float, w_time: float, w_fuel: float, w_delay: float, w_constraint: float = 10000.0) -> 'CostWeights':
        """
        Helper method to automatically normalize weights that don't sum to 1.
        Used by Phase 5 sandbox sliders.
        """
        total = w_distance + w_time + w_fuel + w_delay
        if total == 0:
            return cls(w_distance=0.25, w_time=0.25, w_fuel=0.25, w_delay=0.25, w_constraint=w_constraint)
            
        return cls(
            w_distance=w_distance / total,
            w_time=w_time / total,
            w_fuel=w_fuel / total,
            w_delay=w_delay / total,
            w_constraint=w_constraint
        )

# Delay penalty multipliers based on priority
PRIORITY_MULTIPLIERS: Dict[str, float] = {
    "low": 0.5,
    "standard": 1.0,
    "high": 2.0,
    "urgent": 5.0
}

# Pre-configured Presets
PRESETS: Dict[str, CostWeights] = {
    "time_focused": CostWeights(w_distance=0.1, w_time=0.6, w_fuel=0.1, w_delay=0.2),
    "cost_focused": CostWeights(w_distance=0.2, w_time=0.1, w_fuel=0.6, w_delay=0.1),
    "distance_focused": CostWeights(w_distance=0.7, w_time=0.1, w_fuel=0.1, w_delay=0.1),
    "balanced": CostWeights(w_distance=0.25, w_time=0.25, w_fuel=0.25, w_delay=0.25)
}
