from dataclasses import dataclass, field
from typing import Protocol

from apps.common.geo import LngLat


@dataclass(frozen=True)
class RawRoute:
    """A route as the provider returned it, before checkpoints or weather."""
    coordinates: list[LngLat]
    distance_mi: float
    duration_s: float
    provider: str
    #: Provider-side identifier, e.g. "alternative-1" or "via-left"
    provider_ref: str


@dataclass
class RoutingResult:
    routes: list[RawRoute]
    warnings: list[str] = field(default_factory=list)


class RoutingProvider(Protocol):
    name: str

    def routes(self, origin: LngLat, destination: LngLat, max_routes: int = 3) -> RoutingResult:
        """Up to `max_routes` alternatives, primary first. Raises NoRouteFound or ProviderError."""
