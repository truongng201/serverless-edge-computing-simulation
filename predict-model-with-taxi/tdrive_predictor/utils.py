import math
from dataclasses import dataclass
from typing import Tuple

try:
    from pyproj import Transformer
except Exception:  # pragma: no cover
    Transformer = None  # type: ignore


WGS84_EPSG = "EPSG:4326"
UTM50N_EPSG = "EPSG:32650"  # Beijing region


def get_transformers():
    if Transformer is None:
        raise ImportError(
            "pyproj is required. Please install: pip install pyproj"
        )
    to_utm = Transformer.from_crs(WGS84_EPSG, UTM50N_EPSG, always_xy=True)
    to_wgs = Transformer.from_crs(UTM50N_EPSG, WGS84_EPSG, always_xy=True)
    return to_utm, to_wgs


def wgs84_to_utm(lon, lat):
    to_utm, _ = get_transformers()
    x, y = to_utm.transform(lon, lat)
    return x, y


def utm_to_wgs84(x, y):
    _, to_wgs = get_transformers()
    lon, lat = to_wgs.transform(x, y)
    return lon, lat


def angle_wrap(radians: float) -> float:
    """Wrap angle to [-pi, pi)."""
    return (radians + math.pi) % (2 * math.pi) - math.pi


def heading_from_dxdy(dx: float, dy: float) -> float:
    return math.atan2(dy, dx)


@dataclass
class HorizonSpec:
    # minutes ahead
    horizons_min: Tuple[int, int, int, int] = (1, 3, 5, 10)
    # weights for loss per horizon
    weights: Tuple[float, float, float, float] = (1.0, 0.5, 0.5, 1.0)

