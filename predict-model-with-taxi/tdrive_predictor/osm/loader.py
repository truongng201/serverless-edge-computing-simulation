"""
OSM loader skeleton for Phase B.

Provides a simple API to obtain a drivable road graph via OSMnx, with caching
to GraphML for reproducibility and offline runs.
"""

from typing import Optional

try:
    import osmnx as ox  # type: ignore
except Exception:  # pragma: no cover
    ox = None

import os


def load_graph(
    graphml_path: Optional[str] = None,
    place: Optional[str] = None,
    bbox: Optional[tuple] = None,
    network_type: str = "drive",
    save_if_download: bool = True,
    project: bool = True,
    overpass_endpoint: Optional[str] = None,
    overpass_timeout: Optional[int] = None,
    xml_path: Optional[str] = None,
):
    """
    Load a road graph.

    Priority:
      1) If graphml_path exists -> load_graphml
      2) Else if place or bbox provided -> download via OSMnx and optionally save
      3) Else -> raise a helpful error

    Parameters
    ----------
    graphml_path : str, optional
        Path to a .graphml cache file to load/save.
    place : str, optional
        Place name for OSMnx (e.g., "Beijing, China").
    bbox : tuple, optional
        (north, south, east, west) bounding box for OSMnx.
    network_type : str
        OSMnx network type (default "drive").
    save_if_download : bool
        If True and graphml_path is set, save the downloaded graph to that file.
    """
    if ox is None:
        raise ImportError(
            "osmnx is not installed. Install with `pip install osmnx` to use OSM loader."
        )
    # Optional: configure Overpass endpoint/timeout (if downloading)
    if overpass_endpoint:
        try:
            ox.settings.overpass_endpoint = overpass_endpoint
        except Exception:
            pass
    if overpass_timeout:
        try:
            ox.settings.timeout = int(overpass_timeout)
        except Exception:
            pass
    try:
        ox.settings.overpass_rate_limit = True
    except Exception:
        pass

    if graphml_path and os.path.exists(graphml_path):
        G = ox.load_graphml(graphml_path)
        # If loaded graph is not projected and project=True, project it
        if project:
            try:
                if not G.graph.get('crs_is_projected', False):
                    Gp = ox.project_graph(G)
                    Gp.graph['crs_is_projected'] = True
                    return Gp
            except Exception:
                pass
        return G
    # Option: load from local OSM/XML (avoids Overpass)
    if xml_path and os.path.exists(xml_path):
        G = ox.graph_from_xml(xml_path, bidirectional=True, simplify=True)
        if project:
            G = ox.project_graph(G)
            G.graph['crs_is_projected'] = True
        if save_if_download and graphml_path:
            os.makedirs(os.path.dirname(graphml_path), exist_ok=True)
            ox.save_graphml(G, graphml_path)
        return G
    if place is None and bbox is None:
        raise ValueError("Provide either an existing graphml_path or a place/bbox to download.")
    if place is not None:
        G = ox.graph_from_place(place, network_type=network_type)
    else:
        north, south, east, west = bbox  # type: ignore
        # OSMnx API changed across versions: some expect a single `bbox` kwarg
        # while older versions accept 4 positional args. Prefer the kw form.
        try:
            G = ox.graph_from_bbox(bbox=(north, south, east, west), network_type=network_type)
        except TypeError:
            G = ox.graph_from_bbox(north, south, east, west, network_type=network_type)
    if project:
        G = ox.project_graph(G)
        G.graph['crs_is_projected'] = True
    if save_if_download and graphml_path:
        os.makedirs(os.path.dirname(graphml_path), exist_ok=True)
        ox.save_graphml(G, graphml_path)
    return G
