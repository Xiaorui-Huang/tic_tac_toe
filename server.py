import socket
import sys
import threading
from queue import Queue

# Server setup
SERVER = "127.0.0.1"
PORT = 5555
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((SERVER, PORT))
server.listen()

# Player and Spectator Queues
player_queue = Queue()
spectators = []

# Game state
board = [' '] * 9
current_player = None
players = []
MAX_PLAYERS = 2

def reset_board():
    global board
    board = [' '] * 9
def broadcast(message, sender=None):
    message = message + "\n"
    for conn in spectators + players:
        if conn != sender:
            try:
                conn.send(message.encode('utf-8'))
            except:
                remove_connection(conn)

def handle_player(conn, addr):
    global current_player
    print(f"[NEW CONNECTION] {addr} connected.")
    
    if len(players) < MAX_PLAYERS:
        players.append(conn)
        conn.send("Welcome to Tic Tac Toe! You are a player.".encode('utf-8'))
    else:
        spectators.append(conn)
        conn.send("Welcome to Tic Tac Toe! You are a spectator for now.".encode('utf-8'))
    
    broadcast(f"{addr} has joined the game.", sender=conn)
    
    if current_player is None and len(players) == MAX_PLAYERS:
        next_player()  # Start the game when we have two players

    while True:
        try:
            message = conn.recv(1024).decode('utf-8')
            if not message:
                break 
            if conn == current_player:
                # Process Tic Tac Toe move
                process_move(conn, message)
            else:
                # Process chat message
                broadcast(f"{addr}: {message}", sender=conn)

        except:
            break

    remove_connection(conn)
    
def game_over(winner):
    symbol = 'X' if winner == players[0] else 'O'
    message = f"""
    **Game Over!**

    Player {symbol} has won!

    ----------------------------------
    """
    broadcast(message)

def process_move(conn, message):
    global board, current_player

    try:
        move = int(message) - 1 
        if 0 <= move < 9 and board[move] == ' ':
            symbol = 'X' if current_player == players[0] else 'O'
            board[move] = symbol
            broadcast_board()

            if check_win():
                conn.send("You won!\n".encode('utf-8'))
                other_player = players[1] if current_player == players[0] else players[0]
                other_player.send("You lost!\n".encode('utf-8'))
                game_over(current_player)
                reset_game()
            elif ' ' not in board:
                broadcast("Game Over: It's a draw!")
                reset_game()
            else:
                next_player()
        else:
            conn.send("Invalid move, try again.".encode('utf-8'))
    except ValueError:
        conn.send("Invalid input, please enter a number between 1-9.".encode('utf-8'))
        

def broadcast_board():
    # ANSI color codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BLUE = "\033[34m"
    RED = "\033[31m"
    
    # Unicode box-drawing characters
    TOP_LEFT = "╔"
    TOP_RIGHT = "╗"
    BOTTOM_LEFT = "╚"
    BOTTOM_RIGHT = "╝"
    HORIZONTAL = "═"
    VERTICAL = "║"
    CROSS = "╬"
    T_DOWN = "╦"
    T_UP = "╩"
    T_RIGHT = "╠"
    T_LEFT = "╣"

    def color_symbol(symbol):
        if symbol == 'X':
            return f"{BOLD}{BLUE}X{RESET}"
        elif symbol == 'O':
            return f"{BOLD}{RED}O{RESET}"
        else:
            return " "

    board_state = f"""
{TOP_LEFT}{HORIZONTAL*3}{T_DOWN}{HORIZONTAL*3}{T_DOWN}{HORIZONTAL*3}{TOP_RIGHT}
{VERTICAL} {color_symbol(board[0])} {VERTICAL} {color_symbol(board[1])} {VERTICAL} {color_symbol(board[2])} {VERTICAL}
{T_RIGHT}{HORIZONTAL*3}{CROSS}{HORIZONTAL*3}{CROSS}{HORIZONTAL*3}{T_LEFT}
{VERTICAL} {color_symbol(board[3])} {VERTICAL} {color_symbol(board[4])} {VERTICAL} {color_symbol(board[5])} {VERTICAL}
{T_RIGHT}{HORIZONTAL*3}{CROSS}{HORIZONTAL*3}{CROSS}{HORIZONTAL*3}{T_LEFT}
{VERTICAL} {color_symbol(board[6])} {VERTICAL} {color_symbol(board[7])} {VERTICAL} {color_symbol(board[8])} {VERTICAL}
{BOTTOM_LEFT}{HORIZONTAL*3}{T_UP}{HORIZONTAL*3}{T_UP}{HORIZONTAL*3}{BOTTOM_RIGHT}
    """
    
    broadcast(board_state)

def check_win():
    win_conditions = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columns
        (0, 4, 8), (2, 4, 6)              # Diagonals
    ]
    for condition in win_conditions:
        if board[condition[0]] == board[condition[1]] == board[condition[2]] != ' ':
            return True 
    return False

def reset_game():
    global board, current_player
    reset_board()
    current_player = None
    next_player()

def remove_connection(conn):
    global players, spectators, current_player
    if conn in players:
        players.remove(conn)
        if spectators:
            new_player = spectators.pop(0)
            players.append(new_player)
            new_player.send("You've been promoted to a player.".encode('utf-8'))
    elif conn in spectators:
        spectators.remove(conn)
    
    conn.close()
    
    if conn == current_player or len(players) < MAX_PLAYERS:
        next_player()

def next_player():
    global current_player
    if len(players) == MAX_PLAYERS:
        # Alternate between the two players
        current_player = players[1] if current_player == players[0] else players[0]
        current_player.send("It's your turn!".encode('utf-8'))
    elif len(players) < MAX_PLAYERS and spectators:
        # If we don't have enough players, promote a spectator
        new_player = spectators.pop(0)
        players.append(new_player)
        current_player = new_player
        current_player.send("You've been promoted to a player. It's your turn!".encode('utf-8'))
    else:
        current_player = None
        broadcast("Waiting for players to join...")
        
        
def start():
    print("[STARTING] Server has started...")
    server.settimeout(1)  # Set a timeout so accept() doesn't block indefinitely
    
    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_player, args=(conn, addr))
                thread.start()
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
            except socket.timeout:
                continue  # No connection received, continue the loop
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
    except KeyboardInterrupt:
        print("\n[SHUTTING DOWN] Server is shutting down...")
    finally:
        print("[CLEANUP] Closing all connections...")
        for conn in spectators + players:
            try:
                conn.close()
            except:
                pass  # Ignore errors while closing connections
        server.close()
        print("[FINISHED] Server has been shut down.")
        sys.exit(0)

if __name__ == "__main__":
    start()
