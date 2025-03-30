import pygame
import socket
import pickle
import threading
import random
import time


"""
Server side of the game - contains code to initialize and run the game.
The server-side game state contains information about the position and direction of 
all the snakes. Information is received and broadcasted to all clients via sockets.
The server is also responsible for handling game logic and determining winners.
Logic includes movement, food generation, various collisions, etc.
"""


# Server Constants (defines screen size, ports, etc.)
HOST = '0.0.0.0'
PORT = 5555
GAME_WIDTH = 1000
GAME_HEIGHT = 1000
SPACE_SIZE = 20
BODY_PARTS = 3
SPEED = 10

# Unique starting positions and directions for each player
starting_positions = [
    {"pos": [100, 100], "direction": "RIGHT"},
    {"pos": [900, 900], "direction": "LEFT"},
    {"pos": [100, 900], "direction": "RIGHT"},
    {"pos": [900, 100], "direction": "LEFT"}
]

# Initialize clients and max_player count
clients = {}
max_players = 0

# Get user input to decide player count
try:
    max_players = min(4, max(2, int(input("Enter number of players (2-4): "))))

# At minimum, 2 players are required to proceed
except: 
    max_players = 2
    print("Invalid input. Using 2 players.")

# Variables for initial food generation (Area around the center of screen)
CENTER_X = 500  
CENTER_Y = 500  
AREA_SIZE = 200  

# Calculate x-boundaries for the food to spawn
MIN_X = CENTER_X - (AREA_SIZE // 2)  
MAX_X = CENTER_X + (AREA_SIZE // 2) - SPACE_SIZE  

# Calculate y-boundaries for the food to spawn
MIN_Y = CENTER_Y - (AREA_SIZE // 2)  
MAX_Y = CENTER_Y + (AREA_SIZE // 2) - SPACE_SIZE  

# Game state (server side that is updated with each client message)
game_state = {
    "players": {},
    "food": [random.randint(MIN_X // SPACE_SIZE, MAX_X // SPACE_SIZE) * SPACE_SIZE,
             random.randint(MIN_Y // SPACE_SIZE, MAX_Y // SPACE_SIZE) * SPACE_SIZE],
    "scores": {},
    "game_over": False,
    "countdown": False,
    "countdown_value": 3,
    "game_started": False
}


# Lock for thread-safe game state updates
game_state_lock = threading.Lock()


def initialize_snake(position, direction):
    """
    Parameters: position (x,y) of the snake, direction (left, right, etc.) of the snake)

    Function for initializing snakes using their position and direction.
    Sets up the head and body of the snake in the direction it's facing.

    Returns: List of positions called 'coordinates' that represents the snake 
    """

    # Variables 
    coordinates = []
    x, y = position
    
    # Initialize based on direction
    if direction == "RIGHT":
        for i in range(BODY_PARTS):
            coordinates.append([x - i * SPACE_SIZE, y])

    elif direction == "LEFT":
        for i in range(BODY_PARTS):
            coordinates.append([x + i * SPACE_SIZE, y])

    elif direction == "UP":
        for i in range(BODY_PARTS):
            coordinates.append([x, y + i * SPACE_SIZE])

    elif direction == "DOWN":
        for i in range(BODY_PARTS):
            coordinates.append([x, y - i * SPACE_SIZE])
    
    return coordinates


def handle_client(conn, addr, player_id):
    """
    Parameters: socket connection object (conn), address of client (addr), player number (player_id)  

    Function for handling the different snakes.
    Uses initialize_snake(position, direction) to set up the snakes and sends the information to clients.
    Handles movements and ensures snakes don't 180-degree collide on themselves.
    
    Returns: NULL (Nothing)
    """

    # Global server game state
    global game_state
    try:

        # Initialize player in game state
        with game_state_lock:
            start_data = starting_positions[player_id]
            initial_body = initialize_snake(start_data["pos"], start_data["direction"])
            
            game_state["players"][str(player_id)] = {
                "body": initial_body,
                "direction": start_data["direction"]
            }
            game_state["scores"][str(player_id)] = 0
        
        # Send initial player info, game state, and max_players
        initial_data = {
            "player_id": player_id,
            "game_state": game_state,
            "max_players": max_players  
        }
        conn.send(pickle.dumps(initial_data))
        
        # While snake is active 
        while True:
            try:

                # Load data from clients
                data = pickle.loads(conn.recv(1024))

                # Validate and update player direction 
                if "direction" in data and "player_id" in data:
                    with game_state_lock:
                        player_key = str(data["player_id"])

                        # Ensure the player exists
                        if player_key in game_state["players"]:
                            current_direction = game_state["players"][player_key]["direction"]
                            new_direction = data["direction"]
                            
                            # Server-side validation to prevent 180-degree turns
                            valid_change = True
                            if (current_direction == 'UP' and new_direction == 'DOWN') or \
                               (current_direction == 'DOWN' and new_direction == 'UP') or \
                               (current_direction == 'LEFT' and new_direction == 'RIGHT') or \
                               (current_direction == 'RIGHT' and new_direction == 'LEFT'):
                                valid_change = False
                                
                            # Apply new direction 
                            if valid_change:
                                game_state["players"][player_key]["direction"] = new_direction

            # Exception for errors during data processing
            except Exception as e:
                print(f"Error processing client {player_id} data: {e}")
                break

    # Exception for errors during connection
    except Exception as e:
        print(f"Initial connection error with player {player_id}: {e}")

    # Clean up remaining resources
    finally:
        with game_state_lock:
            if str(player_id) in game_state["players"]:
                del game_state["players"][str(player_id)]

            if str(player_id) in game_state["scores"]:
                del game_state["scores"][str(player_id)]

        if player_id in clients:
            del clients[player_id]

        # Close connection
        conn.close()


def move_snake(player_id, player_data):
    """
    Parameters: player number (player_id), dictionary of a player that contains position coordinates direction (player_data)

    Function that moves the snake in the current direction.
    If the snake lands on a food tile, update accordingly.
    
    Returns: Boolean called food_collision that says whether or not a snake has eaten an apple
    """

    # Variables
    direction = player_data["direction"]
    body = player_data["body"]
    head_x, head_y = body[0]
    
    # Calculate new head position
    if direction == "UP":
        new_head = [head_x, head_y - SPACE_SIZE]

    elif direction == "DOWN":
        new_head = [head_x, head_y + SPACE_SIZE]

    elif direction == "LEFT":
        new_head = [head_x - SPACE_SIZE, head_y]

    elif direction == "RIGHT":
        new_head = [head_x + SPACE_SIZE, head_y]
    
    # Insert new head
    body.insert(0, new_head)
    
    # Boolean for food collisions
    food_collision = False

    # If a food collision has occured
    if new_head[0] == game_state["food"][0] and new_head[1] == game_state["food"][1]:

        # Increase score of the snake that ate it
        game_state["scores"][player_id] += 1

        # Generate new food (food has been eaten)
        food_collision = True

    else:

        # Remove tail if no food was eaten
        body.pop()
    
    return food_collision


# def check_collision(player_id, player_data):
#     """
#     Parameters: player number (player_id), dictionary of a player that contains position coordinates direction (player_data)

#     *** TESTING FUNCTION ***
#     Used to run the game without any collision logic.

#     Returns: Boolean (False) so that snake never dies
#     """

#     # Variables
#     head_x, head_y = player_data["body"][0]
#     collision_occurred = False
#     collision_type = ""
    
#     # Check wall collision (wrap around instead of dying)
#     if head_x < 0:

#         # Wrap to right side
#         player_data["body"][0][0] = GAME_WIDTH - SPACE_SIZE
#         collision_occurred = True
#         collision_type = "wall (left)"

#     elif head_x >= GAME_WIDTH:

#         # Wrap to left side
#         player_data["body"][0][0] = 0
#         collision_occurred = True
#         collision_type = "wall (right)"
    
#     if head_y < 0:

#         # Wrap to bottom
#         player_data["body"][0][1] = GAME_HEIGHT - SPACE_SIZE
#         collision_occurred = True
#         collision_type = "wall (top)"

#     elif head_y >= GAME_HEIGHT:

#         # Wrap to top
#         player_data["body"][0][1] = 0
#         collision_occurred = True
#         collision_type = "wall (bottom)"
    
#     # Check self collision (log it for debugging)
#     for segment in player_data["body"][1:]:
#         if head_x == segment[0] and head_y == segment[1]:
#             collision_occurred = True
#             collision_type = "self"
#             break
    
#     # Check collision with other snakes (log it for debugging)
#     for other_id, other_data in game_state["players"].items():
#         if other_id == player_id:
#             continue
        
#         for segment in other_data["body"]:
#             if head_x == segment[0] and head_y == segment[1]:
#                 collision_occurred = True
#                 collision_type = f"player {other_id}"
#                 break
    
#     # Log collision for debugging, but continue the game
#     if collision_occurred:
#         print(f"Player {player_id} collision with {collision_type} detected (snake survives - testing)")
    
#     # Always return False so the player doesn't die
#     return False


def check_collision(player_id, player_data):
    """
    Parameters: player number (player_id), dictionary of a player that contains position coordinates direction (player_data)

    Function that implements the collision logic for the snakes.
    Upon wall collision, snake dies
    Upon self collision, snake dies
    Upon collision with other snake's tail, snake dies
    Upon head-to-head collision, the longer snake survives and a tied length means both die
    
    Returns: Boolean of whether or not the snake should die, list of other snakes that should die from this collision
    """

    # Variables
    head_x, head_y = player_data["body"][0]
    additional_deaths = []
    
    # Check wall collision
    if (head_x < 0 or head_x >= GAME_WIDTH or 
        head_y < 0 or head_y >= GAME_HEIGHT):
        print(f"Player {player_id} died by hitting a wall")
        return True, additional_deaths
    
    # Check self collision 
    for segment in player_data["body"][1:]:
        if head_x == segment[0] and head_y == segment[1]:
            print(f"Player {player_id} died by hitting own tail")
            return True, additional_deaths
    
    # Check collision with other snakes
    for other_id, other_data in game_state["players"].items():
        if other_id == player_id:
            continue
        
        other_head = other_data["body"][0]
        
        # Head-to-head collision
        if head_x == other_head[0] and head_y == other_head[1]:

            # Compare snake lengths to determine winner
            my_length = len(player_data["body"])
            other_length = len(other_data["body"])
                
            # This snake wins            
            if my_length > other_length:
                print(f"Head collision: Player {player_id} wins against Player {other_id} ({my_length} vs {other_length})")
                additional_deaths.append(other_id)
                return False, additional_deaths

            # Other snake wins
            elif other_length > my_length:
                print(f"Head collision: Player {player_id} loses to Player {other_id} ({my_length} vs {other_length})")
                return True, additional_deaths
            
            # Tie - both snakes lose            
            else:
                print(f"Head collision: Players {player_id} and {other_id} tie and both die ({my_length} segments)")
                additional_deaths.append(other_id)
                return True, additional_deaths
        
        # Collision with other snake's body (except the head)
        for segment in other_data["body"][1:]:
            if head_x == segment[0] and head_y == segment[1]:
                print(f"Player {player_id} died by hitting Player {other_id}'s tail")
                return True, additional_deaths
    
    # No collisions detected
    return False, additional_deaths


def generate_new_food():
    """
    Parameters: NULL (Nothing)

    Function for finding the new coordinates for the food to generate. 
    Position cannot be where a snake currently resides on.

    Returns: Pair of coordinates that represents the new spawnpoint for food 
    """

    # Variable
    occupied_positions = []
    
    # Collect all snake positions
    for player_data in game_state["players"].values():
        occupied_positions.extend(player_data["body"])
    
    # Generate positions until we find one that doesn't overlap
    while True:
        food_x = random.randint(0, (GAME_WIDTH-SPACE_SIZE) // SPACE_SIZE) * SPACE_SIZE
        food_y = random.randint(0, (GAME_HEIGHT-SPACE_SIZE) // SPACE_SIZE) * SPACE_SIZE
        
        # If found, return the coordinates
        if [food_x, food_y] not in occupied_positions:
            return [food_x, food_y]


def game_loop():
    """
    Parameters: NULL (Nothing)

    Function for running the main game itself.
    Enforces logic and ensures the game is ran to completion.

    Returns: NULL (Nothing)
    """

    # Global server game state and time
    global game_state
    clock = pygame.time.Clock() if 'pygame' in globals() else None
    
    # Countdown variables
    countdown_started = False
    last_countdown_time = 0
    
    # Main loop of the game
    while True:

        # Variables to be updated
        food_eaten = False
        players_to_remove = []
        
        with game_state_lock:

            # Check if all players have connected
            if len(game_state["players"]) == max_players and not game_state["game_started"] and not countdown_started:
                print("All players connected. Starting countdown...")
                game_state["countdown"] = True
                countdown_started = True
                last_countdown_time = time.time()
                game_state["countdown_value"] = 3
                
                # Broadcast countdown start
                try:
                    broadcast_data = pickle.dumps(game_state)
                    for client in clients.values():
                        client.send(broadcast_data)
                        
                # Exception for error in broadcasting to clients        
                except Exception as e:
                    print(f"Error broadcasting countdown: {e}")
            
            # Handle countdown
            if countdown_started and not game_state["game_started"]:
                current_time = time.time()

                # Increment countdown
                if current_time - last_countdown_time >= 1:
                    game_state["countdown_value"] -= 1
                    last_countdown_time = current_time
                    print(f"Countdown: {game_state['countdown_value']}")
                    
                    # Broadcast updated countdown
                    try:
                        broadcast_data = pickle.dumps(game_state)
                        for client in clients.values():
                            client.send(broadcast_data)

                    # Exception for error in broadcasting to clients
                    except Exception as e:
                        print(f"Error broadcasting countdown update: {e}")
                    
                    # Start the game when countdown reaches 0
                    if game_state["countdown_value"] <= 0:
                        game_state["countdown"] = False
                        game_state["game_started"] = True
                        print("Game started!")
                        
                        # Broadcast game start
                        try:
                            broadcast_data = pickle.dumps(game_state)
                            for client in clients.values():
                                client.send(broadcast_data)

                        # Exception for error in broadcasting for clients
                        except Exception as e:
                            print(f"Error broadcasting game start: {e}")
                
                # Skip the rest of the game logic until countdown finishes
                if not game_state["game_started"]:
                    time.sleep(0.1)  # Prevent CPU usage hogging
                    continue
            
            # Only proceed if the game has started and there are at least 2 players
            active_players = len(game_state["players"])
            if not game_state["game_started"] or active_players < 2:
                time.sleep(0.1)  # Prevent CPU usage hogging
                continue
            
            # Process each player
            for player_id, player_data in list(game_state["players"].items()):

                # Skip already removed players
                if player_id in players_to_remove:
                    continue
                    
                # Move snake
                if move_snake(player_id, player_data):
                    food_eaten = True
                
                # Check collisions 
                should_die, others_to_kill = check_collision(player_id, player_data)
                
                # If a snake has crashed or should be removed
                if should_die:
                    players_to_remove.append(player_id)
                
                # Add any other players that should die from this collision
                for other_id in others_to_kill:
                    if other_id not in players_to_remove:
                        players_to_remove.append(other_id)
            
            # Generate new food if needed
            if food_eaten:
                game_state["food"] = generate_new_food()
            
            # Remove dead players
            for player_id in players_to_remove:
                if player_id in game_state["players"]:
                    print(f"Player {player_id} removed from game")
                    del game_state["players"][player_id]
            
            # Check game over condition
            remaining_players = len(game_state["players"])
            
            # Game ends when 0 or 1 player remains
            if remaining_players <= 1 and active_players > 1:
                game_state["game_over"] = True

                # Last player standing wins
                if remaining_players == 1:
                    game_state["winner"] = list(game_state["players"].keys())[0]
                    print(f"Game over! Player {game_state['winner']} wins!")

                # Everyone has died - it's a tie
                else:
                    game_state["tie"] = True
                    print("Game over! All players died - it's a tie!")
            
            # Broadcast updated game state to all clients
            try:
                broadcast_data = pickle.dumps(game_state)
                for client in clients.values():
                    client.send(broadcast_data)

            # Exception in the case of failed broadcasting
            except Exception as e:
                print(f"Error broadcasting: {e}")
        
        # Control game speed
        if clock:
            clock.tick(SPEED)
        else:
            time.sleep(1/SPEED)

# Start server and wait for players
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(max_players)

print(f"Server started. Waiting for {max_players} players...")
player_count = 0

# Start game loop in a separate thread
game_thread = threading.Thread(target=game_loop, daemon=True)
game_thread.start()

# Accept player connections
while player_count < max_players:
    try:
        conn, addr = server.accept()
        print(f"Player {player_count + 1} connected from {addr}")
        
        clients[player_count] = conn
        
        thread = threading.Thread(target=handle_client, args=(conn, addr, player_count))
        thread.start()
        
        player_count += 1
        
        print(f"{player_count}/{max_players} players connected")
    
    # Exception in the case of failed connection
    except Exception as e:
        print(f"Error accepting connection: {e}")

print("All players connected. Game will start after the countdown.")

# Keep the server running
try:
    while True:
        time.sleep(1)

# Exception in the case of user-inputted server shutdown
except KeyboardInterrupt:
    print("Server shutting down...")
    server.close()
