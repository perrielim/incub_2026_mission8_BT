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
    "Decorator",
    "Timeout",
    "RetryUntilSuccessful",
}


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
        '    nodesep=0.9,',
        '    ranksep=1.2,',
        '    pad=0.35,',
        '    bgcolor="white"',
        '  ];',
        '  node [',
        '    shape=box,',
        '    style="rounded,filled",',
        '    fillcolor="lightsteelblue1",',
        '    color="black",',
        '    fontname="Helvetica",',
        '    fontsize=11,',
        '    margin="0.18,0.10"',
        '  ];',
        '  edge [',
        '    color="black",',
        '    penwidth=1.1',
        '  ];',
    ]

    def esc(text: str) -> str:
        return (
            text
            .replace("\\", "\\\\")   # keep this
            .replace('"', '\\"')     # keep this
            .replace("\\\\n", "\\n") # 🔥 undo double-escaped newline
        )

    def short_tag(tag: str) -> str:
        # navigation_NavigateToPose -> NavigateToPose
        # controller_CommandLand -> CommandLand
        # exploration_GetSearchArea -> GetSearchArea
        if "_" in tag:
            return tag.split("_", 1)[1]
        return tag

    def label(elem) -> str:
        tag = elem.tag

        if tag == "SubTree":
            subtree_id = elem.attrib.get("ID", "UNKNOWN")
            name = elem.attrib.get("name")
            return name if name else subtree_id

        name = elem.attrib.get("name")
        if name:
            return name

        if tag == "Parallel":
            sc = elem.attrib.get("success_count", "?")
            fc = elem.attrib.get("failure_count", "?")
            return f"Parallel\nsuccess={sc} fail={fc}"

        if tag == "Timeout":
            msec = elem.attrib.get("msec", "?")
            return f"Timeout\n{msec} ms"

        if tag == "RetryUntilSuccessful":
            n = elem.attrib.get("num_attempts", "?")
            return f"RetryUntilSuccessful\\n{n} attempts"

        base = short_tag(tag)
        parts = [base]

        if "agent_id" in elem.attrib:
            parts.append(elem.attrib["agent_id"])
        elif "vehicle_id" in elem.attrib:
            parts.append(elem.attrib["vehicle_id"])
        elif "source_vehicle" in elem.attrib:
            parts.append(elem.attrib["source_vehicle"])

        if "pose" in elem.attrib:
            parts.append(elem.attrib["pose"])
        elif "target_id" in elem.attrib:
            parts.append(elem.attrib["target_id"])
        elif "task" in elem.attrib:
            parts.append(elem.attrib["task"])

        if "radius_m" in elem.attrib:
            parts.append(f"r={elem.attrib['radius_m']}")

        return " | ".join(parts)

    def node_style(elem) -> dict[str, str]:
        tag = elem.tag

        if tag in {"Sequence", "ReactiveSequence"}:
            return {"fill": "palegreen", "shape": "box", "penwidth": "1.7"}
        if tag in {"Fallback", "ReactiveFallback"}:
            return {"fill": "lightsalmon", "shape": "box", "penwidth": "1.7"}
        if tag == "Parallel":
            return {"fill": "plum", "shape": "box", "penwidth": "1.9"}
        if tag == "SubTree":
            return {"fill": "khaki1", "shape": "box", "penwidth": "1.5"}
        if tag in {"Timeout", "RetryUntilSuccessful"}:
            return {
                "fill": "lightgoldenrod1",
                "shape": "box",
                "penwidth": "1.4",
            }
        return {"fill": "lightsteelblue1", "shape": "box", "penwidth": "1.1"}

    def add_node(
        node_id: str,
        label_text: str,
        fill: str,
        shape: str,
        penwidth: str,
    ) -> None:
        lines.append(
            f'  {node_id} [label="{esc(label_text)}", '
            f'fillcolor="{fill}", shape="{shape}", penwidth={penwidth}];'
        )

    def visit(elem, parent=None, stack=None):
        if stack is None:
            stack = set()

        my_id = f"n{next(node_id_gen)}"
        style = node_style(elem)
        add_node(
            my_id,
            label(elem),
            style["fill"],
            style["shape"],
            style["penwidth"],
        )

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
                    f"RecursiveRef\\n{subtree_id}",
                    "mistyrose",
                    "box",
                    "1.2",
                )
                lines.append(f"  {my_id} -> {loop_id};")
                return my_id

            subtree = bt_map.get(subtree_id)
            if subtree is None:
                missing_id = f"n{next(node_id_gen)}"
                add_node(
                    missing_id,
                    f"MissingTree\\n{subtree_id}",
                    "tomato",
                    "box",
                    "1.2",
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
    add_node(root_id, main_tree_id, "gold", "box", "2.0")

    top_children = []
    for child in main_bt:
        cid = visit(child, root_id, {main_tree_id})
        top_children.append(cid)

    if len(top_children) > 1:
        lines.append("  { rank=same; " + "; ".join(top_children) + "; }")

    # Push the main mission branch and recovery branch farther apart
    if len(top_children) == 2:
        lines.append(
            f"  {top_children[0]} -> {top_children[1]} "
            f'[style=invis, minlen=4];'
        )

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