from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from .simulation import Simulation, Snapshot


class Visualizer:
    def __init__(self, sim: Simulation, steps: int = 1200, interval_ms: int = 40):
        self.sim = sim
        self.steps = steps
        self.interval_ms = interval_ms
        self.anim: FuncAnimation | None = None
        self.population_history: list[int] = []
        self.active_species_history: list[int] = []
        self.prey_history: list[int] = []
        self.predator_history: list[int] = []

        self.fig, (self.ax_world, self.ax_stats) = plt.subplots(1, 2, figsize=(14, 6))
        self.fig.suptitle("Project GENESIS: Digital Life Simulator")

    def run(self) -> None:
        backend = plt.get_backend().lower()
        if "agg" in backend:
            for _ in range(self.steps):
                self._update(0)
            output = Path.cwd() / "genesis_snapshot.png"
            plt.tight_layout()
            self.fig.savefig(output, dpi=150)
            print(
                f"Matplotlib backend '{backend}' is non-interactive. "
                f"Saved simulation snapshot to: {output}"
            )
            return

        self.anim = FuncAnimation(self.fig, self._update, frames=self.steps, interval=self.interval_ms, repeat=False)
        plt.tight_layout()
        plt.show()

    def _update(self, _: int):
        snap = self.sim.step()
        self.population_history.append(snap.total_population)
        self.active_species_history.append(len(snap.species_population))
        self.prey_history.append(snap.prey_population)
        self.predator_history.append(snap.predator_population)

        self.ax_world.clear()
        self.ax_stats.clear()

        self._draw_world(snap)
        self._draw_stats(snap)

    def _draw_world(self, snap: Snapshot) -> None:
        self.ax_world.set_title(f"Tick {snap.tick} | Pop {snap.total_population} | Species {len(snap.species_population)}")
        self.ax_world.set_xlim(0, self.sim.cfg.width)
        self.ax_world.set_ylim(0, self.sim.cfg.height)
        self.ax_world.set_facecolor("#101820")

        prey_x: list[int] = []
        prey_y: list[int] = []
        prey_s: list[float] = []
        predator_x: list[int] = []
        predator_y: list[int] = []
        predator_s: list[float] = []

        for org in self.sim.organisms:
            if self.sim._is_predator(org):
                predator_x.append(org.x)
                predator_y.append(org.y)
                predator_s.append(max(14.0, org.energy * 1.2))
            else:
                prey_x.append(org.x)
                prey_y.append(org.y)
                prey_s.append(max(10.0, org.energy))

        self.ax_world.scatter(prey_x, prey_y, s=prey_s, alpha=0.75, c="#7dd36f", label="Prey")
        self.ax_world.scatter(predator_x, predator_y, s=predator_s, alpha=0.85, c="#ff6b57", marker="^", label="Predator")
        self.ax_world.legend(loc="upper right", fontsize=8)

    def _draw_stats(self, snap: Snapshot) -> None:
        self.ax_stats.set_title("Population Dynamics")
        self.ax_stats.plot(self.population_history, label="Population", linewidth=2.0)
        self.ax_stats.plot(self.prey_history, label="Prey", linewidth=1.8)
        self.ax_stats.plot(self.predator_history, label="Predator", linewidth=1.8)
        self.ax_stats.plot(self.active_species_history, label="Active species", linewidth=2.0)
        self.ax_stats.set_xlabel("Ticks")
        self.ax_stats.set_ylabel("Count")
        self.ax_stats.grid(alpha=0.3)
        self.ax_stats.legend()

        extinct = self.sim.next_species_id - 1 - len(snap.species_population)
        txt = (
            f"Births: {snap.births}\n"
            f"Deaths: {snap.deaths}\n"
            f"Prey: {snap.prey_population}\n"
            f"Predators: {snap.predator_population}\n"
            f"Avg energy: {snap.average_energy:.2f}\n"
            f"Ever evolved species: {self.sim.next_species_id - 1}\n"
            f"Extinct species: {max(0, extinct)}"
        )
        self.ax_stats.text(0.02, 0.98, txt, transform=self.ax_stats.transAxes, va="top", fontsize=10)
