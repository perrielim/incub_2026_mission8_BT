#!/usr/bin/env python3

"""
Generic BT.CPP XML compiler.

This compiler reads generated/compiled_bt_plan.yaml and renders:
- main_tree_to_execute
- reusable subtree templates
- explicit mission phases
- decorators, control nodes, actions, conditions
- recovery branch

It assumes planner_agent.py already resolved:
- root control policy
- per-agent defaults
- phase ordering
- decorator parameters
- mission blackboard values
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"YAML file is empty: {path}")
    return data


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def indent(level: int) -> str:
    return "  " * level


def render_attrs(attrs: dict[str, Any] | None) -> str:
    if not attrs:
        return ""
    parts = []
    for key, value in attrs.items():
        if isinstance(value, list):
            value = ",".join(str(v) for v in value)
        parts.append(f'{key}="{value}"')
    return " " + " ".join(parts)


def render_leaf(node: dict[str, Any], level: int) -> str:
    sp = indent(level)
    node_id = node["id"]
    attrs = node.get("ports", {})
    return f"{sp}<{node_id}{render_attrs(attrs)}/>"


def render_subtree(node: dict[str, Any], level: int) -> str:
    sp = indent(level)
    subtree_id = node["id"]
    bind = node.get("bind", {})
    return f'{sp}<SubTree ID="{subtree_id}"{render_attrs(bind)}/>'


def render_decorator(node: dict[str, Any], level: int) -> str:
    sp = indent(level)
    decorator_id = node["id"]
    params = node.get("params", {})
    child = render_node(node["child"], level + 1)
    return (
        f"{sp}<{decorator_id}{render_attrs(params)}>\n"
        f"{child}\n"
        f"{sp}</{decorator_id}>"
    )


def render_phase_body(phase: dict[str, Any], level: int) -> str:
    control = phase["control"]
    attrs: dict[str, Any] = {}

    if control == "Parallel":
        attrs["success_count"] = phase["success_count"]
        attrs["failure_count"] = phase["failure_count"]

    children = [render_node(node, level + 1) for node in phase["nodes"]]
    children_text = "\n".join(children)

    return (
        f"{indent(level)}<{control}{render_attrs(attrs)}>\n"
        f"{children_text}\n"
        f"{indent(level)}</{control}>"
    )


def render_template(template_id: str, template: dict[str, Any]) -> str:
    body = render_phase_body(
        {
            "control": template["control"],
            "nodes": template["nodes"],
        },
        1,
    )
    return (
        f'<BehaviorTree ID="{template_id}">\n'
        f"{body}\n"
        f"</BehaviorTree>"
    )


def render_phase(phase: dict[str, Any]) -> str:
    body = render_phase_body(phase, 1)

    if "timeout_msec" in phase:
        body = (
            f"{indent(1)}<Timeout msec=\"{phase['timeout_msec']}\">\n"
            f"{body}\n"
            f"{indent(1)}</Timeout>"
        )

    return (
        f'<BehaviorTree ID="{phase["id"]}">\n'
        f"{body}\n"
        f"</BehaviorTree>"
    )


def render_node(node: dict[str, Any], level: int) -> str:
    node_type = node["type"]

    if node_type in {"Action", "Condition"}:
        return render_leaf(node, level)

    if node_type == "SubTree":
        return render_subtree(node, level)

    if node_type == "Decorator":
        return render_decorator(node, level)

    raise ValueError(f"Unsupported node type '{node_type}' in compiler")


def render_main_tree(plan: dict[str, Any]) -> str:
    root_control = plan["root"]["control"]

    phase_refs = []
    for phase in plan["phases"]:
        phase_refs.append(f'{indent(4)}<SubTree ID="{phase["id"]}"/>')

    phase_sequence = (
        f'{indent(3)}<Sequence name="mission_sequence">\n'
        f'{"\n".join(phase_refs)}\n'
        f'{indent(3)}</Sequence>'
    )

    recovery_block = ""
    recovery = plan.get("recovery", {})
    if recovery.get("enabled"):
        recovery_nodes = "\n".join(
            render_node(node, 4) for node in recovery["nodes"]
        )
        recovery_block = (
            f"\n{indent(3)}<{recovery['control']} name=\"abort_or_recover\">\n"
            f"{recovery_nodes}\n"
            f"{indent(3)}</{recovery['control']}>"
        )

    return (
        '<BehaviorTree ID="MainMission">\n'
        f'{indent(1)}<{root_control} name="mission_root">\n'
        f"{phase_sequence}"
        f"{recovery_block}\n"
        f'{indent(1)}</{root_control}>\n'
        f"</BehaviorTree>"
    )


def render_xml(plan: dict[str, Any]) -> str:
    sections = [
        '<root BTCPP_format="4" main_tree_to_execute="MainMission">',
        "",
        render_main_tree(plan),
        "",
    ]

    for template_id, template in plan.get("subtree_templates", {}).items():
        sections.append(render_template(template_id, template))
        sections.append("")

    for phase in plan["phases"]:
        sections.append(render_phase(phase))
        sections.append("")

    sections.append("</root>")
    return "\n".join(sections)


def main() -> None:
    plan = load_yaml(GENERATED / "compiled_bt_plan.yaml")
    xml = render_xml(plan)
    write_text(GENERATED / "main_mission.xml", xml)
    print(f"Wrote {GENERATED / 'main_mission.xml'}")


if __name__ == "__main__":
    main()