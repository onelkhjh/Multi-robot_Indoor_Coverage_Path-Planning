"""Read-only 2D map visualization."""

from __future__ import annotations

from matplotlib import pyplot as plt
from matplotlib.patches import Polygon, Rectangle

from .models import DiscretizedMap


def render_plan(value, allocation, plan):
    """Render node ownership and nearest-neighbor coverage paths."""
    fig, ax = plt.subplots()
    source = value.source
    colors = plt.get_cmap("tab10")
    ax.add_patch(Polygon(source.aoi.exterior, closed=True, fill=False, edgecolor="black", linewidth=2))
    for zone in source.no_fly_zones:
        ax.add_patch(Polygon(zone.exterior, closed=True, facecolor="black", alpha=0.25, hatch="//"))
    owners = dict(allocation.owner_by_cell)
    for cell in value.cells:
        x, y = cell.vertices[0]
        owner = owners[cell.id]
        ax.add_patch(Rectangle((x, y), value.cell_width_m, value.cell_width_m, facecolor=colors(owner), edgecolor="white", alpha=0.35))
    for path in plan.paths:
        points = path.trajectory
        if len(points) > 1:
            xs, ys = zip(*points)
            ax.plot(xs, ys, color=colors(path.cluster_index), linewidth=1.2, label=f"{path.node_id}: {path.distance_m:.1f} m")
        ax.scatter(*path.start, color=colors(path.cluster_index), marker="x", s=55)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"{source.name} — SCoPP allocation and NN paths")
    ax.legend(loc="best", fontsize="small")
    return fig, ax


def render_map(value: DiscretizedMap, *, show_samples: bool = False):
    fig, ax = plt.subplots()
    source = value.source
    ax.add_patch(Polygon(source.aoi.exterior, closed=True, fill=False, edgecolor="black", linewidth=2, label="AOI"))
    for zone in source.no_fly_zones:
        ax.add_patch(Polygon(zone.exterior, closed=True, facecolor="red", alpha=0.35, hatch="//", label="no-fly zone"))
    for cell in value.cells:
        x, y = cell.vertices[0]
        ax.add_patch(Rectangle((x, y), value.cell_width_m, value.cell_width_m, facecolor="#4c9be8", edgecolor="#2968a3", alpha=0.25))
        if show_samples:
            xs, ys = zip(*cell.perimeter_samples)
            ax.scatter(xs, ys, s=3, color="#163f68")
    for node in source.node_starts:
        ax.scatter(*node.position, marker="x", s=45, label=node.id)
        ax.annotate(node.id, node.position)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(source.name)
    return fig, ax
