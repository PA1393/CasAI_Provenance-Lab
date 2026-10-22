"""Bounded API request for draft simulation planning."""

from pydantic import Field

from app.modules.information_processor.contracts import Contract
from app.modules.simulation import SimulationStage


class SimulationPlanCreateBody(Contract):
    confirmed_version_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    guide_map_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    guide_ranking_id: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    stages: tuple[SimulationStage, ...] = Field(min_length=1, max_length=32)
    limitations: tuple[str, ...] = Field(default=(), max_length=64)
