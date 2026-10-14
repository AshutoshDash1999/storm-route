"""Unit normalization for provider values. Unknown units are a provider error, never guessed."""

from apps.common.exceptions import ProviderBadResponse

_TO_MPH = {'mp/h': 1.0, 'mph': 1.0, 'km/h': 0.621371, 'm/s': 2.236936, 'kn': 1.150779}
_TO_INCHES = {'inch': 1.0, 'in': 1.0, 'mm': 1 / 25.4, 'cm': 1 / 2.54}


def _convert(value: float | None, unit: str, table: dict[str, float], provider: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * table[unit]
    except KeyError:
        raise ProviderBadResponse(provider, f'unexpected unit {unit!r}') from None
    except (TypeError, ValueError):
        raise ProviderBadResponse(provider, f'non-numeric value {value!r}') from None


def to_mph(value: float | None, unit: str, provider: str = 'weather') -> float | None:
    return _convert(value, unit, _TO_MPH, provider)


def to_inches(value: float | None, unit: str, provider: str = 'weather') -> float | None:
    return _convert(value, unit, _TO_INCHES, provider)
