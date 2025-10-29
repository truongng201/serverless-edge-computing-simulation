from typing import Optional, Tuple, Any, Dict
import os


try:
    import osmnx as ox  # type: ignore
except Exception:  # pragma: no cover
    ox = None


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

    if xml_path and os.path.exists(xml_path):
        G = ox.graph_from_xml(xml_path, bidirectional=True, simplify=True)
    elif graphml_path and os.path.exists(graphml_path):
        G = ox.load_graphml(graphml_path)
    else:
        raise ValueError(
            f"No valid OSM source found. xml_path={xml_path} graphml_path={graphml_path}"
        )

    if project:
        try:
            # Project to a metric CRS for accurate geometry in meters
            Gp = ox.project_graph(G)
            Gp.graph["crs_is_projected"] = True
            return Gp
        except Exception:
            pass
    return G


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


