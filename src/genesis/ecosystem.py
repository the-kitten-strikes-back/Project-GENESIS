from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass(slots=True)
class Ecosystem:
    width: int
    height: int
    max_food_per_cell: float
    grid: list[float] = field(init=False)
    temperature_map: list[float] = field(init=False)
    terrain_map: list[float] = field(init=False)
    fertility_map: list[float] = field(init=False)

    def __post_init__(self) -> None:
        self.grid = [0.0 for _ in range(self.width * self.height)]
        self.temperature_map = [0.0 for _ in range(self.width * self.height)]
        self.terrain_map = [0.0 for _ in range(self.width * self.height)]
        self.fertility_map = [0.0 for _ in range(self.width * self.height)]
        self._build_environment_maps()

    def _build_environment_maps(self) -> None:
        """Build 4 distinct quadrant ecosystems with different characteristics."""
        mid_x = self.width / 2.0
        mid_y = self.height / 2.0
        
        for y in range(self.height):
            for x in range(self.width):
                i = self.idx(x, y)
                
                # Determine quadrant (0=top-left, 1=top-right, 2=bottom-left, 3=bottom-right)
                quadrant = (0 if x < mid_x else 1) + (0 if y < mid_y else 2)
                
                # Local coordinates within quadrant (0 to 1)
                local_x = (x % (self.width // 2)) / max(1, self.width // 2 - 1)
                local_y = (y % (self.height // 2)) / max(1, self.height // 2 - 1)
                
                # Quadrant 0 (Top-Left): Arctic - Brutally cold, rocky, barely habitable
                if quadrant == 0:
                    temperature = 0.05 + 0.08 * math.sin(local_x * math.tau) + 0.02 * math.cos(local_y * math.tau)
                    terrain = 0.80 + 0.18 * math.sin(local_x * math.tau * 2.5) + 0.02 * math.cos(local_y * math.tau * 1.8)
                
                # Quadrant 1 (Top-Right): Desert - Scorching hot, uniform sand, arid wasteland
                elif quadrant == 1:
                    temperature = 0.85 + 0.12 * math.sin(local_x * math.tau) + 0.03 * math.cos(local_y * math.tau)
                    terrain = 0.20 + 0.12 * math.sin(local_x * math.tau * 1.5) + 0.08 * math.cos(local_y * math.tau * 1.2)
                
                # Quadrant 2 (Bottom-Left): Temperate Forest - Mild, moderate terrain, fertile
                elif quadrant == 2:
                    temperature = 0.45 + 0.15 * math.sin(local_x * math.tau * 1.3) + 0.12 * math.cos(local_y * math.tau * 1.5)
                    terrain = 0.45 + 0.2 * math.sin(local_x * math.tau * 2.0) + 0.15 * math.cos(local_y * math.tau * 1.8)
                
                # Quadrant 3 (Bottom-Right): Tropical Jungle - Hot, lush, very fertile
                else:  # quadrant == 3
                    temperature = 0.75 + 0.12 * math.sin(local_x * math.tau * 0.8) + 0.1 * math.cos(local_y * math.tau * 1.1)
                    terrain = 0.35 + 0.2 * math.sin(local_x * math.tau * 2.2) + 0.15 * math.cos(local_y * math.tau * 1.9)
                
                temperature = max(0.0, min(1.0, temperature))
                terrain = max(0.0, min(1.0, terrain))
                
                # Fertility peaks at 0.55°C and decreases with roughness
                fertility = 1.05 - abs(temperature - 0.55) * 1.35 - terrain * 0.45
                fertility = max(0.05, min(1.0, fertility))
                
                self.temperature_map[i] = temperature
                self.terrain_map[i] = terrain
                self.fertility_map[i] = fertility

    def idx(self, x: int, y: int) -> int:
        x %= self.width
        y %= self.height
        return y * self.width + x

    def seed_food(self, total_amount: float, rng: random.Random) -> None:
        for _ in range(int(total_amount)):
            x = rng.randrange(self.width)
            y = rng.randrange(self.height)
            i = self.idx(x, y)
            increment = 0.35 + self.fertility_map[i]
            self.grid[i] = min(self.max_food_per_cell, self.grid[i] + increment)

    def regrow(self, total_amount: float, rng: random.Random) -> None:
        self.seed_food(total_amount, rng)

    def take_food(self, x: int, y: int, amount: float) -> float:
        i = self.idx(x, y)
        eaten = min(self.grid[i], amount)
        self.grid[i] -= eaten
        return eaten

    def temperature_at(self, x: int, y: int) -> float:
        return self.temperature_map[self.idx(x, y)]

    def terrain_at(self, x: int, y: int) -> float:
        return self.terrain_map[self.idx(x, y)]

    def food_near(self, x: int, y: int, radius: float) -> float:
        r = max(1, int(math.ceil(radius)))
        total = 0.0
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= radius * radius:
                    total += self.grid[self.idx(x + dx, y + dy)]
        return total
