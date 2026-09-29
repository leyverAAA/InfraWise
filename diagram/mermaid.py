"""Pure Mermaid serialization for an architecture specification."""

from schema.architecture import ArchSpec


def _escape_label(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def to_mermaid(spec: ArchSpec) -> str:
    """Render an ``ArchSpec`` as a Mermaid flowchart without I/O or mutation."""
    lines = ["graph TD"]
    lines.extend(
        f'  {component.id}["{_escape_label(component.display_name)}"]'
        for component in spec.components
    )
    for connection in spec.connections:
        if connection.label:
            label = _escape_label(connection.label)
            lines.append(f"  {connection.source} -->|{label}| {connection.target}")
        else:
            lines.append(f"  {connection.source} --> {connection.target}")
    return "\n".join(lines) + "\n"
