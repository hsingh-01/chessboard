import serial
import serial.tools.list_ports
import time
import numpy as np
import chess
import sys
import requests

board_dim = (8, 8)

ports = serial.tools.list_ports.comports()
SERIAL_PORT = None
for port in ports:
    if port.vid is not None or "Arduino" in str(port.description):
        SERIAL_PORT = port.device
        break

if not SERIAL_PORT:
    print("No Arduino detected!")
    sys.exit(1)

baud = 115200
arduino = serial.Serial(port=SERIAL_PORT, baudrate=baud, timeout=1)
time.sleep(2)

base = np.full(board_dim, -1, dtype=float)
OCC_OFF = 15.0  

board_data_pres = np.zeros(board_dim, dtype=float)

game_started = False

# FEN Setup
fen_input = sys.argv[1] if len(sys.argv) > 1 else chess.STARTING_FEN
if len(fen_input.split()) == 1:
    fen_input += " w - - 0 1"

try:
    ref_board = chess.Board(fen_input)
    print("ref:")
    print(ref_board)
except ValueError as e:
    print(f"invalid FEN: {e}")
    sys.exit(1)

board = chess.Board(fen_input)

def map_hardware_to_board(matrix):
    return np.flipud(matrix)

def indexToMove1(pos1):
    r, c = pos1
    rank = 7 - r
    file = c
    return chess.square(file, rank)

def indexToMove2(pos1, pos2):
    fromSq = indexToMove1(pos1)
    toSq = indexToMove1(pos2)
    return chess.Move(fromSq, toSq)

def calibrate(sample_time=5.0):
    sums = np.zeros((8, 8), dtype=float)
    count = np.zeros((8, 8), dtype=float)
    arduino.reset_input_buffer()
    start_time = time.time()

    while time.time() - start_time < sample_time:
        if arduino.in_waiting > 0:
            data = arduino.readline().decode("utf-8").strip().split()
            try:
                raw_data = [float(x) for x in data]
                if len(raw_data) == 64:
                    raw_matrix = np.array(raw_data).reshape(8, 8)
                    for r in range(8):
                        for c in range(8):
                            val = raw_matrix[r, c]
                            if val > 300:
                                sums[r, c] += val
                                count[r, c] += 1
            except ValueError:
                continue
        time.sleep(0.008)

    avg_matrix = np.full((8, 8), -1.0, dtype=float)
    for r in range(8):
        for c in range(8):
            if count[r, c] > 0:
                avg_matrix[r, c] = sums[r, c] / count[r, c]

    global base
    base = map_hardware_to_board(avg_matrix)

def boardWithSensors():
    board.clear()
    for r in range(8):
        for c in range(8):
            sq = indexToMove1((r, c))
            baseVal = base[r, c]
            if baseVal == -1:
                continue

            if board_data_pres[r, c] > baseVal + OCC_OFF:
                ref_piece = ref_board.piece_at(sq)
                if ref_piece is not None:
                    board.set_piece_at(sq, ref_piece)

print("calibrating")
calibrate(8)
print("done calibrating!\n")

board_data_pres = np.copy(base)

input("put pieces down (enter when done)")
game_started = True
print("tracking\n")

while True:
    if arduino.in_waiting > 0:
        data = arduino.readline().decode("utf-8", errors="ignore").strip().split()
        try:
            raw_data = [float(i) for i in data]
            if len(raw_data) == 64:
                incoming_matrix = np.array(raw_data).reshape(8, 8)
                board_data_pres = map_hardware_to_board(incoming_matrix)
        except ValueError:
            pass

    if not game_started:
        boardWithSensors()
    else:
        removed_sqs = []
        placed_sqs = []

        for r in range(8):
            for c in range(8):
                sq = indexToMove1((r, c))
                piece_on_board = board.piece_at(sq) is not None
                sensor_active = board_data_pres[r, c] > base[r, c] + OCC_OFF

                if piece_on_board and not sensor_active:
                    removed_sqs.append((r, c))
                elif not piece_on_board and sensor_active:
                    placed_sqs.append((r, c))

        if removed_sqs and placed_sqs:
            move = indexToMove2(removed_sqs[0], placed_sqs[0])

            if move in board.legal_moves:
                board.push(move)
                print(f"move(legal): {move}")
            else:
                from_sq = indexToMove1(removed_sqs[0])
                to_sq = indexToMove1(placed_sqs[0])
                piece = board.piece_at(from_sq)
                if piece:
                    board.remove_piece_at(from_sq)
                    board.set_piece_at(to_sq, piece)
                    print(f"move (force): {move}")

    try:
        requests.post(
            "http://127.0.0.1:5050/update",
            json={"fen": board.fen(), "data": board_data_pres.tolist()},
            timeout=0.2,
        )
    except Exception:
        pass

    time.sleep(0.05)