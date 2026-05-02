from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .genetics import Genome


ACTIONS = ("forage", "explore", "rest", "hunt")
CONTEXTS = ("stable", "hungry", "threatened", "opportunity")


@dataclass(slots=True)
class SpatialMemory:
    """Tracks regional reputation to help organisms avoid dead zones and find safe forage areas."""
    region_size: int = 8  # Grid cells per region (8x8 regions for 80x60 world)
    reputation: dict[tuple[int, int], float] = field(default_factory=dict)
    visit_counts: dict[tuple[int, int], int] = field(default_factory=dict)
    last_region: tuple[int, int] | None = None

    def get_region(self, x: int, y: int) -> tuple[int, int]:
        """Quantize position to region coordinates."""
        return (x // self.region_size, y // self.region_size)

    def get_reputation(self, x: int, y: int) -> float:
        """Get reputation of region: -1 (deadly) to +1 (safe & abundant)."""
        region = self.get_region(x, y)
        return max(-1.0, min(1.0, self.reputation.get(region, 0.0)))

    def visit_region(self, x: int, y: int) -> None:
        """Record visiting a region for later reinforcement."""
        region = self.get_region(x, y)
        self.last_region = region
        self.visit_counts[region] = self.visit_counts.get(region, 0) + 1

    def reinforce_region(self, energy_change: float, learning_rate: float) -> None:
        """Update region reputation based on energy outcome."""
        if self.last_region is None:
            return
        
        region = self.last_region
        old_rep = self.reputation.get(region, 0.0)
        
        # Adaptive learning: visited regions learn faster than unexplored ones
        visits = self.visit_counts.get(region, 1)
        adaptive_rate = learning_rate * (1.0 + math.log1p(visits)) / (2.0 + visits)
        
        new_rep = old_rep + adaptive_rate * (energy_change - old_rep)
        self.reputation[region] = max(-3.0, min(3.0, new_rep))

    def get_safe_direction(self, x: int, y: int, width: int, height: int, rng: random.Random) -> tuple[int, int]:
        """Bias movement toward high-reputation regions, away from dead zones."""
        current_rep = self.get_reputation(x, y)
        candidates = []
        
        # Check 8 adjacent directions
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx = (x + dx) % width
                ny = (y + dy) % height
                rep = self.get_reputation(nx, ny)
                candidates.append((rep, dx, dy))
        
        # Sort by reputation (highest first)
        candidates.sort(reverse=True, key=lambda c: c[0])
        
        # Pick from top candidates with some randomness
        if candidates and candidates[0][0] > current_rep:
            # 60% pick best, 40% pick random from top 3
            if rng.random() < 0.6:
                return (candidates[0][1], candidates[0][2])
            else:
                top_k = candidates[:min(3, len(candidates))]
                rep, dx, dy = rng.choice(top_k)
                return (dx, dy)
        else:
            # Current region is good or tied, explore cautiously
            return (rng.choice([-1, 0, 1]), rng.choice([-1, 0, 1]))

    def clone(self) -> "SpatialMemory":
        """Clone spatial memory for offspring (incomplete inheritance - organisms must relearn)."""
        return SpatialMemory(
            region_size=self.region_size,
            reputation={k: v * 0.6 for k, v in self.reputation.items()},  # Fade parent's memory
            visit_counts={},  # Reset visit counts
        )


@dataclass(slots=True)
class Brain:
    q_values: dict[str, dict[str, float]]
    spatial_memory: SpatialMemory = field(default_factory=SpatialMemory)
    epsilon: float = 0.08
    last_context: str = "stable"
    last_action: str = "rest"
    last_energy: float = 0.0

    @classmethod
    def create(cls) -> "Brain":
        return cls(
            q_values={ctx: {action: 0.0 for action in ACTIONS} for ctx in CONTEXTS},
            spatial_memory=SpatialMemory(),
        )

    def choose_action(
        self, 
        context: str, 
        logits: dict[str, float], 
        rng: random.Random, 
        energy: float,
        x: int,
        y: int,
    ) -> str:
        self.last_context = context
        self.last_energy = energy

        if rng.random() < self.epsilon:
            action = rng.choice(ACTIONS)
            self.last_action = action
            return action

        # Add spatial awareness to exploration logit
        spatial_rep = self.spatial_memory.get_reputation(x, y)
        logits = dict(logits)  # Don't mutate original
        logits["explore"] += 0.45 * max(0.0, -spatial_rep)  # Encourage leaving bad zones
        logits["rest"] += 0.2 * max(0.0, spatial_rep)  # Encourage staying in good zones

        scores = {a: logits[a] + self.q_values[context][a] for a in ACTIONS}
        mx = max(scores.values())
        weights = {k: math.exp(v - mx) for k, v in scores.items()}
        total = sum(weights.values())
        pick = rng.uniform(0, total)
        walk = 0.0
        for action, w in weights.items():
            walk += w
            if walk >= pick:
                self.last_action = action
                return action

        self.last_action = "rest"
        return "rest"

    def reinforce(self, energy: float, learning_rate: float) -> None:
        reward = energy - self.last_energy
        old = self.q_values[self.last_context][self.last_action]
        self.q_values[self.last_context][self.last_action] = old + learning_rate * (reward - old)
        self.q_values[self.last_context][self.last_action] = max(-6.0, min(6.0, self.q_values[self.last_context][self.last_action]))
        self.epsilon = max(0.02, self.epsilon * 0.9995)
        
        # Also update spatial memory
        self.spatial_memory.reinforce_region(reward, learning_rate)

    def clone(self) -> "Brain":
        return Brain(
            q_values={ctx: dict(values) for ctx, values in self.q_values.items()},
            spatial_memory=self.spatial_memory.clone(),
            epsilon=self.epsilon,
        )

    def mutate(self, rng: random.Random, mutation_rate: float) -> None:
        for ctx in CONTEXTS:
            for action in ACTIONS:
                if rng.random() < mutation_rate:
                    self.q_values[ctx][action] += rng.gauss(0.0, 0.25)
                    self.q_values[ctx][action] = max(-6.0, min(6.0, self.q_values[ctx][action]))
        if rng.random() < mutation_rate:
            self.epsilon = max(0.02, min(0.25, self.epsilon + rng.gauss(0.0, 0.01)))


@dataclass(slots=True)
class Organism:
    id: int
    species_id: int
    genome: Genome
    x: int
    y: int
    energy: float
    age: int = 0
    alive: bool = True
    brain: Brain = field(default_factory=Brain.create)

    def decide_action(
        self,
        nearby_food: float,
        nearby_prey: int,
        nearby_predators: int,
        temperature_match: float,
        terrain_match: float,
        rng: random.Random,
    ) -> str:
        herbivory = 1.0 - self.genome.diet
        carnivory = self.genome.diet

        logits = {action: 0.0 for action in ACTIONS}
        logits["forage"] += (0.45 + herbivory) * math.log1p(max(nearby_food, 0.0))
        logits["forage"] += 0.3 * temperature_match + 0.25 * terrain_match
        logits["explore"] += 0.55 * self.genome.speed + 0.85 * max(nearby_predators, 0)
        logits["rest"] += 0.35 * (1.4 - self.genome.metabolism)
        logits["hunt"] += (0.25 + self.genome.aggression + carnivory) * max(nearby_prey, 0)

        if carnivory < 0.35:
            logits["hunt"] -= 1.1

        if nearby_predators > 0 and self.energy < 22:
            context = "threatened"
        elif self.energy < 14 or (nearby_food < 1.2 and nearby_prey == 0):
            context = "hungry"
        elif nearby_prey > 0 and carnivory >= 0.55:
            context = "opportunity"
        else:
            context = "stable"

        # Record location before decision
        self.brain.spatial_memory.visit_region(self.x, self.y)
        
        return self.brain.choose_action(context, logits, rng, self.energy, self.x, self.y)

    def reinforce(self, learning_rate: float) -> None:
        self.brain.reinforce(self.energy, learning_rate)