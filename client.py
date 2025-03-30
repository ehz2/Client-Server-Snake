import pygame
import socket
import pickle
import threading


"""
Client side of the game - contains code to initialize & update a client game state.
The client-side game state contains information about the position and direction of 
the client snake. This information is updated and sent to the server through sockets.
The client is also responsible for handling game state updates that it receives.
These updates contain position of food, positions of other snakes, etc.
"""


# Initialize pygame (for the game interface)
pygame.init()

# Constants (defines player size, screen size, etc.)
GAME_WIDTH = 1000
GAME_HEIGHT = 1000
SPACE_SIZE = 20
PLAYER_COLORS = [(0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 165, 0)]
FOOD_COLOR = (255, 0, 0)
BACKGROUND_COLOR = (0, 0, 0)

# Setup the game window 
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Multiplayer Snake")

# Fonts for score
font = pygame.font.SysFont('Arial', 20)

# Network setup & socket connection to server
SERVER_IP = '127.0.0.1'  # Change to LAN IP if needed for multiple devices
PORT = 5555
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))

# Initialize empty game state
player_id = None
game_state = {}

# Current direction of snake (used for moving logic)
current_direction = None  

def receive_updates():
    """
    Parameters: NULL (Nothing)

    Function for receiving updates from server.
    If first connection, establish player ID and game_state.
    Otherwise, update game state with new information.

    Returns: NULL (Nothing)
    """

    # Previously initialized global variables
    global game_state, player_id, current_direction

    # Loop to constantly receive updates
    while True:
        try:

            # Access socket data via byte stream
            data = pickle.loads(client.recv(4096)) 
            
            # If this is the initial connection data
            if isinstance(data, dict) and "player_id" in data:
                player_id = data["player_id"]
                game_state = data.get("game_state", {})

                if str(player_id) in game_state["players"]:
                    current_direction = game_state["players"][str(player_id)]["direction"]
                    
                print(f"Connected as Player {player_id + 1}, starting direction: {current_direction}")

            # Otherwise, a regular game state update
            else:
                game_state = data

                # Update our current direction 
                if "players" in game_state and str(player_id) in game_state["players"]:
                    current_direction = game_state["players"][str(player_id)]["direction"]

        # Exception thrown in case of error (ie. too much data)
        except Exception as e:
            print(f"Error receiving updates: {e}")
            break


# Start receiving updates by threading the receive_updates function
threading.Thread(target=receive_updates, daemon=True).start()

# Main game loop
clock = pygame.time.Clock()
running = True

# While the game is running
while running:
    for event in pygame.event.get():

        # If user has quit or game has ended
        if event.type == pygame.QUIT:
            running = False
        
        # If a key has been pressed
        elif event.type == pygame.KEYDOWN and current_direction is not None:
            new_direction = None
            
            # Prevent 180-degree turns by checking the current direction
            if event.key == pygame.K_LEFT and current_direction != 'RIGHT':
                new_direction = 'LEFT'

            elif event.key == pygame.K_RIGHT and current_direction != 'LEFT':
                new_direction = 'RIGHT'

            elif event.key == pygame.K_UP and current_direction != 'DOWN':
                new_direction = 'UP'

            elif event.key == pygame.K_DOWN and current_direction != 'UP':
                new_direction = 'DOWN'
                
            # Send updates if direction has changed and snake has not crashed
            if new_direction and player_id is not None:
                client.send(pickle.dumps({"direction": new_direction, "player_id": player_id}))
                current_direction = new_direction  

    # Draw the background
    window.fill(BACKGROUND_COLOR)

    # Draw the food
    if game_state and "food" in game_state:
        pygame.draw.ellipse(window, FOOD_COLOR, 
                          (game_state["food"][0], game_state["food"][1], SPACE_SIZE, SPACE_SIZE))

    # Draw all other snakes
    if game_state and "players" in game_state:
        for p_id, player_data in game_state["players"].items():
            p_id = int(p_id)  
            color = PLAYER_COLORS[p_id % len(PLAYER_COLORS)]
            
            # Draw each segment of the snake(s)
            for segment in player_data["body"]:
                pygame.draw.rect(window, color, 
                              (segment[0], segment[1], SPACE_SIZE, SPACE_SIZE))
    
    # Draw the scores of all snakes
    if game_state and "scores" in game_state:
        y_offset = 10
        for p_id, score in game_state["scores"].items():
            p_id = int(p_id)
            color = PLAYER_COLORS[p_id % len(PLAYER_COLORS)]
            score_text = font.render(f"Player {p_id + 1}: {score}", True, color)
            window.blit(score_text, (10, y_offset))
            y_offset += 35
    
    # Display the game over when the game has ended
    if game_state and "game_over" in game_state and game_state["game_over"]:
        game_over_text = font.render("GAME OVER", True, (255, 0, 0))
        window.blit(game_over_text, (GAME_WIDTH // 2 - 100, GAME_HEIGHT // 2 - 50))
        
        # Display winner if there is one
        if "winner" in game_state:
            winner = game_state["winner"]
            winner_text = font.render(f"Player {int(winner) + 1} Wins!", True, PLAYER_COLORS[int(winner) % len(PLAYER_COLORS)])
            window.blit(winner_text, (GAME_WIDTH // 2 - 100, GAME_HEIGHT // 2))

        # Display tie game message if head on collision results in tie
        elif "tie" in game_state and game_state["tie"]:
            tie_text = font.render("Game Tied - All Players Died!", True, (255, 255, 255))
            window.blit(tie_text, (GAME_WIDTH // 2 - 150, GAME_HEIGHT // 2))

    pygame.display.update()
    clock.tick(10)  # Must keep consistent with server speed

# Quit and close the client side
pygame.quit()
client.close()
