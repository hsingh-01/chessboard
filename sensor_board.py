import serial
import serial.tools.list_ports
import time
import numpy as np
import chess
import chess.engine
import sys
import requests
import threading

board_dim = (8, 8)

ports = serial.tools.list_ports.comports()
SERIAL_PORT = None
for port in ports:
    if port.vid is not None or "Arduino" in str(port.description):
        SERIAL_PORT = port.device
        break

if not SERIAL_PORT:
    print("you forgot to plug it in")
    sys.exit(1)

baud = 115200
arduino = serial.Serial(port=SERIAL_PORT, baudrate=baud, timeout=1)
time.sleep(2)

base = np.full(board_dim, -1, dtype=float)
OCC_OFF = 20

board_data_pres = np.zeros(board_dim, dtype=float)

game_started = False
turn = None

engine = chess.engine.SimpleEngine.popen_uci("/usr/local/bin/stockfish")

if (len(sys.argv) > 1):
    fen_input = sys.argv[1]
else:
    fen_input = chess.STARTING_FEN

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
posEval = "0.0"
isEval = False

def evaluateFen(fen):
    global posEval, isEval
    board = chess.Board(fen)

    limit = chess.engine.Limit(time = 0.8)
    info = engine.analyse(board, limit)

    score = info['score'].white()
    if score.is_mate():
        posEval = "M" + str(score.mate())
    else:
        cp = score.score(mate_score = 1000)
        posEval = f"{cp / 100.0:+.2f}"
    isEval = False
    print(posEval)

def asyncEval(fen):
    global isEval
    if not isEval:
        isEval = True
        threading.Thread(target=evaluateFen, args=(fen,), daemon=True).start()

def adjustTurn(turn, board):
    turn = "white" if board.turn == chess.WHITE else "black"
    return turn;

def sensorMapToBoard(matrix):
    return np.flipud(matrix)

def indexToMove1(pos1):
    r, c = pos1
    rank = r
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
    base = sensorMapToBoard(avg_matrix)

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
print(base)

board_data_pres = np.copy(base)

input("put pieces down (enter when done)")
game_started = True
print("tracking\n")
moves = []
moves_san = []
turn = adjustTurn(turn, board)

previous_diff = None
pending_from = None
pending_since = None

PENDING_TIMEOUT = 5
CHANGE_THRESHOLD = 15
SIGNAL_THRESHOLD = 15

while True:
    if arduino.in_waiting > 0:
        data = arduino.readline().decode("utf-8").strip().split()
        try:
            raw_data = [float(i) for i in data]
            if len(raw_data) == 64:
                incoming_matrix = np.array(raw_data).reshape(8, 8)
                board_data_pres = sensorMapToBoard(incoming_matrix)

                current_diff = board_data_pres - base

                if previous_diff is None:
                    previous_diff = current_diff.copy()
                else:
                    moving_color = chess.WHITE if board.turn == chess.WHITE else chess.BLACK
                    lifted_candidates = []
                    placed_candidates = []
                    capture_candidates = []

                    for r in range(8):
                        for c in range(8):
                            if base[r, c] == -1:
                                continue

                            sq = indexToMove1((r, c))
                            piece = board.piece_at(sq)
                            diff = current_diff[r, c]
                            change = current_diff[r, c] - previous_diff[r, c]

                            if piece is not None and piece.color == moving_color:
                                if moving_color == chess.WHITE:
                                    if change > CHANGE_THRESHOLD:
                                        lifted_candidates.append((abs(change), (r, c)))
                                else:
                                    if change < -CHANGE_THRESHOLD:
                                        lifted_candidates.append((abs(change), (r, c)))


                            if piece is None:
                                if moving_color == chess.WHITE:
                                    if diff < -SIGNAL_THRESHOLD and change < -CHANGE_THRESHOLD:
                                        placed_candidates.append((abs(change), (r, c)))
                                else:
                                    if diff > SIGNAL_THRESHOLD and change > CHANGE_THRESHOLD:
                                        placed_candidates.append((abs(change), (r, c)))


                            elif piece.color != moving_color:
                                if moving_color == chess.WHITE:
                                    if diff < -SIGNAL_THRESHOLD and change < -CHANGE_THRESHOLD:
                                        capture_candidates.append((abs(change), (r, c)))
                                else:
                                    if diff > SIGNAL_THRESHOLD and change > CHANGE_THRESHOLD:
                                        capture_candidates.append((abs(change), (r, c)))

                    destination_candidates = []
                    destination_candidates.extend((score, pos, False) for score, pos in placed_candidates)
                    destination_candidates.extend((score, pos, True) for score, pos in capture_candidates)
                    destination_candidates.sort(reverse=True)

                    legal_pairs = []
                    for from_score, from_pos in lifted_candidates:
                        for to_score, to_pos, is_capture_candidate in destination_candidates:
                            move_candidate = indexToMove2(from_pos, to_pos)
                            if move_candidate in board.legal_moves:
                                legal_pairs.append(
                                    (from_score + to_score, move_candidate, is_capture_candidate)
                                )

                    move = None
                    is_capture = False

                    if legal_pairs:
                        legal_pairs.sort(key=lambda x: x[0], reverse=True)
                        _, move, is_capture = legal_pairs[0]
                    else:
                        if lifted_candidates:
                            lifted_candidates.sort(reverse=True)
                            pending_from = lifted_candidates[0][1]
                            pending_since = time.time()
                            print(
                                f"source candidate: {chess.square_name(indexToMove1(pending_from))} "
                                f"change={lifted_candidates[0][0]:.0f}"
                            )

                        if pending_from is not None and destination_candidates:
                            pending_legal = []
                            for score, to_pos, is_capture_candidate in destination_candidates:
                                move_candidate = indexToMove2(pending_from, to_pos)
                                if move_candidate in board.legal_moves:
                                    pending_legal.append(
                                        (score, move_candidate, is_capture_candidate)
                                    )

                            if pending_legal:
                                pending_legal.sort(key=lambda x: x[0], reverse=True)
                                _, move, is_capture = pending_legal[0]

                        if move is None and pending_from is not None and pending_since is not None:
                            if time.time() - pending_since > PENDING_TIMEOUT:
                                print(
                                    f"source candidate timed out: "
                                    f"{chess.square_name(indexToMove1(pending_from))}"
                                )
                                pending_from = None
                                pending_since = None

                    if move is not None:
                        move_san = board.san(move)
                        moves.append(move_san)
                        moves_san.append(move_san)
                        board.push(move)
                        asyncEval(board.fen())
                        turn = adjustTurn(turn, board)
                        tag = " (capture)" if is_capture else ""
                        print(f"move(legal){tag}: {move_san}")
                        pending_from = None
                        pending_since = None


                    previous_diff = current_diff.copy()

        except ValueError:
            print("----------------------------")
            pass

    try:
        requests.post(
            "http://127.0.0.1:5050/update",
            json={"fen": board.fen(), "data": board_data_pres.tolist(), "moves": moves_san, "turn": turn, "eval": posEval},
            timeout=0.2,
        )
    except Exception:
        pass

    time.sleep(0.05)
engine.quit()
