from __future__ import annotations

import pygame

from .simulation import Simulation


class PygameVisualizer:
    def __init__(
        self,
        sim: Simulation,
        steps: int = 1200,
        fps: int = 60,
        cell_size: int = 10,
        hud_height: int = 110,
    ):
        self.sim = sim
        self.steps = steps
        self.fps = max(1, fps)
        self.cell_size = max(4, cell_size)
        self.hud_height = hud_height

        self.width_px = self.sim.cfg.width * self.cell_size
        self.height_px = self.sim.cfg.height * self.cell_size + self.hud_height

    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption("Project GENESIS - Pygame")
        screen = pygame.display.set_mode((self.width_px, self.height_px))
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("consolas", 18)
        small_font = pygame.font.SysFont("consolas", 15)

        tick_count = 0
        paused = False
        running = True
        last_snapshot = None

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused

            if not paused and tick_count < self.steps:
                last_snapshot = self.sim.step()
                tick_count += 1

            self._draw_frame(screen, font, small_font, last_snapshot, paused, tick_count)
            pygame.display.flip()
            clock.tick(self.fps)

            if tick_count >= self.steps and not paused:
                paused = True

        pygame.quit()

    def _draw_frame(self, screen: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font, snapshot, paused: bool, tick_count: int) -> None:
        world_rect = pygame.Rect(0, 0, self.width_px, self.sim.cfg.height * self.cell_size)
        hud_rect = pygame.Rect(0, world_rect.height, self.width_px, self.hud_height)

        screen.fill((10, 18, 28), world_rect)
        self._draw_food(screen)
        self._draw_organisms(screen)

        screen.fill((14, 24, 36), hud_rect)
        pygame.draw.line(screen, (60, 85, 110), (0, world_rect.height), (self.width_px, world_rect.height), 2)

        if snapshot is not None:
            status = "PAUSED" if paused else "RUNNING"
            line1 = (
                f"{status}  tick={snapshot.tick}/{self.steps}  pop={snapshot.total_population}  "
                f"prey={snapshot.prey_population}  predator={snapshot.predator_population}"
            )
            line2 = (
                f"species={len(snapshot.species_population)}  births={snapshot.births}  "
                f"deaths={snapshot.deaths}  avg_energy={snapshot.average_energy:.2f}"
            )
        else:
            line1 = f"RUNNING  tick={tick_count}/{self.steps}"
            line2 = "warming up..."

        controls = "Controls: SPACE pause/resume | ESC quit"

        screen.blit(font.render(line1, True, (215, 235, 245)), (12, world_rect.height + 12))
        screen.blit(font.render(line2, True, (185, 218, 232)), (12, world_rect.height + 40))
        screen.blit(small_font.render(controls, True, (150, 190, 210)), (12, world_rect.height + 74))

    def _draw_food(self, screen: pygame.Surface) -> None:
        for y in range(self.sim.cfg.height):
            for x in range(self.sim.cfg.width):
                idx = self.sim.ecosystem.idx(x, y)
                food = self.sim.ecosystem.grid[idx]
                if food <= 0.05:
                    continue
                intensity = min(255, int(35 + (food / self.sim.cfg.max_food_per_cell) * 220))
                color = (18, intensity, 44)
                rect = pygame.Rect(
                    x * self.cell_size,
                    y * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                screen.fill(color, rect)

    def _draw_organisms(self, screen: pygame.Surface) -> None:
        for org in self.sim.organisms:
            x = int(org.x * self.cell_size + self.cell_size * 0.5)
            y = int(org.y * self.cell_size + self.cell_size * 0.5)
            radius = max(2, int(1 + min(6, org.energy / 9.0)))

            if self.sim._is_predator(org):
                color = (255, 94, 77)
                points = [
                    (x, y - radius),
                    (x - radius, y + radius),
                    (x + radius, y + radius),
                ]
                pygame.draw.polygon(screen, color, points)
            else:
                color = (124, 223, 106)
                pygame.draw.circle(screen, color, (x, y), radius)
