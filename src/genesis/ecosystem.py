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
        for y in range(self.height):
            for x in range(self.width):
                i = self.idx(x, y)
                latitude = y / max(1, self.height - 1)
                climate_wave = 0.1 * math.sin((x / max(1, self.width)) * math.tau)
                temperature = 0.15 + 0.75 * (1.0 - abs(0.5 - latitude) * 2.0) + climate_wave
                temperature = max(0.0, min(1.0, temperature))

                terrain_raw = (
                    0.5
                    + 0.25 * math.sin((x / max(1, self.width)) * math.tau * 2.1)
                    + 0.25 * math.cos((y / max(1, self.height)) * math.tau * 1.7)
                )
                terrain = max(0.0, min(1.0, terrain_raw))

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
