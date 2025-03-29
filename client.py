import pygame
import socket
import pickle
import threading

# Pygame Setup
pygame.init()
WIDTH, HEIGHT = 700, 700
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiplayer Snake")

# Colors (Each player gets a different color)
PLAYER_COLORS = [(0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 165, 0)]
FOOD_COLOR = (255, 0, 0)
BACKGROUND_COLOR = (0, 0, 0)

# Network Setup
SERVER_IP = '127.0.0.1'  # Change to actual server IP if needed
PORT = 5555
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))

# Game State
player_id = None
game_state = {}

# Listen for game updates
def receive_updates():
    global game_state, player_id
    while True:
        try:
            data = pickle.loads(client.recv(2048))  # Increased buffer size
            
            # Check if this is the initial connection data
            if "player_id" in data:
                player_id = data["player_id"]
                game_state = data.get("game_state", {})
                print(f"Received initial data. Player ID: {player_id}")
                print(f"Initial Game State: {game_state}")
            else:
                # Regular game state update
                game_state = data
                print(f"Received game state update: {game_state}")
        except Exception as e:
            print(f"Error receiving updates: {e}")
            break

# Start receiving updates
threading.Thread(target=receive_updates, daemon=True).start()

# Main Game Loop
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if player_id is not None and game_state and "players" in game_state:
                current_pos = game_state["players"][player_id]["pos"]
                
                if event.key == pygame.K_LEFT:
                    move = {"pos": (current_pos[0] - 50, current_pos[1]), "direction": "LEFT"}
                elif event.key == pygame.K_RIGHT:
                    move = {"pos": (current_pos[0] + 50, current_pos[1]), "direction": "RIGHT"}
                elif event.key == pygame.K_UP:
                    move = {"pos": (current_pos[0], current_pos[1] - 50), "direction": "UP"}
                elif event.key == pygame.K_DOWN:
                    move = {"pos": (current_pos[0], current_pos[1] + 50), "direction": "DOWN"}
                
                client.send(pickle.dumps(move))

    # Drawing
    window.fill(BACKGROUND_COLOR)

    # Draw players
    if game_state and "players" in game_state:
        for p_id, p_data in game_state["players"].items():
            pygame.draw.rect(window, PLAYER_COLORS[p_id], (p_data["pos"][0], p_data["pos"][1], 50, 50))

    # Draw food
    if game_state and "food" in game_state:
        pygame.draw.ellipse(window, FOOD_COLOR, (*game_state["food"], 50, 50))

    pygame.display.update()
    clock.tick(10)

pygame.quit()
client.close()