from typing import Optional, Tuple, Any
import os
import logging


try:
    import osmnx as ox  # type: ignore
except Exception:  # pragma: no cover
    ox = None
from xml.etree import ElementTree as ET
from shared.custom_exception import BadRequestException

# In-process cache to avoid re-parsing/loading repeatedly
_GRAPH_CACHE = {}


def load_graph(
    xml_path: Optional[str] = None,
    graphml_path: Optional[str] = None,
    network_type: str = "drive",
    project: bool = True,
) -> Any:
    """
    Load a drivable road graph using OSMnx.

    Priority:
      1) If xml_path exists -> graph_from_xml
      2) Else if graphml_path exists -> load_graphml
      3) Else -> raise ValueError
    """
    if ox is None:
        raise ImportError(
            "osmnx is not installed. Install with `pip install osmnx` to use TaxiD scenario."
        )
    logger = logging.getLogger(__name__)

    key = (xml_path or "", graphml_path or "")
    if key in _GRAPH_CACHE:
        return _GRAPH_CACHE[key]

    # Prefer GraphML if present (fast path)
    if graphml_path and os.path.exists(graphml_path):
        logger.info(f"OSM loader: loading GraphML '{graphml_path}'")
        G = ox.load_graphml(graphml_path)
        if project:
            try:
                if not G.graph.get('crs_is_projected', False):
                    G = ox.project_graph(G)
                    G.graph['crs_is_projected'] = True
            except Exception:
                pass
        _GRAPH_CACHE[key] = G
        return G

    # Fallback to XML if provided
    if xml_path and os.path.exists(xml_path):
        # Detect Git LFS pointer files to return a helpful error
        try:
            with open(xml_path, 'rb') as f:
                head = f.read(128)
            if head.startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise BadRequestException(
                    f"OSM XML at '{xml_path}' is a Git LFS pointer. Run 'git lfs pull' or set TAXID_OSM_XML_PATH to a real .osm file."
                )
        except BadRequestException:
            raise
        except Exception:
            pass
        try:
            logger.info(f"OSM loader: parsing XML '{xml_path}' (this may take time)")
            G = ox.graph_from_xml(xml_path, bidirectional=True, simplify=True)
        except ET.ParseError as e:
            raise BadRequestException(
                f"Failed to parse OSM XML at '{xml_path}': {e}. Ensure it is a valid .osm (not a pointer)."
            )
        if project:
            try:
                G = ox.project_graph(G)
                G.graph['crs_is_projected'] = True
            except Exception:
                pass
        # Save GraphML to speed up next loads
        if graphml_path:
            try:
                os.makedirs(os.path.dirname(graphml_path), exist_ok=True)
                ox.save_graphml(G, graphml_path)
                logger.info(f"OSM loader: cached GraphML '{graphml_path}'")
            except Exception:
                pass
        _GRAPH_CACHE[key] = G
        return G

    raise BadRequestException(
        f"No valid OSM source found. Provide TAXID_GRAPHML_PATH or TAXID_OSM_XML_PATH."
    )


def graph_bounds_meters(G: Any) -> Tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) bounds from projected graph (meters)."""
    xs = [d.get("x") for _, d in G.nodes(data=True)]
    ys = [d.get("y") for _, d in G.nodes(data=True)]
    return (min(xs), min(ys), max(xs), max(ys))


def edge_geometries(G: Any):
    """Yield edge geometries as lists of (x_m, y_m) points (meters)."""
    for u, v, data in G.edges(data=True):
        geom = data.get("geometry")
        if geom is not None:
            coords = list(geom.coords)
            yield [(float(x), float(y)) for x, y in coords], data
        else:
            ux = G.nodes[u].get("x")
            uy = G.nodes[u].get("y")
            vx = G.nodes[v].get("x")
            vy = G.nodes[v].get("y")
            yield [(float(ux), float(uy)), (float(vx), float(vy))], data
