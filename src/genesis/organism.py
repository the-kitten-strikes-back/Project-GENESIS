from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .genetics import Genome


ACTIONS = ("forage", "explore", "rest", "hunt")
CONTEXTS = ("stable", "hungry", "threatened", "opportunity")


@dataclass(slots=True)
class Brain:
    q_values: dict[str, dict[str, float]]
    epsilon: float = 0.08
    last_context: str = "stable"
    last_action: str = "rest"
    last_energy: float = 0.0

    @classmethod
    def create(cls) -> "Brain":
        return cls(q_values={ctx: {action: 0.0 for action in ACTIONS} for ctx in CONTEXTS})

    def choose_action(self, context: str, logits: dict[str, float], rng: random.Random, energy: float) -> str:
        self.last_context = context
        self.last_energy = energy

        if rng.random() < self.epsilon:
            action = rng.choice(ACTIONS)
            self.last_action = action
            return action

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

    def clone(self) -> "Brain":
        return Brain(q_values={ctx: dict(values) for ctx, values in self.q_values.items()}, epsilon=self.epsilon)

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

        return self.brain.choose_action(context, logits, rng, self.energy)

    def reinforce(self, learning_rate: float) -> None:
        self.brain.reinforce(self.energy, learning_rate)
