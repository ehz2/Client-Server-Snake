import socket
import threading
import pickle
import random

# Server Constants
HOST = '0.0.0.0'
PORT = 5555
clients = {}
max_players = int(input("Enter number of players (2-4): "))  # User sets max players

# Unique starting positions for each player
starting_positions = [
    (50, 50), (600, 50), (50, 600), (600, 600)
]

# Game state
game_state = {
    "players": {},
    "food": (random.randint(0, 13) * 50, random.randint(0, 13) * 50)  # Random food position
}

def handle_client(conn, addr, player_id):
    global game_state
    try:
        # Send initial player info and game state
        initial_data = {
            "player_id": player_id,
            "game_state": game_state
        }
        conn.send(pickle.dumps(initial_data))
        #print(f"Sent initial data to player {player_id}: {initial_data}")

        while True:
            try:
                data = pickle.loads(conn.recv(2048))  # Increased buffer size
                #print(f"Received data from player {player_id}: {data}")
                
                # Update player position in game state
                game_state["players"][player_id] = data

                # Broadcast updated game state to all clients
                for client in clients.values():
                    client.send(pickle.dumps(game_state))
                
                #print(f"Broadcasted game state: {game_state}")
            except Exception as e:
                print(f"Error processing client {player_id} data: {e}")
                break
    except Exception as e:
        print(f"Initial connection error with player {player_id}: {e}")
    finally:
        # Cleanup
        if player_id in game_state["players"]:
            del game_state["players"][player_id]
        if player_id in clients:
            del clients[player_id]
        conn.close()

# Start Server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(max_players)

print(f"Waiting for {max_players} players...")
player_count = 0


def update_and_broadcast_game_state():
    # Send the updated game state to all clients
    
    print("INSIDE THE UPDATE")
    print(game_state)
    #print(f"Connected clients: {clients}")
    for client in clients.values():
        client.send(pickle.dumps(game_state)) 

while player_count < max_players:
    conn, addr = server.accept()
    player_id = player_count
    clients[player_id] = conn
    
    # Initialize player in game state
    game_state["players"][player_id] = {
        "pos": starting_positions[player_id], 
        "direction": "RIGHT"
    }

    update_and_broadcast_game_state()

    thread = threading.Thread(target=handle_client, args=(conn, addr, player_id))
    thread.start()
    
    player_count += 1
    


print("All players connected. Game starting...")
