from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationConfig:
    width: int = 80
    height: int = 60
    initial_population: int = 120
    initial_species: int = 6
    initial_food: float = 900.0
    food_regrowth_per_step: float = 45.0
    max_food_per_cell: float = 5.0

    start_energy: float = 30.0
    max_age: int = 250
    reproduction_energy_threshold: float = 20.0
    reproduction_cost: float = 3.0

    mutation_rate: float = 0.10
    mutation_strength: float = 0.12
    speciation_threshold: float = 0.45
    predator_diet_threshold: float = 0.55
    hunt_efficiency: float = 1.25
    temperature_stress_scale: float = 0.45
    terrain_drag_scale: float = 0.20
    seasonal_regrowth_amplitude: float = 0.35
    seasonal_period: int = 120
    ecosystem_carrying_density: float = 0.16
    prey_recovery_floor: int = 18
    prey_recovery_interval: int = 25
    predator_recovery_floor: int = 4
    predator_recovery_interval: int = 40
    predator_recovery_min_prey: int = 26
    predator_extinction_trigger_ticks: int = 12
    predator_recovery_cooldown: int = 10
    predator_recovery_min_prey_extinction: int = 14
    predator_recovery_batch_size: int = 3
    startup_stabilization_ticks: int = 70
    startup_regrowth_boost: float = 1.35
    startup_hunt_suppression: float = 0.45
    startup_reproduction_ramp: float = 0.45
    max_birth_fraction_per_tick: float = 0.12
    startup_birth_cap_scale: float = 0.45

    learning_rate: float = 0.08
    random_seed: int = 7
