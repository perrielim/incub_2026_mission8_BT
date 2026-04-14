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
        '  graph [rankdir=TB, splines=false, nodesep=0.95, ranksep=1.15, pad=0.35];',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11];',
        '  edge [color="black", penwidth=1.1];',
    ]

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\\\\n", "\\n")

    def short_tag(tag: str) -> str:
        return tag.split("_", 1)[1] if "_" in tag else tag

    def is_condition_node(elem) -> bool:
        if elem.attrib.get("node_type") == "condition":
            return True

        # fallback heuristic
        tag = elem.tag.lower()
        return (
            tag.startswith("condition_")
            or tag.startswith("is_")
            or tag.startswith("check_")
            or tag.startswith("has_")
            or tag.startswith("can_")
            or tag.startswith("should_")
        )

    def label(elem) -> str:
        tag = elem.tag

        # CONTROL
        if tag in CONTROL_NODES:
            return f"[CONTROL]\n{tag}"

        # DECORATOR
        if tag in DECORATOR_NODES:
            if tag == "Timeout":
                return f"[DECORATOR]\nTimeout\n{elem.attrib.get('msec', '?')} ms"
            if tag == "RetryUntilSuccessful":
                return f"[DECORATOR]\nRetry\n{elem.attrib.get('num_attempts', '?')} attempts"
            return "[DECORATOR]"

        # SUBTREE
        if tag == "SubTree":
            return f"[SUBTREE]\n{elem.attrib.get('ID', 'UNKNOWN')}"

        # CONDITION
        if is_condition_node(elem):
            return f"[COND]\n{short_tag(tag)}"

        # ACTION
        parts = [f"[ACT]\n{short_tag(tag)}"]

        if "agent_id" in elem.attrib:
            parts.append(elem.attrib["agent_id"])
        if "pose" in elem.attrib:
            parts.append("→ pose")

        return "\n".join(parts)

    def node_style(elem) -> dict:
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

        # ACTION
        return {"fill": "#90CAF9", "shape": "box", "penwidth": "1.2"}

    def add_node(node_id, label_text, style):
        lines.append(
            f'  {node_id} [label="{esc(label_text)}", '
            f'fillcolor="{style["fill"]}", shape="{style["shape"]}", penwidth={style["penwidth"]}];'
        )

    def visit(elem, parent=None, stack=None):
        if stack is None:
            stack = set()

        my_id = f"n{next(node_id_gen)}"
        style = node_style(elem)

        add_node(my_id, label(elem), style)

        if parent:
            lines.append(f"  {parent} -> {my_id};")

        # Subtree expansion
        if elem.tag == "SubTree":
            subtree_id = elem.attrib.get("ID")
            if subtree_id in stack:
                return my_id

            subtree = bt_map.get(subtree_id)
            if subtree is None:
                return my_id

            stack = set(stack)
            stack.add(subtree_id)

            for child in subtree:
                visit(child, my_id, stack)

            return my_id

        for child in elem:
            visit(child, my_id, stack)

        return my_id

    main_bt = bt_map[main_tree_id]
    root_id = f"n{next(node_id_gen)}"

    add_node(root_id, f"[ROOT]\n{main_tree_id}", {
        "fill": "#FFD54F",
        "shape": "box",
        "penwidth": "2.0"
    })

    for child in main_bt:
        visit(child, root_id, {main_tree_id})

    # LEGEND
    lines += [
        "",
        "subgraph cluster_legend {",
        '  label="Legend";',
        '  style="rounded,dashed";',

        '  key_seq [label="[CONTROL]\\nSequence", fillcolor="#C8E6C9", style="filled"];',
        '  key_fb [label="[CONTROL]\\nFallback", fillcolor="#FFCDD2", style="filled"];',
        '  key_par [label="[CONTROL]\\nParallel", fillcolor="#E1BEE7", style="filled"];',
        '  key_dec [label="[DECORATOR]", shape=diamond, fillcolor="#FFF9C4", style="filled"];',
        '  key_act [label="[ACT]", fillcolor="#90CAF9", style="filled"];',
        '  key_cond [label="[COND]\\nBoolean check", shape=ellipse, fillcolor="#64B5F6", style="filled"];',
        '  key_sub [label="[SUBTREE]", shape=folder, fillcolor="#FFE082", style="filled"];',

        "}",
    ]

    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_file")
    parser.add_argument("-o", "--output", default="tree.svg")
    args = parser.parse_args()

    xml_text = Path(args.xml_file).read_text()
    dot = xml_to_dot(xml_text)

    with tempfile.TemporaryDirectory() as tmp:
        dot_path = Path(tmp) / "tree.dot"
        out_path = Path(tmp) / args.output

        dot_path.write_text(dot)

        fmt = Path(args.output).suffix.lstrip(".")
        subprocess.run(["dot", f"-T{fmt}", str(dot_path), "-o", str(out_path)], check=True)

        Path(args.output).write_bytes(out_path.read_bytes())

    print(f"✅ Generated: {args.output}")


if __name__ == "__main__":
    main()