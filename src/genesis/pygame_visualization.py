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
        animation_speed = self.fps  # Current animation speed (FPS)

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_UP or event.key == pygame.K_EQUALS:
                        animation_speed = min(120, animation_speed + 5)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_MINUS:
                        animation_speed = max(5, animation_speed - 5)

            if not paused and tick_count < self.steps:
                last_snapshot = self.sim.step()
                tick_count += 1

            self._draw_frame(screen, font, small_font, last_snapshot, paused, tick_count, animation_speed)
            pygame.display.flip()
            clock.tick(animation_speed)

            if tick_count >= self.steps and not paused:
                paused = True

        pygame.quit()

    def _draw_frame(self, screen: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font, snapshot, paused: bool, tick_count: int, animation_speed: int) -> None:
        world_rect = pygame.Rect(0, 0, self.width_px, self.sim.cfg.height * self.cell_size)
        hud_rect = pygame.Rect(0, world_rect.height, self.width_px, self.hud_height)

        screen.fill((10, 18, 28), world_rect)
        self._draw_environment(screen)
        self._draw_food(screen)
        self._draw_organisms(screen)
        self._draw_quadrant_borders(screen, font)

        screen.fill((14, 24, 36), hud_rect)
        pygame.draw.line(screen, (60, 85, 110), (0, world_rect.height), (self.width_px, world_rect.height), 2)

        if snapshot is not None:
            status = "PAUSED" if paused else "RUNNING"
            line1 = (
                f"{status}  tick={snapshot.tick}/{self.steps}  pop={snapshot.total_population}  "
                f"prey={snapshot.prey_population}  predator={snapshot.predator_population}  speed={animation_speed}fps"
            )
            line2 = (
                f"species={len(snapshot.species_population)}  births={snapshot.births}  "
                f"deaths={snapshot.deaths}  avg_energy={snapshot.average_energy:.2f}"
            )
        else:
            line1 = f"RUNNING  tick={tick_count}/{self.steps}  speed={animation_speed}fps"
            line2 = "warming up..."

        controls = "Controls: SPACE pause | UP/DOWN speed | ESC quit"

        screen.blit(font.render(line1, True, (215, 235, 245)), (12, world_rect.height + 12))
        screen.blit(font.render(line2, True, (185, 218, 232)), (12, world_rect.height + 40))
        screen.blit(small_font.render(controls, True, (150, 190, 210)), (12, world_rect.height + 74))

    def _draw_environment(self, screen: pygame.Surface) -> None:
        """Render the 4 quadrant ecosystems with temperature/terrain coloring."""
        for y in range(self.sim.cfg.height):
            for x in range(self.sim.cfg.width):
                idx = self.sim.ecosystem.idx(x, y)
                temp = self.sim.ecosystem.temperature_map[idx]
                terrain = self.sim.ecosystem.terrain_map[idx]
                
                # Temperature dominates color hue (cold=blue, hot=red)
                # Terrain affects brightness (smooth=bright, rocky=dark)
                brightness = 0.4 + 0.6 * (1.0 - terrain)  # rocky = darker
                
                # Hue from temperature: cold (0.2) -> blue, hot (0.8) -> red
                if temp < 0.35:  # Cold (Arctic)
                    r = int(50 * brightness)
                    g = int(150 * brightness)
                    b = int(200 * brightness)
                elif temp < 0.55:  # Temperate
                    r = int(100 * brightness)
                    g = int(180 * brightness)
                    b = int(120 * brightness)
                elif temp < 0.75:  # Warm
                    r = int(200 * brightness)
                    g = int(180 * brightness)
                    b = int(80 * brightness)
                else:  # Hot (Desert/Tropical)
                    r = int(220 * brightness)
                    g = int(150 * brightness)
                    b = int(80 * brightness)
                
                color = (r, g, b)
                rect = pygame.Rect(
                    x * self.cell_size,
                    y * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                screen.fill(color, rect)

    def _draw_food(self, screen: pygame.Surface) -> None:
        """Render food resources on top of environment layer."""
        for y in range(self.sim.cfg.height):
            for x in range(self.sim.cfg.width):
                idx = self.sim.ecosystem.idx(x, y)
                food = self.sim.ecosystem.grid[idx]
                if food <= 0.1:
                    continue
                # Green overlay for food, opacity based on amount
                intensity = min(200, int(100 + (food / self.sim.cfg.max_food_per_cell) * 155))
                color = (50, intensity, 80)
                rect = pygame.Rect(
                    x * self.cell_size,
                    y * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                screen.fill(color, rect)

    def _draw_quadrant_borders(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """Draw quadrant dividers and labels."""
        mid_x = self.sim.cfg.width * self.cell_size // 2
        mid_y = self.sim.cfg.height * self.cell_size // 2
        
        # Draw divider lines
        pygame.draw.line(screen, (100, 130, 160), (mid_x, 0), (mid_x, mid_y * 2), 2)
        pygame.draw.line(screen, (100, 130, 160), (0, mid_y), (mid_x * 2, mid_y), 2)
        
        # Quadrant labels with semi-transparent backgrounds
        label_font = pygame.font.SysFont("consolas", 14, bold=True)
        labels = [
            ("Arctic", 20, 20),
            ("Desert", mid_x + 20, 20),
            ("Forest", 20, mid_y + 20),
            ("Jungle", mid_x + 20, mid_y + 20),
        ]
        
        for text, x, y in labels:
            surf = label_font.render(text, True, (220, 220, 220))
            screen.blit(surf, (x, y))

    def _draw_organisms(self, screen: pygame.Surface) -> None:
        """Render organisms on top of all layers."""
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
