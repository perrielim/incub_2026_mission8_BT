#!/usr/bin/env python3

# Agentic planner layer.
# The user provides mission intent only.
# This script:
# - validates the mission
# - fills inferred defaults (sensor mode, search pattern, root control)
# - resolves execution values (timeouts, retry count, battery thresholds)
# - emits a richer compiled_bt_plan.yaml for the BT compiler

from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "configs"
GENERATED = ROOT / "generated"

TASK_TO_ACTION = {
    "go_to_area": "GoToArea",
    "search": "SearchArea",
    "patrol": "SearchArea",
    "handoff_target": "HandoffTarget",
    "track": "TrackTarget",
    "encircle": "EncircleTarget",
    "return_home": "ReturnHome",
}

REQUIRED_TASK_PARAMS = {
    "go_to_area": ["area_id"],
    "search": [],
    "patrol": ["area_id"],
    "handoff_target": [],
    "track": [],
    "encircle": ["radius_m", "standoff_m"],
    "return_home": [],
}

INVALID_DOMAIN_TASKS = {
    ("sea", "go_to_altitude"),
    ("air", "dive_to_depth"),
    ("land", "dive_to_depth"),
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"YAML file is empty: {path}")
    return data


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def fleet_by_id(mission: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {vehicle["id"]: vehicle for vehicle in mission["fleet"]}


def get_task(mission: dict[str, Any], task_type: str) -> dict[str, Any] | None:
    for task in mission["tasks"]:
        if task["type"] == task_type:
            return task
    return None


def validate_assigned_agents(mission: dict[str, Any]) -> None:
    known_ids = {vehicle["id"] for vehicle in mission["fleet"]}
    for task in mission["tasks"]:
        for agent_id in task.get("assigned_to", []):
            if agent_id not in known_ids:
                raise ValueError(
                    f"Task '{task['id']}' references unknown vehicle '{agent_id}'"
                )


def validate_required_params(mission: dict[str, Any]) -> None:
    for task in mission["tasks"]:
        required = REQUIRED_TASK_PARAMS.get(task["type"], [])
        params = task.get("params", {})
        for name in required:
            if name not in params:
                raise ValueError(
                    f"Task '{task['id']}' of type '{task['type']}' "
                    f"is missing required param '{name}'"
                )


def validate_task_support(mission: dict[str, Any], catalog: dict[str, Any]) -> None:
    fleet = fleet_by_id(mission)
    for task in mission["tasks"]:
        required_action = TASK_TO_ACTION.get(task["type"])
        if required_action is None:
            raise ValueError(f"Unsupported task type '{task['type']}'")

        for agent_id in task.get("assigned_to", []):
            platform_type = fleet[agent_id]["platform_type"]
            platform_type = fleet[agent_id]["platform_type"]
            platform_entry = catalog["platforms"].get(platform_type)
            if platform_entry is None:
                raise ValueError(
                    f"Agent '{agent_id}' uses unknown platform_type '{platform_type}'. "
                    f"Add it to platform_catalog.yaml"
                )
            supported = catalog["platforms"][platform_type]["supports_actions"]
            if required_action not in supported:
                raise ValueError(
                    f"Task '{task['id']}' requires action '{required_action}', "
                    f"but platform '{platform_type}' for agent '{agent_id}' "
                    f"does not support it"
                )


def validate_task_domain_combos(mission: dict[str, Any]) -> None:
    fleet = fleet_by_id(mission)
    for task in mission["tasks"]:
        for agent_id in task.get("assigned_to", []):
            domain = fleet[agent_id]["domain"]
            combo = (domain, task["type"])
            if combo in INVALID_DOMAIN_TASKS:
                raise ValueError(
                    f"Task '{task['type']}' is invalid for domain '{domain}' "
                    f"(agent '{agent_id}')"
                )


def validate_mission(mission: dict[str, Any], catalog: dict[str, Any]) -> None:
    validate_assigned_agents(mission)
    validate_required_params(mission)
    validate_task_support(mission, catalog)
    validate_task_domain_combos(mission)


def resolve_root_control(mission: dict[str, Any], catalog: dict[str, Any]) -> str:
    priority = mission["constraints"]["soft"]["priority"]
    if priority == "safety":
        return catalog["policy"]["if_priority_safety_root"]
    return "Fallback"


def resolve_blackboard(mission: dict[str, Any]) -> dict[str, Any]:
    go_to_area_task = get_task(mission, "go_to_area")
    mission_area = ""
    if go_to_area_task is not None:
        mission_area = go_to_area_task.get("params", {}).get("area_id", "")

    return {
        "mission_area": mission_area,
        "target_id": "",
        "geofence_id": mission["environment"]["geofence"]["polygon_id"],
        "restricted_zone_list": mission["environment"]["restricted_zones"],
    }


def resolve_timeouts_ms(mission: dict[str, Any]) -> dict[str, int]:
    return {
        task_name: int(timeout_s * 1000)
        for task_name, timeout_s in mission["tuning"]["timeout_s"].items()
    }


def resolve_vehicle_defaults(
    mission: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    vehicles: dict[str, dict[str, Any]] = {}
    time_of_day = mission["environment"]["time_of_day"]

    for vehicle in mission["fleet"]:
        vehicle_id = vehicle["id"]
        platform_type = vehicle["platform_type"]
        entry = catalog["platforms"].get(platform_type)
        if entry is None:
            raise ValueError(
                f"Unknown platform_type '{platform_type}' for vehicle '{vehicle_id}'. "
                f"Add it to platform_catalog.yaml"
            )

        defaults = entry.get("defaults", {})
        limits = entry.get("limits", {})

        sensor_mode = defaults.get("sensor_mode", {}).get(time_of_day)
        search_pattern = defaults.get("search_pattern")
        min_battery_pct = float(
            limits.get(
                "min_battery_abort_pct",
                mission["constraints"]["hard"].get("min_battery_abort_pct", 20.0),
            )
        )

        vehicle_info = {
            "domain": vehicle["domain"],
            "platform_type": platform_type,
            "role": vehicle["role"],
            "sensor_mode": sensor_mode,
            "min_battery_pct": min_battery_pct,
            "supported_actions": entry["supports_actions"],
        }
        if search_pattern is not None:
            vehicle_info["search_pattern"] = search_pattern

        vehicles[vehicle_id] = vehicle_info

    return vehicles


def build_common_safety_template() -> dict[str, Any]:
    return {
        "control": "Sequence",
        "nodes": [
            {
                "type": "Condition",
                "id": "BatteryOK",
                "ports": {
                    "vehicle_id": "{vehicle_id}",
                    "min_battery_pct": "{min_battery_pct}",
                },
            },
            {
                "type": "Condition",
                "id": "WithinGeofence",
                "ports": {
                    "vehicle_id": "{vehicle_id}",
                    "geofence_id": "{geofence_id}",
                },
            },
            {
                "type": "Condition",
                "id": "OutsideRestrictedZone",
                "ports": {
                    "vehicle_id": "{vehicle_id}",
                    "restricted_zone_list": "{restricted_zone_list}",
                },
            },
        ],
    }


def build_detect_phase(
    mission: dict[str, Any],
    vehicles: dict[str, dict[str, Any]],
    blackboard: dict[str, Any],
    timeouts_ms: dict[str, int],
    retry_count: int,
) -> dict[str, Any]:
    search_task = get_task(mission, "search")
    go_to_area_task = get_task(mission, "go_to_area")
    if search_task is None or go_to_area_task is None:
        raise ValueError("Mission requires both 'go_to_area' and 'search' tasks")

    uav_id = search_task["assigned_to"][0]
    uav = vehicles[uav_id]

    return {
        "id": "UAV_Search",
        "control": "Sequence",
        "dependencies": [],
        "assigned_agents": [uav_id],
        "nodes": [
            {
                "type": "SubTree",
                "id": "CommonSafety",
                "bind": {
                    "vehicle_id": uav_id,
                    "min_battery_pct": uav["min_battery_pct"],
                    "geofence_id": "{geofence_id}",
                    "restricted_zone_list": "{restricted_zone_list}",
                },
            },
            {
                "type": "Decorator",
                "id": "Timeout",
                "params": {"msec": timeouts_ms["go_to_area"]},
                "child": {
                    "type": "Action",
                    "id": "GoToArea",
                    "ports": {
                        "vehicle_id": uav_id,
                        "area_id": "{mission_area}",
                    },
                },
            },
            {
                "type": "Decorator",
                "id": "RetryUntilSuccessful",
                "params": {"num_attempts": retry_count},
                "child": {
                    "type": "Decorator",
                    "id": "Timeout",
                    "params": {"msec": timeouts_ms["search"]},
                    "child": {
                        "type": "Action",
                        "id": "SearchArea",
                        "ports": {
                            "vehicle_id": uav_id,
                            "area_id": "{mission_area}",
                            "pattern": uav.get("search_pattern", "lawnmower"),
                            "sensor_mode": uav["sensor_mode"],
                        },
                    },
                },
            },
            {
                "type": "Condition",
                "id": "TargetDetected",
                "ports": {
                    "source_vehicle": uav_id,
                    "target_id": "{target_id}",
                },
            },
        ],
    }


def build_track_phase(
    mission: dict[str, Any],
    vehicles: dict[str, dict[str, Any]],
    timeouts_ms: dict[str, int],
) -> dict[str, Any]:
    handoff_task = get_task(mission, "handoff_target")
    track_task = get_task(mission, "track")
    if handoff_task is None or track_task is None:
        raise ValueError("Mission requires both 'handoff_target' and 'track' tasks")

    usv_id = track_task["assigned_to"][0]
    usv = vehicles[usv_id]

    return {
        "id": "USV_Track",
        "control": "Sequence",
        "dependencies": ["UAV_Search"],
        "assigned_agents": [usv_id],
        "nodes": [
            {
                "type": "SubTree",
                "id": "CommonSafety",
                "bind": {
                    "vehicle_id": usv_id,
                    "min_battery_pct": usv["min_battery_pct"],
                    "geofence_id": "{geofence_id}",
                    "restricted_zone_list": "{restricted_zone_list}",
                },
            },
            {
                "type": "Decorator",
                "id": "Timeout",
                "params": {"msec": timeouts_ms["handoff_target"]},
                "child": {
                    "type": "Action",
                    "id": "HandoffTarget",
                    "ports": {
                        "vehicle_id": usv_id,
                        "target_id": "{target_id}",
                    },
                },
            },
            {
                "type": "Condition",
                "id": "TargetAssigned",
                "ports": {
                    "vehicle_id": usv_id,
                    "target_id": "{target_id}",
                },
            },
            {
                "type": "Decorator",
                "id": "Timeout",
                "params": {"msec": timeouts_ms["track"]},
                "child": {
                    "type": "Action",
                    "id": "TrackTarget",
                    "ports": {
                        "vehicle_id": usv_id,
                        "target_id": "{target_id}",
                    },
                },
            },
            {
                "type": "Condition",
                "id": "TrackStable",
                "ports": {
                    "vehicle_id": usv_id,
                    "target_id": "{target_id}",
                },
            },
        ],
    }


def build_encircle_phase(
    mission: dict[str, Any],
    timeouts_ms: dict[str, int],
) -> dict[str, Any]:
    encircle_task = get_task(mission, "encircle")
    if encircle_task is None:
        raise ValueError("Mission requires an 'encircle' task")

    assigned = encircle_task["assigned_to"]
    params = encircle_task["params"]

    nodes = []
    for agent_id in assigned:
        nodes.append(
            {
                "type": "Action",
                "id": "EncircleTarget",
                "ports": {
                    "vehicle_id": agent_id,
                    "target_id": "{target_id}",
                    "radius_m": params["radius_m"],
                    "standoff_m": params["standoff_m"],
                },
            }
        )

    return {
        "id": "Joint_Encircle",
        "control": "Parallel",
        "dependencies": ["USV_Track"],
        "assigned_agents": assigned,
        "timeout_msec": timeouts_ms["encircle"],
        "success_count": len(assigned),
        "failure_count": 1,
        "nodes": nodes,
    }


def build_recovery_policy(mission: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    for vehicle in mission["fleet"]:
        nodes.append(
            {
                "type": "Action",
                "id": "ReturnHome",
                "ports": {"vehicle_id": vehicle["id"]},
            }
        )

    return {
        "enabled": True,
        "control": "Sequence",
        "mode": "return_home_all",
        "nodes": nodes,
    }


def build_compiled_plan(mission: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    validate_mission(mission, catalog)

    blackboard = resolve_blackboard(mission)
    vehicles = resolve_vehicle_defaults(mission, catalog)
    timeouts_ms = resolve_timeouts_ms(mission)
    retry_count = mission["tuning"]["retry_count"]
    tick_hz = mission["tuning"]["tick_hz"]

    phases = [
        build_detect_phase(mission, vehicles, blackboard, timeouts_ms, retry_count),
        build_track_phase(mission, vehicles, timeouts_ms),
        build_encircle_phase(mission, timeouts_ms),
    ]

    return {
        "mission_id": mission["mission"]["id"],
        "root": {
            "control": resolve_root_control(mission, catalog),
        },
        "blackboard": blackboard,
        "defaults": {
            "retry_count": retry_count,
            "tick_hz": tick_hz,
        },
        "vehicles": vehicles,
        "timeouts_ms": timeouts_ms,
        "subtree_templates": {
            "CommonSafety": build_common_safety_template(),
        },
        "phases": phases,
        "recovery": build_recovery_policy(mission),
    }


def main() -> None:
    mission = load_yaml(CONFIGS / "mission_spec.yaml")
    catalog = load_yaml(CONFIGS / "platform_catalog.yaml")

    compiled = build_compiled_plan(mission, catalog)
    save_yaml(GENERATED / "compiled_bt_plan.yaml", compiled)
    print(f"Wrote {GENERATED / 'compiled_bt_plan.yaml'}")


if __name__ == "__main__":
    main()