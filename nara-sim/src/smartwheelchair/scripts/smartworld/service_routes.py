"""Seleção de âncoras de passagem em qualquer OccupancyGrid, sem dependência ROS.

A rota candidata considera passáveis apenas os portais anunciados pela infra.
Ela serve para negociar acesso, nunca para comandar movimento ou apagar os
obstáculos dos sensores. Nav2 continua responsável pelo caminho executável.
"""
from dataclasses import dataclass
import heapq
import math

import numpy as np


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    yaw: float = 0.0

    def cell(self, x, y):
        dx, dy = x - self.origin_x, y - self.origin_y
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return (math.floor((c * dx + s * dy) / self.resolution),
                math.floor((-s * dx + c * dy) / self.resolution))

    def point(self, col, row):
        x, y = (col + 0.5) * self.resolution, (row + 0.5) * self.resolution
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        return self.origin_x + c * x - s * y, self.origin_y + s * x + c * y

    def contains(self, col, row):
        return 0 <= col < self.width and 0 <= row < self.height


@dataclass(frozen=True)
class Anchor:
    name: str
    x: float
    y: float
    width: float
    thickness: float
    yaw: float = 0.0

    def side(self, point):
        return -(point[0] - self.x) * math.sin(self.yaw) + (point[1] - self.y) * math.cos(self.yaw)


@dataclass
class ServiceRoute:
    points: list
    services: list
    entry_sides: dict


def portal_cells(grid, anchor):
    """Índices cujos centros estão no portal, incluindo orientação e origem do grid."""
    c, s = math.cos(anchor.yaw), math.sin(anchor.yaw)
    corners = [grid.cell(anchor.x + c * u - s * v, anchor.y + s * u + c * v)
               for u in (-anchor.width / 2, anchor.width / 2)
               for v in (-anchor.thickness / 2, anchor.thickness / 2)]
    min_col, max_col = min(p[0] for p in corners), max(p[0] for p in corners)
    min_row, max_row = min(p[1] for p in corners), max(p[1] for p in corners)
    cells = []
    for row in range(max(0, min_row), min(grid.height - 1, max_row) + 1):
        for col in range(max(0, min_col), min(grid.width - 1, max_col) + 1):
            wx, wy = grid.point(col, row)
            dx, dy = wx - anchor.x, wy - anchor.y
            if (abs(c * dx + s * dy) <= anchor.width / 2 + 1e-9
                    and abs(-s * dx + c * dy) <= anchor.thickness / 2 + 1e-9):
                cells.append(row * grid.width + col)
    return cells


def inflate(blocked, radius):
    """Expande obstáculos sem criar dependência de OpenCV ou SciPy."""
    result = blocked.copy()
    height, width = blocked.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            src_y, dst_y = max(0, -dy), max(0, dy)
            src_x, dst_x = max(0, -dx), max(0, dx)
            rows, cols = height - abs(dy), width - abs(dx)
            if rows > 0 and cols > 0:
                result[dst_y:dst_y + rows, dst_x:dst_x + cols] |= blocked[src_y:src_y + rows, src_x:src_x + cols]
    if radius:
        result[:radius, :] = result[-radius:, :] = True
        result[:, :radius] = result[:, -radius:] = True
    return result


def find_service_route(data, grid, start, goal, anchors, denied=(), clearance=0.45,
                       occupied_threshold=65, max_expansions=200000):
    """A* geométrico para descobrir serviços necessários; retorna None sem conexão.

    Serviços negados ficam bloqueados, permitindo escolher outra passagem.
    A inflação é conservadora na largura; o footprint completo é validado por
    Nav2 somente depois da confirmação física dos serviços selecionados.
    """
    start_cell, goal_cell = grid.cell(*start), grid.cell(*goal)
    if not grid.contains(*start_cell) or not grid.contains(*goal_cell):
        return None
    values = np.asarray(data, dtype=np.int16).reshape(grid.height, grid.width)
    blocked = (values < 0) | (values >= occupied_threshold)
    indices = {}
    names_at = {}
    denied = set(denied)
    for anchor in anchors:
        cells = portal_cells(grid, anchor)
        indices[anchor.name] = cells
        for index in cells:
            blocked.flat[index] = anchor.name in denied
            names_at.setdefault(index, []).append(anchor.name)
    # Uma âncora permitida sobreposta não pode apagar uma passagem negada.
    for name in denied:
        for index in indices.get(name, ()):
            blocked.flat[index] = True
    blocked = inflate(blocked, math.ceil(clearance / grid.resolution))
    start_i = start_cell[1] * grid.width + start_cell[0]
    goal_i = goal_cell[1] * grid.width + goal_cell[0]
    if blocked.flat[start_i] or blocked.flat[goal_i]:
        return None
    distance = {start_i: 0.0}
    parents = {}
    heap = [(math.hypot(start_cell[0] - goal_cell[0], start_cell[1] - goal_cell[1]), 0.0, start_i)]
    moves = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    expansions = 0
    while heap and expansions < max_expansions:
        _, cost, index = heapq.heappop(heap)
        if cost != distance.get(index):
            continue
        if index == goal_i:
            path = [index]
            while path[-1] != start_i:
                path.append(parents[path[-1]])
            path.reverse()
            selected = []
            for cell in path:
                for name in names_at.get(cell, ()):
                    if name not in selected:
                        selected.append(name)
            points = [grid.point(i % grid.width, i // grid.width) for i in path]
            by_name = {a.name: a for a in anchors}
            return ServiceRoute(points, selected, {name: by_name[name].side(start) for name in selected})
        expansions += 1
        col, row = index % grid.width, index // grid.width
        for dx, dy in moves:
            nc, nr = col + dx, row + dy
            if not grid.contains(nc, nr) or blocked[nr, nc]:
                continue
            if dx and dy and (blocked[row, nc] or blocked[nr, col]):
                continue
            next_i = nr * grid.width + nc
            next_cost = cost + (math.sqrt(2) if dx and dy else 1.0)
            if next_cost < distance.get(next_i, math.inf):
                distance[next_i] = next_cost
                parents[next_i] = index
                heuristic = math.hypot(nc - goal_cell[0], nr - goal_cell[1])
                heapq.heappush(heap, (next_cost + heuristic, next_cost, next_i))
    return None
