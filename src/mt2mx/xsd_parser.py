from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree as ET

XS = "{http://www.w3.org/2001/XMLSchema}"


def _local_type(name: str | None) -> str:
    if not name:
        return ""
    return name.split(":", 1)[-1]


def _combine_min(parent: str, child: str) -> str:
    try:
        return str(int(parent) * int(child))
    except ValueError:
        return "0" if "0" in (parent, child) else child


def _combine_max(parent: str, child: str) -> str:
    if "unbounded" in (parent, child) or "*" in (parent, child):
        return "unbounded"
    try:
        return str(int(parent) * int(child))
    except ValueError:
        return child


def extract_xsd_inventory(path: str | Path) -> dict[str, Any]:
    """Expand an ISO 20022 XSD into exact XML element/attribute paths."""
    path = Path(path)
    schema = ET.parse(path).getroot()
    target_ns = schema.attrib.get("targetNamespace", "")
    message_id = target_ns.rsplit(":", 1)[-1] if target_ns else path.stem

    complex_types = {
        node.attrib["name"]: node
        for node in schema.findall(f"{XS}complexType")
        if node.get("name")
    }
    global_elements = {
        node.attrib["name"]: node
        for node in schema.findall(f"{XS}element")
        if node.get("name")
    }
    document = global_elements.get("Document")
    if document is None:
        raise ValueError(f"{path.name}: global Document element not found")

    rows: list[dict[str, Any]] = []
    choice_counter = 0

    def add_attributes(type_name: str, parent_path: str) -> None:
        ctype = complex_types.get(type_name)
        if ctype is None:
            return
        for attr in ctype.findall(f".//{XS}attribute"):
            name = attr.get("name")
            if not name:
                continue
            rows.append(
                {
                    "path": f"{parent_path}/@{name}",
                    "parent_path": parent_path,
                    "xml_tag": f"@{name}",
                    "type": _local_type(attr.get("type")),
                    "min_occurs": "1" if attr.get("use") == "required" else "0",
                    "max_occurs": "1",
                    "is_attribute": True,
                    "choice_group": "",
                }
            )

    def walk_type(
        type_name: str,
        parent_path: str,
        inherited_min: str = "1",
        inherited_max: str = "1",
        type_stack: tuple[str, ...] = (),
    ) -> None:
        nonlocal choice_counter
        type_name = _local_type(type_name)
        ctype = complex_types.get(type_name)
        if ctype is None or type_name in type_stack:
            return
        next_stack = type_stack + (type_name,)

        def walk_particle(
            particle: ET.Element,
            pmin: str,
            pmax: str,
            active_choice: str = "",
        ) -> None:
            nonlocal choice_counter
            tag = particle.tag
            local_min = particle.get("minOccurs", "1")
            local_max = particle.get("maxOccurs", "1")
            effective_min = _combine_min(pmin, local_min)
            effective_max = _combine_max(pmax, local_max)

            if tag == f"{XS}choice":
                choice_counter += 1
                group = f"choice-{choice_counter}"
                for child in particle:
                    if child.tag in {f"{XS}element", f"{XS}sequence", f"{XS}choice", f"{XS}all"}:
                        walk_particle(child, effective_min, effective_max, group)
                return
            if tag in {f"{XS}sequence", f"{XS}all"}:
                for child in particle:
                    if child.tag in {f"{XS}element", f"{XS}sequence", f"{XS}choice", f"{XS}all"}:
                        walk_particle(child, effective_min, effective_max, active_choice)
                return
            if tag != f"{XS}element":
                return

            name = particle.get("name")
            if not name:
                return
            child_type = _local_type(particle.get("type"))
            child_path = f"{parent_path}/{name}"
            row_min = "0" if active_choice and effective_min != "0" else effective_min
            rows.append(
                {
                    "path": child_path,
                    "parent_path": parent_path,
                    "xml_tag": name,
                    "type": child_type,
                    "min_occurs": row_min,
                    "max_occurs": effective_max,
                    "is_attribute": False,
                    "choice_group": active_choice,
                }
            )
            add_attributes(child_type, child_path)
            walk_type(child_type, child_path, row_min, effective_max, next_stack)

        for child in ctype:
            if child.tag in {f"{XS}sequence", f"{XS}choice", f"{XS}all"}:
                walk_particle(child, inherited_min, inherited_max)

    document_type = _local_type(document.get("type"))
    doc_complex = complex_types.get(document_type)
    if doc_complex is None:
        raise ValueError(f"{path.name}: Document type {document_type!r} not found")
    first = doc_complex.find(f".//{XS}element")
    if first is None or not first.get("name"):
        raise ValueError(f"{path.name}: message root element not found")
    root_tag = first.attrib["name"]

    walk_type(document_type, "Document")
    return {
        "message_id": message_id,
        "namespace": target_ns,
        "root_tag": root_tag,
        "rows": rows,
    }
