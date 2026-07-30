"""Standard-format exporters (SPEC §7): SVG now; ArchiMate/BPMN/XMI in later phases."""

from .svg import render_view_svg

__all__ = ["render_view_svg"]
