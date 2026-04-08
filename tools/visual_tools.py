"""
Visual tools — schema-driven multimodal visual rendering via RPC.

This module introduces a single additive tool, `render_visual`, that validates
strict visualization schemas and forwards canonical payloads to the frontend.
"""

import json
import logging
from typing import Any

from livekit.agents import RunContext, function_tool

from helpers.room_utils import get_frontend_identity, send_rpc

logger = logging.getLogger("agent-UnlockPi")


_SUPPORTED_TYPES = {"map", "chart", "flow", "graph"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _ensure_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def _ensure_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _ensure_only_keys(value: dict[str, Any], allowed: set[str], path: str) -> None:
    extra = set(value.keys()) - allowed
    if extra:
        raise ValueError(f"{path} contains unsupported fields: {sorted(extra)}")


def _validate_map_schema(payload: dict[str, Any]) -> None:
    required = {"type", "title", "locations", "connections", "animation"}
    _ensure_only_keys(payload, required, "map payload")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        raise ValueError("map.title must be a non-empty string")

    locations = _ensure_list(payload.get("locations"), "map.locations")
    for index, loc in enumerate(locations):
        item = _ensure_object(loc, f"map.locations[{index}]")
        _ensure_only_keys(item, {"name", "lat", "lng"}, f"map.locations[{index}]")
        if not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError(f"map.locations[{index}].name must be a non-empty string")
        if not _is_number(item.get("lat")):
            raise ValueError(f"map.locations[{index}].lat must be a number")
        if not _is_number(item.get("lng")):
            raise ValueError(f"map.locations[{index}].lng must be a number")

    connections = _ensure_list(payload.get("connections"), "map.connections")
    for index, point in enumerate(connections):
        row = _ensure_list(point, f"map.connections[{index}]")
        if len(row) != 2 or not _is_number(row[0]) or not _is_number(row[1]):
            raise ValueError(
                f"map.connections[{index}] must be [lat, lng] with numeric values"
            )

    animation = _ensure_object(payload.get("animation"), "map.animation")
    _ensure_only_keys(animation, {"type", "speed"}, "map.animation")
    if animation.get("type") != "route":
        raise ValueError("map.animation.type must be 'route'")
    if not _is_number(animation.get("speed")) or animation["speed"] <= 0:
        raise ValueError("map.animation.speed must be a positive number")


def _validate_chart_schema(payload: dict[str, Any]) -> None:
    required = {"type", "chartType", "labels", "values", "animation"}
    _ensure_only_keys(payload, required, "chart payload")
    if payload.get("chartType") not in {"bar", "line", "pie"}:
        raise ValueError("chart.chartType must be one of: bar, line, pie")

    labels = _ensure_list(payload.get("labels"), "chart.labels")
    values = _ensure_list(payload.get("values"), "chart.values")
    if len(labels) != len(values):
        raise ValueError("chart.labels and chart.values must have the same length")

    for index, label in enumerate(labels):
        if not isinstance(label, str):
            raise ValueError(f"chart.labels[{index}] must be a string")

    for index, value in enumerate(values):
        if not _is_number(value):
            raise ValueError(f"chart.values[{index}] must be a number")

    animation = _ensure_object(payload.get("animation"), "chart.animation")
    _ensure_only_keys(animation, {"type", "duration"}, "chart.animation")
    if animation.get("type") != "grow":
        raise ValueError("chart.animation.type must be 'grow'")
    if not _is_number(animation.get("duration")) or animation["duration"] <= 0:
        raise ValueError("chart.animation.duration must be a positive number")


def _validate_flow_schema(payload: dict[str, Any]) -> None:
    required = {"type", "nodes", "edges", "animation"}
    _ensure_only_keys(payload, required, "flow payload")

    nodes = _ensure_list(payload.get("nodes"), "flow.nodes")
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        item = _ensure_object(node, f"flow.nodes[{index}]")
        _ensure_only_keys(item, {"id", "label"}, f"flow.nodes[{index}]")
        node_id = item.get("id")
        label = item.get("label")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError(f"flow.nodes[{index}].id must be a non-empty string")
        if not isinstance(label, str):
            raise ValueError(f"flow.nodes[{index}].label must be a string")
        if node_id in node_ids:
            raise ValueError(f"Duplicate flow node id: {node_id}")
        node_ids.add(node_id)

    edges = _ensure_list(payload.get("edges"), "flow.edges")
    for index, edge in enumerate(edges):
        item = _ensure_object(edge, f"flow.edges[{index}]")
        _ensure_only_keys(item, {"from", "to"}, f"flow.edges[{index}]")
        from_id = item.get("from")
        to_id = item.get("to")
        if not isinstance(from_id, str) or not isinstance(to_id, str):
            raise ValueError(f"flow.edges[{index}] requires string from/to")
        if from_id not in node_ids or to_id not in node_ids:
            raise ValueError(
                f"flow.edges[{index}] references unknown node id (from={from_id}, to={to_id})"
            )

    animation = _ensure_object(payload.get("animation"), "flow.animation")
    _ensure_only_keys(animation, {"type", "delay"}, "flow.animation")
    if animation.get("type") != "step":
        raise ValueError("flow.animation.type must be 'step'")
    if not _is_number(animation.get("delay")) or animation["delay"] <= 0:
        raise ValueError("flow.animation.delay must be a positive number")


def _validate_graph_schema(payload: dict[str, Any]) -> None:
    required = {"type", "nodes", "edges", "layout", "animation"}
    _ensure_only_keys(payload, required, "graph payload")
    if payload.get("layout") != "force":
        raise ValueError("graph.layout must be 'force'")

    nodes = _ensure_list(payload.get("nodes"), "graph.nodes")
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        item = _ensure_object(node, f"graph.nodes[{index}]")
        _ensure_only_keys(item, {"id", "label"}, f"graph.nodes[{index}]")
        node_id = item.get("id")
        label = item.get("label")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError(f"graph.nodes[{index}].id must be a non-empty string")
        if not isinstance(label, str):
            raise ValueError(f"graph.nodes[{index}].label must be a string")
        if node_id in node_ids:
            raise ValueError(f"Duplicate graph node id: {node_id}")
        node_ids.add(node_id)

    edges = _ensure_list(payload.get("edges"), "graph.edges")
    for index, edge in enumerate(edges):
        item = _ensure_object(edge, f"graph.edges[{index}]")
        _ensure_only_keys(item, {"source", "target"}, f"graph.edges[{index}]")
        source = item.get("source")
        target = item.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError(f"graph.edges[{index}] requires string source/target")
        if source not in node_ids or target not in node_ids:
            raise ValueError(
                f"graph.edges[{index}] references unknown node id (source={source}, target={target})"
            )

    animation = _ensure_object(payload.get("animation"), "graph.animation")
    _ensure_only_keys(animation, {"type"}, "graph.animation")
    if animation.get("type") != "expand":
        raise ValueError("graph.animation.type must be 'expand'")


def _normalize_visual_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a canonical visual payload matching one of the supported schemas."""
    raw = dict(payload)

    # Accept either direct schema payload or RPC wrapper shape: {type, data}
    if "data" in raw and isinstance(raw["data"], dict):
        data = dict(raw["data"])
        if "type" not in data and "type" in raw:
            data["type"] = raw["type"]
        raw = data

    visual_type = raw.get("type")
    if visual_type not in _SUPPORTED_TYPES:
        raise ValueError("payload.type must be one of: map, chart, flow, graph")

    return raw


def _validate_visual_payload(payload: dict[str, Any]) -> bool:
    """Validate a normalized visual payload against strict schemas."""
    visual_type = payload["type"]
    if visual_type == "map":
        _validate_map_schema(payload)
    elif visual_type == "chart":
        _validate_chart_schema(payload)
    elif visual_type == "flow":
        _validate_flow_schema(payload)
    elif visual_type == "graph":
        _validate_graph_schema(payload)
    else:
        raise ValueError(f"Unsupported visual type: {visual_type}")
    return True


@function_tool()
async def render_visual(
    context: RunContext,
    visual_json: str,
) -> str:
    """Render a schema-driven visual on the frontend.

    Use this tool only for strict visual schemas and pass a JSON string.

    Supported schema types:
    - map: {type, title, locations[], connections[], animation{type='route',speed}}
    - chart: {type, chartType, labels[], values[], animation{type='grow',duration}}
    - flow: {type, nodes[], edges[], animation{type='step',delay}}
    - graph: {type, nodes[], edges[], layout='force', animation{type='expand'}}

    The schema structure is fixed. Populate data fields only.
    """
    frontend_id = get_frontend_identity()
    if not frontend_id:
        return "Could not find the classroom display."

    try:
        payload = json.loads(visual_json) if isinstance(visual_json, str) else visual_json
        if not isinstance(payload, dict):
            return "Invalid visual payload: expected a JSON object."

        normalized = _normalize_visual_payload(payload)
        _validate_visual_payload(normalized)

        rpc_payload = {"type": normalized["type"], "data": normalized}
        await send_rpc("render_visual", rpc_payload, frontend_id=frontend_id)
        return f"Rendered {normalized['type']} visual successfully."

    except Exception as e:
        logger.error(f"render_visual failed: {e}")
        return f"Failed to render visual: {str(e)}"
