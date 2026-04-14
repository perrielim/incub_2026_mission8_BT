#!/usr/bin/env python3

import argparse
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from itertools import count
from pathlib import Path


CONTROL_NODES = {
    "Sequence",
    "Fallback",
    "ReactiveSequence",
    "ReactiveFallback",
    "Parallel",
}

DECORATOR_NODES = {
    "Decorator",
    "Timeout",
    "RetryUntilSuccessful",
}


def clean_value(val: str) -> str:
    val = val.strip()
    if val.startswith("{") and val.endswith("}"):
        return f"[{val[1:-1]}]"
    return val


def xml_to_dot(xml_text: str) -> str:
    root = ET.fromstring(xml_text)

    main_tree_id = root.attrib.get("main_tree_to_execute")
    bt_map = {
        bt.attrib["ID"]: bt
        for bt in root.findall("BehaviorTree")
        if "ID" in bt.attrib
    }

    if not main_tree_id or main_tree_id not in bt_map:
        raise ValueError("Missing or invalid main_tree_to_execute")

    node_id_gen = count()

    lines = [
        "digraph BT {",
        '  graph [',
        '    rankdir=TB,',
        '    splines=false,',
        '    nodesep=0.95,',
        '    ranksep=1.15,',
        '    pad=0.35,',
        '    bgcolor="white"',
        '  ];',
        '  node [',
        '    shape=box,',
        '    style="rounded,filled",',
        '    fontname="Helvetica",',
        '    fontsize=11,',
        '    color="black"',
        '  ];',
        '  edge [',
        '    color="black",',
        '    penwidth=1.1',
        '  ];',
    ]

    def esc(text: str) -> str:
        return (
            text
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\\\\n", "\\n")
        )

    def short_tag(tag: str) -> str:
        return tag.split("_", 1)[1] if "_" in tag else tag

    def is_condition_node(elem) -> bool:
        if elem.attrib.get("node_type") == "condition":
            return True

        tag = elem.tag.lower()
        return (
            tag.startswith("condition_")
            or tag.startswith("is_")
            or tag.startswith("check_")
            or tag.startswith("has_")
            or tag.startswith("can_")
            or tag.startswith("should_")
        )

    def collect_relevant_attrs(elem) -> list[str]:
        attrs = []

        for key in (
            "agent_id",
            "agent_ids",
            "vehicle_id",
            "vehicle_ids",
            "asset_id",
            "asset_ids",
        ):
            if key in elem.attrib:
                attrs.append(clean_value(elem.attrib[key]))

        for key in (
            "target_id",
            "target_ids",
            "task",
            "goal",
            "area",
            "zone",
            "region",
            "waypoint",
            "waypoints",
            "source_vehicle",
            "target_vehicle",
            "platform",
            "platform_id",
        ):
            if key in elem.attrib:
                attrs.append(f"{key}={clean_value(elem.attrib[key])}")

        if "pose" in elem.attrib:
            attrs.append(f"pose={clean_value(elem.attrib['pose'])}")

        if "radius_m" in elem.attrib:
            attrs.append(f"r={clean_value(elem.attrib['radius_m'])}")

        if "altitude_m" in elem.attrib:
            attrs.append(f"alt={clean_value(elem.attrib['altitude_m'])}")

        if "speed_mps" in elem.attrib:
            attrs.append(f"v={clean_value(elem.attrib['speed_mps'])}")

        if "timeout_s" in elem.attrib:
            attrs.append(f"timeout={clean_value(elem.attrib['timeout_s'])}s")

        if "msec" in elem.attrib:
            attrs.append(f"{clean_value(elem.attrib['msec'])} ms")

        if "num_attempts" in elem.attrib:
            attrs.append(f"{clean_value(elem.attrib['num_attempts'])}x")

        return attrs

    def label(elem) -> str:
        tag = elem.tag
        name = elem.attrib.get("name")

        if tag in CONTROL_NODES:
            parts = ["[CONTROL]"]
            if name:
                parts.append(name)
                parts.append(f"({tag})")
            else:
                parts.append(tag)

            if tag == "Parallel":
                sc = elem.attrib.get("success_count")
                fc = elem.attrib.get("failure_count")
                if sc is not None:
                    parts.append(f"success={clean_value(sc)}")
                if fc is not None:
                    parts.append(f"fail={clean_value(fc)}")

            return "\n".join(parts)

        if tag in DECORATOR_NODES:
            parts = [f"[DECORATOR]\n{tag}"]
            if name:
                parts.append(f"name={clean_value(name)}")

            if tag == "Timeout":
                parts.append(f"msec={clean_value(elem.attrib.get('msec', '?'))}")
            elif tag == "RetryUntilSuccessful":
                parts.append(
                    f"num_attempts={clean_value(elem.attrib.get('num_attempts', '?'))}"
                )

            return "\n".join(parts)

        if tag == "SubTree":
            parts = [f"[SUBTREE]\n{clean_value(elem.attrib.get('ID', 'UNKNOWN'))}"]
            if name:
                parts.append(f"name={clean_value(name)}")
            return "\n".join(parts)

        if is_condition_node(elem):
            parts = [f"[COND]\n{short_tag(tag)}"]
            if name:
                parts.append(f"name={clean_value(name)}")
            parts.extend(collect_relevant_attrs(elem))
            return "\n".join(parts)

        parts = [f"[ACT]\n{short_tag(tag)}"]
        if name:
            parts.append(f"name={clean_value(name)}")
        parts.extend(collect_relevant_attrs(elem))
        return "\n".join(parts)

    def node_style(elem) -> dict[str, str]:
        tag = elem.tag

        if tag in {"Sequence", "ReactiveSequence"}:
            return {"fill": "#C8E6C9", "shape": "box", "penwidth": "1.8"}

        if tag in {"Fallback", "ReactiveFallback"}:
            return {"fill": "#FFCDD2", "shape": "box", "penwidth": "1.8"}

        if tag == "Parallel":
            return {"fill": "#E1BEE7", "shape": "box", "penwidth": "2.0"}

        if tag in DECORATOR_NODES:
            return {"fill": "#FFF9C4", "shape": "diamond", "penwidth": "1.5"}

        if tag == "SubTree":
            return {"fill": "#FFE082", "shape": "folder", "penwidth": "1.5"}

        if is_condition_node(elem):
            return {"fill": "#64B5F6", "shape": "ellipse", "penwidth": "1.6"}

        return {"fill": "#90CAF9", "shape": "box", "penwidth": "1.2"}

    def add_node(node_id: str, label_text: str, style: dict[str, str]) -> None:
        lines.append(
            f'  {node_id} [label="{esc(label_text)}", '
            f'fillcolor="{style["fill"]}", '
            f'shape="{style["shape"]}", '
            f'penwidth={style["penwidth"]}];'
        )

    def visit(elem, parent=None, stack=None):
        if stack is None:
            stack = set()

        my_id = f"n{next(node_id_gen)}"
        add_node(my_id, label(elem), node_style(elem))

        if parent is not None:
            lines.append(f"  {parent} -> {my_id};")

        if elem.tag == "SubTree":
            subtree_id = elem.attrib.get("ID")
            if not subtree_id:
                return my_id

            if subtree_id in stack:
                loop_id = f"n{next(node_id_gen)}"
                add_node(
                    loop_id,
                    f"RecursiveRef\n{clean_value(subtree_id)}",
                    {"fill": "#F8BBD0", "shape": "box", "penwidth": "1.2"},
                )
                lines.append(f"  {my_id} -> {loop_id};")
                return my_id

            subtree = bt_map.get(subtree_id)
            if subtree is None:
                missing_id = f"n{next(node_id_gen)}"
                add_node(
                    missing_id,
                    f"MissingTree\n{clean_value(subtree_id)}",
                    {"fill": "#EF9A9A", "shape": "box", "penwidth": "1.2"},
                )
                lines.append(f"  {my_id} -> {missing_id};")
                return my_id

            new_stack = set(stack)
            new_stack.add(subtree_id)

            child_ids = []
            for child in subtree:
                cid = visit(child, my_id, new_stack)
                child_ids.append(cid)

            if len(child_ids) > 1:
                lines.append("  { rank=same; " + "; ".join(child_ids) + "; }")

            return my_id

        child_ids = []
        for child in elem:
            cid = visit(child, my_id, stack)
            child_ids.append(cid)

        if len(child_ids) > 1:
            lines.append("  { rank=same; " + "; ".join(child_ids) + "; }")

        return my_id

    main_bt = bt_map[main_tree_id]
    root_id = f"n{next(node_id_gen)}"
    add_node(
        root_id,
        f"[ROOT]\n{clean_value(main_tree_id)}",
        {"fill": "#FFD54F", "shape": "box", "penwidth": "2.0"},
    )

    top_children = []
    for child in main_bt:
        cid = visit(child, root_id, {main_tree_id})
        top_children.append(cid)

    if len(top_children) > 1:
        lines.append("  { rank=same; " + "; ".join(top_children) + "; }")

    if len(top_children) == 2:
        lines.append(
            f"  {top_children[0]} -> {top_children[1]} "
            f'[style=invis, minlen=4];'
        )

    lines += [
        "",
        "  subgraph cluster_legend {",
        '    label="Legend";',
        '    fontname="Helvetica";',
        '    fontsize=12;',
        '    color="gray40";',
        '    style="rounded,dashed";',
        '    margin=16;',
        "",
        '    key_root [label="[ROOT]\\nMain tree", fillcolor="#FFD54F", shape="box", style="rounded,filled"];',
        '    key_seq [label="[CONTROL]\\nSequence / ReactiveSequence\\nname=<unique_name>", fillcolor="#C8E6C9", shape="box", style="rounded,filled"];',
        '    key_fb [label="[CONTROL]\\nFallback / ReactiveFallback\\nname=<unique_name>", fillcolor="#FFCDD2", shape="box", style="rounded,filled"];',
        '    key_par [label="[CONTROL]\\nParallel\\nname=<unique_name>", fillcolor="#E1BEE7", shape="box", style="rounded,filled"];',
        '    key_dec [label="[DECORATOR]\\nTimeout / Retry / Decorator", fillcolor="#FFF9C4", shape="diamond", style="filled"];',
        '    key_sub [label="[SUBTREE]\\nReferenced subtree", fillcolor="#FFE082", shape="folder", style="filled"];',
        '    key_act [label="[ACT]\\nAction node\\nrefs in [...]", fillcolor="#90CAF9", shape="box", style="rounded,filled"];',
        '    key_cond [label="[COND]\\nCondition node\\nrefs in [...]", fillcolor="#64B5F6", shape="ellipse", style="filled"];',
        "",
        "  }",
    ]

    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_file")
    parser.add_argument("-o", "--output", default="tree.svg")
    args = parser.parse_args()

    xml_text = Path(args.xml_file).read_text(encoding="utf-8")
    dot = xml_to_dot(xml_text)

    with tempfile.TemporaryDirectory() as tmp:
        dot_path = Path(tmp) / "tree.dot"
        out_path = Path(tmp) / args.output

        dot_path.write_text(dot, encoding="utf-8")

        fmt = Path(args.output).suffix.lstrip(".").lower()
        if not fmt:
            raise ValueError("Output file must have an extension, e.g. .svg or .png")

        subprocess.run(
            ["dot", f"-T{fmt}", str(dot_path), "-o", str(out_path)],
            check=True,
        )

        Path(args.output).write_bytes(out_path.read_bytes())

    print(f"✅ Generated: {args.output}")


if __name__ == "__main__":
    main()