from __future__ import annotations

import argparse

from .config import SimulationConfig
from .simulation import Simulation


def build_parser() -> argparse.ArgumentParser:
    defaults = SimulationConfig()
    parser = argparse.ArgumentParser(description="Project GENESIS digital life simulator")
    parser.add_argument("--width", type=int, default=defaults.width)
    parser.add_argument("--height", type=int, default=defaults.height)
    parser.add_argument("--population", type=int, default=defaults.initial_population)
    parser.add_argument("--initial-species", type=int, default=defaults.initial_species)
    parser.add_argument("--food", type=float, default=defaults.initial_food)
    parser.add_argument("--regrowth", type=float, default=defaults.food_regrowth_per_step)
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--headless", action="store_true", help="Run without matplotlib animation")
    parser.add_argument("--pygame", action="store_true", help="Run real-time pygame simulation window")
    parser.add_argument("--fps", type=int, default=60, help="Frames per second for --pygame mode")
    parser.add_argument("--cell-size", type=int, default=10, help="Cell size (pixels) for --pygame mode")
    parser.add_argument("--report-every", type=int, default=100, help="Ticks between headless reports")
    return parser


def run_headless(sim: Simulation, steps: int, report_every: int) -> None:
    snap = None
    cumulative_births = 0
    cumulative_deaths = 0
    for i in range(steps):
        snap = sim.step()
        cumulative_births += snap.births
        cumulative_deaths += snap.deaths
        if (i + 1) % max(1, report_every) == 0:
            print(
                f"tick={snap.tick} pop={snap.total_population} "
                f"prey={snap.prey_population} predator={snap.predator_population} "
                f"species={len(snap.species_population)} births={snap.births} deaths={snap.deaths} "
                f"cum_births={cumulative_births} cum_deaths={cumulative_deaths} "
                f"avg_energy={snap.average_energy:.2f}"
            )

    if snap is not None:
        print(
            f"final tick={snap.tick} pop={snap.total_population} "
            f"prey={snap.prey_population} predator={snap.predator_population} "
            f"species={len(snap.species_population)} "
            f"cum_births={cumulative_births} cum_deaths={cumulative_deaths} "
            f"avg_energy={snap.average_energy:.2f}"
        )


def main() -> None:
    args = build_parser().parse_args()

    cfg = SimulationConfig(
        width=args.width,
        height=args.height,
        initial_population=args.population,
        initial_species=args.initial_species,
        initial_food=args.food,
        food_regrowth_per_step=args.regrowth,
        random_seed=args.seed,
    )

    sim = Simulation(cfg)

    if args.headless:
        run_headless(sim, steps=args.steps, report_every=args.report_every)
        return

    if args.pygame:
        try:
            from .pygame_visualization import PygameVisualizer
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "Pygame mode requires pygame. Install with: pip install -e '.[pygame]' "
                "or use --headless / matplotlib mode."
            ) from exc

        viz = PygameVisualizer(sim, steps=args.steps, fps=args.fps, cell_size=args.cell_size)
        viz.run()
        return

    try:
        from .visualization import Visualizer
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Visualization requires matplotlib. Install with: pip install -e '.[viz]' "
            "or run with --headless."
        ) from exc

    viz = Visualizer(sim, steps=args.steps)
    viz.run()


if __name__ == "__main__":
    main()
