import pygame
import random
import time
import math
from typing import List, Tuple
import os

# Game configuration from original
CONFIG = {
    'CANVAS_WIDTH': 1200,
    'CANVAS_HEIGHT': 800,
    'BAT_WIDTH': 32,
    'BAT_HEIGHT': 32,
    'BAT_SCALE': 2,
    'BASE_MOVE_SPEED': 5,
    'WORLD_WIDTH': 2400,
    'WORLD_HEIGHT': 1600,
    'BG_SPEED_1': 2,
    'BG_SPEED_2': 1,
    'BG_SPEED_3': 0.5,
    'OBSTACLE_WIDTH': 60,
    'OBSTACLE_HEIGHT': 60,
    'OBSTACLE_SPEED': 3,
    'OBSTACLE_SPAWN_INTERVAL': 2.0,
    'GRAVITY': 0.5,
    'JUMP_FORCE': -10,
    'MAX_FALL_SPEED': 10
}

class Obstacle:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.width = CONFIG['OBSTACLE_WIDTH']
        self.height = CONFIG['OBSTACLE_HEIGHT']
        self.speed = CONFIG['OBSTACLE_SPEED']
        self.is_active = True
        
        # Load obstacle sprite
        try:
            self.image = pygame.image.load(os.path.join("assets", "sprites", "obstacle.png")).convert_alpha()
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except Exception as e:
            print(f"Error loading obstacle sprite: {e}")
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(self.image, (255, 0, 0), (0, 0, self.width, self.height))

    def update(self):
        self.x -= self.speed
        if self.x < -self.width:
            self.is_active = False

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, (self.x, self.y))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

class Bat:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.width = CONFIG['BAT_WIDTH'] * CONFIG['BAT_SCALE']
        self.height = CONFIG['BAT_HEIGHT'] * CONFIG['BAT_SCALE']
        self.speed = CONFIG['BASE_MOVE_SPEED']
        self.is_active = True
        self.frame = 0
        self.frame_count = 0
        self.frame_speed = 10
        self.total_frames = 4
        self.vx = 0
        self.vy = 0
        self.target_vx = 0
        self.target_vy = 0
        self.acceleration = 0.3
        self.deceleration = 0.2
        self.is_jumping = False
        self.facing_right = True
        
        # Load bat sprite sheet
        try:
            self.sprite_sheet = pygame.image.load(os.path.join("assets", "sprites", "batsprite.png")).convert_alpha()
            self.frame_width = self.sprite_sheet.get_width() // self.total_frames
            self.frame_height = self.sprite_sheet.get_height()
            self.image = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
            self.image.blit(self.sprite_sheet, (0, 0), (0, 0, self.frame_width, self.frame_height))
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except Exception as e:
            print(f"Error loading bat sprite: {e}")
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.rect(self.image, (255, 255, 255), (0, 0, self.width, self.height))

    def move(self, dx: int):
        self.target_vx = dx * self.speed
        self.facing_right = dx > 0
        
        # Apply acceleration/deceleration
        if abs(self.target_vx - self.vx) > 0:
            if abs(self.target_vx) > abs(self.vx):
                self.vx += self.acceleration * (1 if self.target_vx > self.vx else -1)
            else:
                self.vx += self.deceleration * (-1 if self.vx > 0 else 1)
        
        self.x += self.vx
        # Keep bat within screen bounds
        self.x = max(0, min(self.x, CONFIG['CANVAS_WIDTH'] - self.width))

    def jump(self):
        if not self.is_jumping:
            self.vy = CONFIG['JUMP_FORCE']
            self.is_jumping = True

    def update(self):
        # Apply gravity
        if self.is_jumping:
            self.vy += CONFIG['GRAVITY']
            self.vy = min(self.vy, CONFIG['MAX_FALL_SPEED'])
            self.y += self.vy
            
            # Check if landed
            if self.y >= CONFIG['CANVAS_HEIGHT'] - self.height:
                self.y = CONFIG['CANVAS_HEIGHT'] - self.height
                self.vy = 0
                self.is_jumping = False
        
        # Animate sprite
        self.frame_count += 1
        if self.frame_count >= self.frame_speed:
            self.frame_count = 0
            self.frame = (self.frame + 1) % self.total_frames
            # Update current frame from sprite sheet
            self.image.fill((0, 0, 0, 0))  # Clear current frame
            frame_x = self.frame * self.frame_width
            self.image.blit(self.sprite_sheet, (0, 0), (frame_x, 0, self.frame_width, self.frame_height))
            # Flip image if facing left
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
            self.image = pygame.transform.scale(self.image, (self.width, self.height))

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, (self.x, self.y))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.width = CONFIG['CANVAS_WIDTH']
        self.height = CONFIG['CANVAS_HEIGHT']
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Bat Times")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.score = 0
        self.bats: List[Bat] = []
        self.obstacles: List[Obstacle] = []
        self.last_bat_time = time.time()
        self.last_obstacle_time = time.time()
        self.bat_spawn_interval = 3.0
        self.font = pygame.font.Font(None, 36)
        
        # Load background layers
        try:
            self.bg_layers = []
            for i in range(1, 4):
                bg = pygame.image.load(os.path.join("assets", "sprites", f"layer{i}.png")).convert_alpha()
                # Scale background layers differently
                scale = 1 if i == 1 else (0.75 if i == 2 else 0.5)
                scaled_width = int(CONFIG['WORLD_WIDTH'] * scale)
                scaled_height = int(CONFIG['WORLD_HEIGHT'] * scale)
                bg = pygame.transform.scale(bg, (scaled_width, scaled_height))
                self.bg_layers.append(bg)
        except Exception as e:
            print(f"Error loading background layers: {e}")
            self.bg_layers = [pygame.Surface((self.width, self.height)) for _ in range(3)]
            for bg in self.bg_layers:
                bg.fill((20, 20, 40))
        
        self.bg_scroll = [0, 0, 0]
        self.bg_speeds = [CONFIG['BG_SPEED_1'], CONFIG['BG_SPEED_2'], CONFIG['BG_SPEED_3']]
        
        # Initialize audio
        try:
            self.background_music = pygame.mixer.Sound(os.path.join("assets", "audio", "backmusic.mp3"))
            self.background_music.set_volume(0.5)
            self.background_music.play(-1)  # Loop indefinitely
        except Exception as e:
            print(f"Error loading background music: {e}")

    def spawn_bat(self):
        current_time = time.time()
        if current_time - self.last_bat_time >= self.bat_spawn_interval:
            x = self.width // 2 - CONFIG['BAT_WIDTH'] * CONFIG['BAT_SCALE'] // 2
            y = self.height - CONFIG['BAT_HEIGHT'] * CONFIG['BAT_SCALE'] - 10
            self.bats.append(Bat(x, y))
            self.last_bat_time = current_time

    def spawn_obstacle(self):
        current_time = time.time()
        if current_time - self.last_obstacle_time >= CONFIG['OBSTACLE_SPAWN_INTERVAL']:
            x = self.width
            y = random.randint(0, self.height - CONFIG['OBSTACLE_HEIGHT'])
            self.obstacles.append(Obstacle(x, y))
            self.last_obstacle_time = current_time

    def check_collisions(self):
        for bat in self.bats:
            bat_rect = bat.get_rect()
            for obstacle in self.obstacles:
                if obstacle.is_active and bat_rect.colliderect(obstacle.get_rect()):
                    self.game_over = True
                    return

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    for bat in self.bats:
                        bat.jump()
                elif event.key == pygame.K_SPACE and self.game_over:
                    self.reset_game()

        if not self.game_over:
            keys = pygame.key.get_pressed()
            direction = 0
            if keys[pygame.K_LEFT]:
                direction = -1
            if keys[pygame.K_RIGHT]:
                direction = 1
                
            for bat in self.bats:
                bat.move(direction)

    def reset_game(self):
        self.game_over = False
        self.score = 0
        self.bats.clear()
        self.obstacles.clear()
        self.last_bat_time = time.time()
        self.last_obstacle_time = time.time()
        self.spawn_bat()

    def update(self):
        if not self.game_over:
            self.spawn_bat()
            self.spawn_obstacle()
            
            # Update background scroll with wrapping
            for i in range(len(self.bg_scroll)):
                self.bg_scroll[i] = (self.bg_scroll[i] + self.bg_speeds[i]) % self.bg_layers[i].get_width()
            
            # Update all bats and obstacles
            for bat in self.bats:
                bat.update()
            for obstacle in self.obstacles:
                obstacle.update()
            
            # Remove inactive obstacles
            self.obstacles = [obs for obs in self.obstacles if obs.is_active]
            
            # Update score
            self.score += 1
            
            # Check for collisions
            self.check_collisions()

    def draw(self):
        # Draw background layers with parallax scrolling
        for i, layer in enumerate(self.bg_layers):
            # Draw each layer twice for seamless scrolling
            self.screen.blit(layer, (-self.bg_scroll[i], 0))
            self.screen.blit(layer, (layer.get_width() - self.bg_scroll[i], 0))
        
        # Draw all bats and obstacles
        for bat in self.bats:
            bat.draw(self.screen)
        for obstacle in self.obstacles:
            obstacle.draw(self.screen)
        
        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        
        if self.game_over:
            game_over_text = self.font.render("GAME OVER - Press SPACE to restart", True, (255, 255, 255))
            text_rect = game_over_text.get_rect(center=(self.width // 2, self.height // 2))
            self.screen.blit(game_over_text, text_rect)
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

        pygame.quit()

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main() 