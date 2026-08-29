"""
road_network.py
Global route planning layer -- the "Google Maps" part of the system.
Sits ABOVE the existing local planner (planner.py) and does not replace
it: this module answers "which sequence of roads gets me from A to B,
avoiding roads other cars have flagged as bad?"; planner.py still
handles moment-to-moment obstacle/collision avoidance once the car is
actually driving a given road.

LOCATIONS are real, named places in Kolkata with real approximate
coordinates, so the frontend can plot them on an actual OpenStreetMap
tile layer (via Leaflet) -- this is not a synthetic grid. ROADS are the
real-world stretches connecting them; each road is what actually gets
flagged as jammed/potholed, at the coordinates of its two endpoints,
so a reported jam plots as an actual line segment on the map.

Honest limitation: this is a curated set of ~14 well-known Kolkata
landmarks/areas, not a full street-level import of every road in the
city (that would need a live OpenStreetMap/osmnx data pull, which this
environment can't do). The map tiles themselves are 100% real OSM data,
rendered live in the browser -- only the routing graph is hand-curated.
Swap LOCATIONS/ROADS for an osmnx-exported graph later; nothing else
in this file, or the API layer that calls it, needs to change.
"""
from __future__ import annotations
import networkx as nx

# id -> {name, lat, lng}
LOCATIONS: dict[str, dict] = {
    "esplanade":      {"name": "Esplanade",               "lat": 22.5626, "lng": 88.3529},
    "park_street":    {"name": "Park Street",              "lat": 22.5535, "lng": 88.3529},
    "howrah_bridge":  {"name": "Howrah Bridge",            "lat": 22.5851, "lng": 88.3468},
    "sealdah":        {"name": "Sealdah",                  "lat": 22.5675, "lng": 88.3706},
    "maidan":         {"name": "Maidan",                   "lat": 22.5550, "lng": 88.3450},
    "park_circus":    {"name": "Park Circus",              "lat": 22.5423, "lng": 88.3717},
    "ballygunge":     {"name": "Ballygunge",               "lat": 22.5308, "lng": 88.3639},
    "gariahat":       {"name": "Gariahat",                 "lat": 22.5186, "lng": 88.3671},
    "rashbehari":     {"name": "Rashbehari",               "lat": 22.5186, "lng": 88.3554},
    "em_bypass":      {"name": "EM Bypass (Science City)", "lat": 22.5320, "lng": 88.3936},
    "salt_lake":      {"name": "Salt Lake Sector V",       "lat": 22.5744, "lng": 88.4338},
    "new_town":       {"name": "New Town",                 "lat": 22.5809, "lng": 88.4645},
    "shyambazar":     {"name": "Shyambazar",               "lat": 22.5983, "lng": 88.3719},
    "dum_dum":        {"name": "Dum Dum",                  "lat": 22.6420, "lng": 88.4200},
}

# (location_a, location_b, approx length in km) -- undirected: a road can be
# driven either way. road id is derived automatically as "a__b".
_ROAD_EDGES: list[tuple[str, str, float]] = [
    ("esplanade", "park_street", 1.2),
    ("esplanade", "howrah_bridge", 1.5),
    ("esplanade", "sealdah", 2.0),
    ("esplanade", "maidan", 1.0),
    ("maidan", "park_street", 1.0),
    ("park_street", "park_circus", 2.5),
    ("park_street", "ballygunge", 3.0),
    ("park_circus", "em_bypass", 2.0),
    ("park_circus", "gariahat", 3.5),
    ("park_circus", "sealdah", 2.5),
    ("ballygunge", "gariahat", 1.5),
    ("gariahat", "rashbehari", 1.0),
    ("em_bypass", "new_town", 8.0),
    ("em_bypass", "salt_lake", 5.0),
    ("salt_lake", "new_town", 4.0),
    ("salt_lake", "dum_dum", 6.0),
    ("sealdah", "shyambazar", 3.0),
    ("shyambazar", "dum_dum", 5.0),
    ("howrah_bridge", "shyambazar", 4.0),
]

CONDITION_WEIGHT = {
    "ACCIDENT": 12.0,
    "CONSTRUCTION": 8.0,
    "JAM": 6.0,
    "BUMPY_ROAD": 1.0,
    "POTHOLE": 0.6,
}


def road_id(a: str, b: str) -> str:
    return f"{a}__{b}" if a < b else f"{b}__{a}"


_road_id = road_id  # internal alias used throughout this module


def get_locations() -> list[dict]:
    return [{"id": loc_id, **data} for loc_id, data in LOCATIONS.items()]


def get_roads() -> list[dict]:
    """Every road, for populating a 'report a condition' picker with real
    names like 'Esplanade to Park Street' instead of raw ids."""
    roads = []
    for a, b, length_km in _ROAD_EDGES:
        roads.append({
            "id": _road_id(a, b),
            "from_id": a, "to_id": b,
            "from_name": LOCATIONS[a]["name"], "to_name": LOCATIONS[b]["name"],
            "length_km": length_km,
        })
    return roads


def _penalty_for(road_id: str, conditions: list[dict]) -> float:
    penalty = 0.0
    for c in conditions:
        if c["road_id"] != road_id:
            continue
        weight = CONDITION_WEIGHT.get(c["condition_type"], 3.0)
        penalty += weight * max(0.0, min(1.0, c["severity"]))
    return penalty


def build_graph(active_conditions: list[dict]) -> nx.Graph:
    graph = nx.Graph()
    for a, b, length_km in _ROAD_EDGES:
        road_id = _road_id(a, b)
        penalty = _penalty_for(road_id, active_conditions)
        graph.add_edge(a, b, weight=length_km + penalty, road_id=road_id, length_km=length_km)
    return graph


def calculate_route(start: str, destination: str, active_conditions: list[dict]) -> dict:
    """Returns node path, the real road_ids actually used, and which
    flagged roads were routed around (avoided)."""
    if start not in LOCATIONS or destination not in LOCATIONS:
        raise ValueError(f"Unknown location id(s): {start}, {destination}")

    graph = build_graph(active_conditions)
    try:
        node_path = nx.dijkstra_path(graph, start, destination, weight="weight")
        total_cost = nx.dijkstra_path_length(graph, start, destination, weight="weight")
    except nx.NetworkXNoPath:
        return {"start": start, "destination": destination, "path": [], "path_names": [],
                "road_ids": [], "total_cost": -1, "avoided": []}

    road_ids_used = [graph[node_path[i]][node_path[i + 1]]["road_id"] for i in range(len(node_path) - 1)]
    flagged_roads = {c["road_id"] for c in active_conditions}
    avoided = sorted(r for r in flagged_roads if r not in road_ids_used and any(
        _road_id(a, b) == r for a, b, _ in _ROAD_EDGES))

    return {
        "start": start, "destination": destination,
        "path": node_path,
        "path_names": [LOCATIONS[n]["name"] for n in node_path],
        "road_ids": road_ids_used,
        "total_cost": round(total_cost, 2),
        "avoided": avoided,
    }
