from __future__ import annotations

import collections
import math
import random
from dataclasses import dataclass

from .config import SimulationConfig
from .ecosystem import Ecosystem
from .genetics import Genome, genomic_distance, mutate_genome, random_genome
from .organism import Organism


@dataclass(slots=True)
class Snapshot:
    tick: int
    total_population: int
    prey_population: int
    predator_population: int
    species_population: dict[int, int]
    average_energy: float
    births: int
    deaths: int


class Simulation:
    def __init__(self, config: SimulationConfig):
        self.cfg = config
        self.rng = random.Random(config.random_seed)
        self.ecosystem = Ecosystem(config.width, config.height, config.max_food_per_cell)
        self.organisms: list[Organism] = []
        self.next_id = 1
        self.next_species_id = 1
        self.species_founder: dict[int, Genome] = {}
        self.tick = 0
        self.ticks_without_predators = 0
        self.last_predator_recovery_tick = -10_000

        self.ecosystem.seed_food(config.initial_food, self.rng)
        self._spawn_initial_population()

    def _spawn_initial_population(self) -> None:
        founders: list[tuple[int, Genome]] = []
        for _ in range(max(1, self.cfg.initial_species)):
            founder_genome = random_genome(self.rng)
            sid = self._register_species(founder_genome)
            founders.append((sid, founder_genome))

        for _ in range(self.cfg.initial_population):
            sid, founder_genome = self.rng.choice(founders)
            genome = mutate_genome(
                founder_genome,
                self.rng,
                mutation_rate=0.03,
                mutation_strength=self.cfg.mutation_strength * 0.25,
            )
            self.organisms.append(
                Organism(
                    id=self._new_id(),
                    species_id=sid,
                    genome=genome,
                    x=self.rng.randrange(self.cfg.width),
                    y=self.rng.randrange(self.cfg.height),
                    energy=self.cfg.start_energy,
                )
            )

    def _new_id(self) -> int:
        oid = self.next_id
        self.next_id += 1
        return oid

    def _register_species(self, genome: Genome) -> int:
        sid = self.next_species_id
        self.next_species_id += 1
        self.species_founder[sid] = genome
        return sid

    def _assign_species(self, parent_species: int, genome: Genome) -> int:
        founder = self.species_founder[parent_species]
        if genomic_distance(founder, genome) > self.cfg.speciation_threshold:
            return self._register_species(genome)
        return parent_species

    def _is_predator(self, org: Organism) -> bool:
        return org.genome.diet >= self.cfg.predator_diet_threshold

    def _startup_progress(self) -> float:
        if self.cfg.startup_stabilization_ticks <= 0:
            return 1.0
        return min(1.0, self.tick / float(self.cfg.startup_stabilization_ticks))

    def step(self) -> Snapshot:
        self.tick += 1
        living_before = [o for o in self.organisms if o.alive]
        predator_before = sum(1 for o in living_before if self._is_predator(o))
        prey_before = max(0, len(living_before) - predator_before)
        carrying_capacity = max(1.0, self.cfg.width * self.cfg.height * self.cfg.ecosystem_carrying_density)
        crowding = min(1.0, len(living_before) / carrying_capacity)
        season_phase = (2.0 * math.pi * self.tick) / max(1, self.cfg.seasonal_period)
        season_multiplier = 1.0 + self.cfg.seasonal_regrowth_amplitude * math.sin(season_phase)
        startup_progress = self._startup_progress()
        startup_regrowth = 1.0 + (self.cfg.startup_regrowth_boost - 1.0) * (1.0 - startup_progress)
        regrowth_multiplier = max(0.4, (1.12 - 0.55 * crowding) * season_multiplier * startup_regrowth)
        self.ecosystem.regrow(self.cfg.food_regrowth_per_step * regrowth_multiplier, self.rng)

        births = 0
        deaths = 0

        by_position: dict[tuple[int, int], list[Organism]] = collections.defaultdict(list)
        for org in self.organisms:
            if org.alive:
                by_position[(org.x, org.y)].append(org)

        newborns: list[Organism] = []
        base_birth_cap = max(1, int(len(living_before) * self.cfg.max_birth_fraction_per_tick))
        startup_birth_scale = self.cfg.startup_birth_cap_scale + (1.0 - self.cfg.startup_birth_cap_scale) * startup_progress
        birth_cap = max(1, int(base_birth_cap * startup_birth_scale))

        for org in self.organisms:
            if not org.alive:
                continue

            co_located = by_position[(org.x, org.y)]
            nearby_prey = len(
                [other for other in co_located if other.alive and other.id != org.id and not self._is_predator(other)]
            )
            nearby_predators = len(
                [other for other in co_located if other.alive and other.id != org.id and self._is_predator(other)]
            )
            food_near = self.ecosystem.food_near(org.x, org.y, org.genome.vision)
            local_temperature = self.ecosystem.temperature_at(org.x, org.y)
            local_terrain = self.ecosystem.terrain_at(org.x, org.y)
            temperature_match = 1.0 - abs(local_temperature - org.genome.temp_preference)
            terrain_match = 1.0 - abs(local_terrain - org.genome.terrain_preference)
            action = org.decide_action(
                food_near,
                nearby_prey,
                nearby_predators,
                temperature_match,
                terrain_match,
                self.rng,
            )

            deaths += self._apply_action(org, action, by_position, startup_progress)
            org.age += 1
            climate_stress = abs(local_temperature - org.genome.temp_preference)
            terrain_stress = abs(local_terrain - org.genome.terrain_preference)
            predator_pressure = max(0.0, (predator_before - prey_before) / max(1, len(living_before)))
            trophic_stress = 0.06 * org.genome.diet * predator_pressure
            org.energy -= (
                0.18
                + 0.16 * org.genome.metabolism
                + 0.05 * org.genome.diet
                + self.cfg.temperature_stress_scale * climate_stress * 0.18
                + terrain_stress * 0.06
                + trophic_stress
            )

            if org.age >= self.cfg.max_age or org.energy <= 0:
                org.alive = False
                deaths += 1
                continue

            reproduction_threshold = self.cfg.reproduction_energy_threshold * (
                1.0 + self.cfg.startup_reproduction_ramp * (1.0 - startup_progress)
            )
            if org.energy >= reproduction_threshold and births < birth_cap:
                child = self._reproduce(org)
                newborns.append(child)
                births += 1

            org.reinforce(self.cfg.learning_rate)

        self.organisms = [o for o in self.organisms if o.alive]
        self.organisms.extend(newborns)

        self._apply_recovery_seed()

        species_counts = collections.Counter(o.species_id for o in self.organisms if o.alive)
        predator_population = sum(1 for o in self.organisms if o.alive and self._is_predator(o))
        prey_population = len(self.organisms) - predator_population
        avg_energy = sum(o.energy for o in self.organisms if o.alive) / max(1, len(self.organisms))

        return Snapshot(
            tick=self.tick,
            total_population=len(self.organisms),
            prey_population=prey_population,
            predator_population=predator_population,
            species_population=dict(species_counts),
            average_energy=avg_energy,
            births=births,
            deaths=deaths,
        )

    def _apply_action(
        self,
        org: Organism,
        action: str,
        by_position: dict[tuple[int, int], list[Organism]],
        startup_progress: float,
    ) -> int:
        deaths = 0
        herbivory = 1.0 - org.genome.diet
        local_temperature = self.ecosystem.temperature_at(org.x, org.y)
        local_terrain = self.ecosystem.terrain_at(org.x, org.y)
        temperature_match = 1.0 - abs(local_temperature - org.genome.temp_preference)
        terrain_match = 1.0 - abs(local_terrain - org.genome.terrain_preference)
        habitat_quality = 0.55 * temperature_match + 0.45 * terrain_match
        if action == "forage":
            eaten = self.ecosystem.take_food(
                org.x, org.y, amount=2.0 * org.genome.fertility * (0.35 + herbivory) * (0.7 + habitat_quality)
            )
            org.energy += eaten * (1.8 + 1.5 * herbivory) * (0.7 + 0.6 * habitat_quality)
        elif action == "explore":
            dx = self.rng.choice((-1, 0, 1))
            dy = self.rng.choice((-1, 0, 1))
            hops = max(1, int(round(org.genome.speed)))
            for _ in range(hops):
                org.x = (org.x + dx) % self.cfg.width
                org.y = (org.y + dy) % self.cfg.height
            terrain_penalty = (1.0 - terrain_match) * self.cfg.terrain_drag_scale
            org.energy -= (0.12 + terrain_penalty) * hops
        elif action == "hunt":
            if not self._is_predator(org):
                org.energy -= 0.25
                return deaths
            candidates = [
                other
                for other in by_position[(org.x, org.y)]
                if other.alive and other.id != org.id and not self._is_predator(other)
            ]
            if candidates:
                target = self.rng.choice(candidates)
                hunt_power = 0.8 + 1.6 * org.genome.aggression + 0.8 * org.genome.speed + org.genome.diet
                evade_power = 0.8 + target.genome.speed + 0.6 * target.genome.vision
                hunt_power *= 0.6 + habitat_quality
                startup_hunt_scale = self.cfg.startup_hunt_suppression + (
                    1.0 - self.cfg.startup_hunt_suppression
                ) * startup_progress
                chance = (hunt_power / (hunt_power + evade_power)) * startup_hunt_scale
                if self.rng.random() < chance:
                    transfer = max(0.0, target.energy * (0.35 + 0.35 * org.genome.diet))
                    target.energy -= transfer
                    org.energy += transfer * self.cfg.hunt_efficiency * startup_hunt_scale
                    if target.energy <= 0:
                        target.alive = False
                        deaths += 1
                else:
                    org.energy -= 0.45
            else:
                org.energy -= 0.35
        else:
            org.energy += 0.1
        return deaths

    def _apply_recovery_seed(self) -> None:
        alive = [o for o in self.organisms if o.alive]
        predators = sum(1 for o in alive if self._is_predator(o))
        prey = len(alive) - predators

        if predators == 0:
            self.ticks_without_predators += 1
        else:
            self.ticks_without_predators = 0

        if self.tick % max(1, self.cfg.prey_recovery_interval) == 0 and prey < self.cfg.prey_recovery_floor:
            needed_prey = self.cfg.prey_recovery_floor - prey
            self._spawn_recovery_prey(needed_prey)

            alive = [o for o in self.organisms if o.alive]
            predators = sum(1 for o in alive if self._is_predator(o))
            prey = len(alive) - predators

        if (
            self.tick % max(1, self.cfg.predator_recovery_interval) == 0
            and prey >= self.cfg.predator_recovery_min_prey
            and predators < self.cfg.predator_recovery_floor
        ):
            needed_predators = self.cfg.predator_recovery_floor - predators
            self._spawn_recovery_predators(needed_predators)
            self.last_predator_recovery_tick = self.tick
            self.ticks_without_predators = 0

        extinction_recovery_due = self.ticks_without_predators >= self.cfg.predator_extinction_trigger_ticks
        cooldown_passed = (self.tick - self.last_predator_recovery_tick) >= self.cfg.predator_recovery_cooldown
        if predators == 0 and prey >= self.cfg.predator_recovery_min_prey_extinction and extinction_recovery_due and cooldown_passed:
            self._spawn_recovery_predators(self.cfg.predator_recovery_batch_size)
            self.last_predator_recovery_tick = self.tick
            self.ticks_without_predators = 0

    def _spawn_recovery_prey(self, count: int) -> None:
        for _ in range(max(0, count)):
            genome = random_genome(self.rng)
            genome.diet = min(genome.diet, self.cfg.predator_diet_threshold - 0.08)
            genome = genome.clamp()
            sid = self._register_species(genome)
            self.organisms.append(
                Organism(
                    id=self._new_id(),
                    species_id=sid,
                    genome=genome,
                    x=self.rng.randrange(self.cfg.width),
                    y=self.rng.randrange(self.cfg.height),
                    energy=self.cfg.start_energy * 0.85,
                )
            )

    def _spawn_recovery_predators(self, count: int) -> None:
        for _ in range(max(0, count)):
            genome = random_genome(self.rng)
            genome.diet = max(genome.diet, self.cfg.predator_diet_threshold + 0.1)
            genome.aggression = max(genome.aggression, 0.45)
            genome = genome.clamp()
            sid = self._register_species(genome)
            self.organisms.append(
                Organism(
                    id=self._new_id(),
                    species_id=sid,
                    genome=genome,
                    x=self.rng.randrange(self.cfg.width),
                    y=self.rng.randrange(self.cfg.height),
                    energy=self.cfg.start_energy,
                )
            )

    def _reproduce(self, parent: Organism) -> Organism:
        parent.energy -= self.cfg.reproduction_cost
        child_energy = max(5.0, parent.energy * 0.45)
        parent.energy -= child_energy * 0.5

        child_genome = mutate_genome(
            parent.genome,
            self.rng,
            mutation_rate=self.cfg.mutation_rate,
            mutation_strength=self.cfg.mutation_strength,
        )

        child_species = self._assign_species(parent.species_id, child_genome)

        child = Organism(
            id=self._new_id(),
            species_id=child_species,
            genome=child_genome,
            x=(parent.x + self.rng.choice((-1, 0, 1))) % self.cfg.width,
            y=(parent.y + self.rng.choice((-1, 0, 1))) % self.cfg.height,
            energy=child_energy,
            brain=parent.brain.clone(),
        )

        child.brain.mutate(self.rng, self.cfg.mutation_rate)

        return child
