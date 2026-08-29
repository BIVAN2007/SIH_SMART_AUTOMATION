"""
road_network.py
Global route planning layer -- the "Google Maps" part of the system.
Sits ABOVE the existing local planner (planner.py) and does not replace
it: this module answers "which sequence of roads gets me from A to B,
avoiding roads other cars have flagged as bad?"; planner.py still
handles moment-to-moment obstacle/collision avoidance once the car is
actually driving a given road.

Deliberately a small, self-contained synthetic graph rather than a
real-world map import (OpenStreetMap etc.) -- no external data file,
no API key, nothing extra to configure on Railway. Swap in real map
data later by replacing ROAD_NETWORK with nodes/edges loaded from OSM;
everything downstream (cost penalties, Dijkstra, the API endpoint)
stays the same.

condition_type severities:
  JAM            -> large penalty, strongly avoided if any alternative exists
  ACCIDENT       -> largest penalty, strongly avoided
  CONSTRUCTION   -> large penalty
  POTHOLE        -> moderate penalty, car will still use the road if it's
                     clearly the best option, just prefers a smoother one
  BUMPY_ROAD     -> small-moderate penalty
"""
from __future__ import annotations
import networkx as nx

# name -> {length (km), connects to: {neighbor: length}}
# A small demo town layout: a direct road through a market area, plus
# a longer bypass, so jam/pothole avoidance actually has somewhere to go.
ROAD_NETWORK: dict[str, dict[str, float]] = {
    "Road_A":      {"Road_B": 1.0, "Road_C": 1.0},
    "Road_B":      {"Road_D": 1.5},   # direct route, passes the market
    "Road_C":      {"Road_D": 2.2},   # bypass, longer but avoids the market
    "Road_D":      {"Road_E": 1.0, "Road_F": 1.0},
    "Road_E":      {"Road_G": 1.2},
    "Road_F":      {"Road_G": 1.6},
    "Road_G":      {},
}

CONDITION_WEIGHT = {
    "ACCIDENT": 8.0,
    "CONSTRUCTION": 6.0,
    "JAM": 5.0,
    "BUMPY_ROAD": 1.5,
    "POTHOLE": 1.0,
}


def _penalty_for(road_id: str, conditions: list[dict]) -> tuple[float, list[str]]:
    """Total extra cost for road_id given a list of active condition dicts
    (each with road_id/condition_type/severity). Returns (penalty, labels)."""
    penalty = 0.0
    labels = []
    for c in conditions:
        if c["road_id"] != road_id:
            continue
        weight = CONDITION_WEIGHT.get(c["condition_type"], 3.0)
        penalty += weight * max(0.0, min(1.0, c["severity"]))
        labels.append(c["condition_type"])
    return penalty, labels


def build_graph(active_conditions: list[dict]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for road_id, edges in ROAD_NETWORK.items():
        penalty, _ = _penalty_for(road_id, active_conditions)
        for neighbor, base_length in edges.items():
            graph.add_edge(road_id, neighbor, weight=base_length + penalty)
    return graph


def calculate_route(start: str, destination: str, active_conditions: list[dict]) -> dict:
    """Returns {path, total_cost, avoided} where `avoided` lists roads
    that had an active condition and were routed around (i.e. excluded
    from the chosen path despite existing in the network)."""
    if start not in ROAD_NETWORK or destination not in ROAD_NETWORK:
        raise ValueError(f"Unknown road id(s): {start}, {destination}")

    graph = build_graph(active_conditions)
    try:
        path = nx.dijkstra_path(graph, start, destination, weight="weight")
        total_cost = nx.dijkstra_path_length(graph, start, destination, weight="weight")
    except nx.NetworkXNoPath:
        return {"start": start, "destination": destination, "path": [], "total_cost": -1, "avoided": []}

    flagged_roads = {c["road_id"] for c in active_conditions}
    avoided = sorted(r for r in flagged_roads if r in ROAD_NETWORK and r not in path)

    return {"start": start, "destination": destination, "path": path,
            "total_cost": round(total_cost, 2), "avoided": avoided}
