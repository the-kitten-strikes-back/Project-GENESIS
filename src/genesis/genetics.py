from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace


@dataclass(slots=True)
class Genome:
    speed: float
    metabolism: float
    vision: float
    fertility: float
    aggression: float
    diet: float
    temp_preference: float
    terrain_preference: float

    def clamp(self) -> "Genome":
        return Genome(
            speed=max(0.1, min(self.speed, 2.2)),
            metabolism=max(0.1, min(self.metabolism, 2.5)),
            vision=max(1.0, min(self.vision, 12.0)),
            fertility=max(0.1, min(self.fertility, 2.0)),
            aggression=max(0.0, min(self.aggression, 1.0)),
            diet=max(0.0, min(self.diet, 1.0)),
            temp_preference=max(0.0, min(self.temp_preference, 1.0)),
            terrain_preference=max(0.0, min(self.terrain_preference, 1.0)),
        )


def random_genome(rng: random.Random) -> Genome:
    return Genome(
        speed=rng.uniform(0.6, 1.4),
        metabolism=rng.uniform(0.7, 1.4),
        vision=rng.uniform(2.0, 7.0),
        fertility=rng.uniform(0.7, 1.3),
        aggression=rng.uniform(0.0, 0.3),
        diet=rng.uniform(0.0, 0.6),
        temp_preference=rng.uniform(0.15, 0.85),
        terrain_preference=rng.uniform(0.15, 0.85),
    )


def mutate_genome(parent: Genome, rng: random.Random, mutation_rate: float, mutation_strength: float) -> Genome:
    child = replace(parent)
    for trait in ("speed", "metabolism", "vision", "fertility", "aggression", "diet", "temp_preference", "terrain_preference"):
        if rng.random() < mutation_rate:
            value = getattr(child, trait)
            drift = rng.gauss(0.0, mutation_strength * max(0.2, abs(value)))
            setattr(child, trait, value + drift)
    return child.clamp()


def genomic_distance(a: Genome, b: Genome) -> float:
    parts = [
        abs(a.speed - b.speed) / 2.2,
        abs(a.metabolism - b.metabolism) / 2.5,
        abs(a.vision - b.vision) / 12.0,
        abs(a.fertility - b.fertility) / 2.0,
        abs(a.aggression - b.aggression),
        abs(a.diet - b.diet),
        abs(a.temp_preference - b.temp_preference),
        abs(a.terrain_preference - b.terrain_preference),
    ]
    return math.sqrt(sum(p * p for p in parts) / len(parts))
