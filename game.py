import pygame
import random

# Initialize Pygame
pygame.init()

# Constants
GAME_WIDTH = 1000
GAME_HEIGHT = 1000
SPEED = 10
SPACE_SIZE = 20
BODY_PARTS = 3
SNAKE_COLOR = (0, 255, 0)  # Green
FOOD_COLOR = (255, 0, 0)  # Red
BACKGROUND_COLOR = (0, 0, 0)  # Black

# Setup the game window
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Snake Game")

# Fonts for score
font = pygame.font.SysFont('consolas', 40)

# Initialize variables
score = 0
direction = 'DOWN'

class Snake:
    def __init__(self):
        self.body_size = BODY_PARTS
        self.coordinates = []
        self.squares = []

        # Initialize the snake's body
        for i in range(0, BODY_PARTS):
            self.coordinates.append([0, 0])

    def draw(self):
        for segment in self.coordinates:
            pygame.draw.rect(window, SNAKE_COLOR, pygame.Rect(segment[0], segment[1], SPACE_SIZE, SPACE_SIZE))


class Food:
    def __init__(self):
        # Ensure the random values are integers by using int()
        self.coordinates = [
            random.randint(0, int(GAME_WIDTH / SPACE_SIZE) - 1) * SPACE_SIZE,
            random.randint(0, int(GAME_HEIGHT / SPACE_SIZE) - 1) * SPACE_SIZE
        ]

    def draw(self):
        pygame.draw.ellipse(window, FOOD_COLOR, pygame.Rect(self.coordinates[0], self.coordinates[1], SPACE_SIZE, SPACE_SIZE))


def next_turn(snake, food):
    global score, direction

    x, y = snake.coordinates[0]

    if direction == "UP":
        y -= SPACE_SIZE
    elif direction == "DOWN":
        y += SPACE_SIZE
    elif direction == "LEFT":
        x -= SPACE_SIZE
    elif direction == "RIGHT":
        x += SPACE_SIZE

    # Insert new head to the snake
    snake.coordinates.insert(0, [x, y])

    # Check if snake eats food
    if x == food.coordinates[0] and y == food.coordinates[1]:
        score += 1
        food = Food()
    else:
        snake.coordinates.pop()

    # Check for collisions
    if check_collisions(snake):
        game_over()

    return food


def change_direction(new_direction):
    global direction

    if new_direction == 'LEFT' and direction != 'RIGHT':
        direction = 'LEFT'
    elif new_direction == 'RIGHT' and direction != 'LEFT':
        direction = 'RIGHT'
    elif new_direction == 'UP' and direction != 'DOWN':
        direction = 'UP'
    elif new_direction == 'DOWN' and direction != 'UP':
        direction = 'DOWN'


def check_collisions(snake):
    x, y = snake.coordinates[0]

    # Check if snake hits the boundaries
    if x < 0 or x >= GAME_WIDTH or y < 0 or y >= GAME_HEIGHT:
        return True

    # Check if snake hits itself
    for body_part in snake.coordinates[1:]:
        if x == body_part[0] and y == body_part[1]:
            return True

    return False


def game_over():
    global score

    window.fill(BACKGROUND_COLOR)
    game_over_text = font.render("GAME OVER", True, (255, 0, 0))
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    window.blit(game_over_text, (GAME_WIDTH / 4, GAME_HEIGHT / 3))
    window.blit(score_text, (GAME_WIDTH / 3, GAME_HEIGHT / 2))

    pygame.display.update()
    pygame.time.delay(2000)
    pygame.quit()
    quit()


# Main game loop
def game_loop():
    global score

    snake = Snake()
    food = Food()

    # Game loop
    clock = pygame.time.Clock()
    running = True
    while running:
        window.fill(BACKGROUND_COLOR)

        # Draw the snake and food
        snake.draw()
        food.draw()

        # Display the score
        score_text = font.render(f"Score: {score}", True, (255, 255, 255))
        window.blit(score_text, (10, 10))

        pygame.display.update()

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    change_direction('LEFT')
                elif event.key == pygame.K_RIGHT:
                    change_direction('RIGHT')
                elif event.key == pygame.K_UP:
                    change_direction('UP')
                elif event.key == pygame.K_DOWN:
                    change_direction('DOWN')

        # Move the snake and check for collisions
        food = next_turn(snake, food)

        # Control the game speed
        clock.tick(SPEED)

    pygame.quit()


if __name__ == "__main__":
    game_loop()
    