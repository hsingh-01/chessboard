import serial
import time
import numpy as np
import os
import chess
import keyboard
import sys
import pygame

pygame.init()
CHESS_FONT = pygame.font.SysFont("Arial", 48)


SERIAL_PORT = '/dev/cu.usbmodem11201'
baud = 9600

tolerance = 15
BASE = 520
LOW_BASE = BASE - tolerance
HIGH_BASE = BASE + tolerance

LOW_OCC = 250
HIGH_OCC = 790

arduino = serial.Serial(port = SERIAL_PORT, baudrate = baud, timeout = 1)
board_dim = (8, 8)
time.sleep(1)
print("im in")
time.sleep(2)


board_arr = np.full(board_dim, "-", dtype = '<U1')

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
SQUARE_SIZE = SCREEN_HEIGHT / 8
WINDOW = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))


LIGHT = (240, 217, 181)
DARK = (181, 136, 99)

board = chess.Board(None)


def drawBoard():
	for r in range(8):
		for c in range(8):
			square = chess.square(c, 7-r)
			if ((r+c) % 2 == 0):
				color = LIGHT
			else:
				color = DARK

			piece = board.piece_at(square)
			pygame.draw.rect(WINDOW, color, pygame.Rect(c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

			if (piece != None):
				if (piece.color == chess.BLACK):
					text = CHESS_FONT.render(piece.symbol(), True, (0, 0, 0))
				if (piece.color == chess.WHITE):
					text = CHESS_FONT.render(piece.symbol(), True, (255, 255, 255))

				text_rect = text.get_rect(center=(c * SQUARE_SIZE + SQUARE_SIZE//2, r * SQUARE_SIZE + SQUARE_SIZE//2))
				WINDOW.blit(text, text_rect)
	pygame.display.flip()		

ref_board = chess.Board()

pieces = [
["BR", "BN", "BB", "BQ", "BK", "BB", "BN", "BR"],
["BP", "BP", "BP", "BP", "BP", "BP", "BP", "BP"],
["", "", "", "", "", "", "", ""],
["", "", "", "", "", "", "", ""],
["", "", "", "", "", "", "", ""],
["", "", "", "", "", "", "", ""],
["WP", "WP", "WP", "WP", "WP", "WP", "WP", "WP"],
["WR", "WN", "WB", "WQ", "WK", "WB", "WN", "WR"]
]

def indexToMove2(pos1, pos2):
	# convert array index (like (6,6) --> (5,5)) to UCI notation (g7f6)
	row1 = pos1[0]
	row1 = 8 - row1

	col1 = pos1[1]
	col1 += 1
	col1 = chr(col1 + 96)


	row2 = pos2[0]
	row2 = 8 - row2

	col2 = pos2[1]
	col2 += 1
	col2 = chr(col2 + 96)

	#print(str(col1) + str(row1) + str(col2) + str(row2))
	return chess.parse_square(str(col1) + str(row1) + str(col2) + str(row2))

def indexToMove1(pos1):
	row1 = pos1[0]
	row1 = 8 - row1

	col1 = pos1[1]
	col1 += 1
	col1 = chr(col1 + 96)

	#print(str(col1) + str(row1))
	return chess.parse_square(str(col1) + str(row1))




def calibrate():
	pass

def movePiece(arr, start, end):
	arr[end[0]][end[1]] = arr[start[0]][start[1]]
	pieces[end[0]][end[1]] = pieces[start[0]][start[1]]

	arr[start[0]][start[1]] = BASE
	pieces[start[0]][start[1]] = ""

def boardWithSensors():
	board.clear()
	for r in range(8):
		for c in range(8):
			sq = indexToMove1((r,c))
			piece = ref_board.piece_at(sq)

			if piece is not None:
				if (board_data_pres[r,c] > HIGH_BASE):
					new_piece = chess.Piece(piece.piece_type, chess.WHITE)
					board.set_piece_at(sq, new_piece)
					#print(indexToMove1((r, c)))

				if (board_data_pres[r,c] < LOW_BASE):
					new_piece = chess.Piece(piece.piece_type, chess.BLACK)
					board.set_piece_at(sq, new_piece)
					#print(indexToMove1((r, c)))

step = 0
board_data_pres = np.full(board_dim, BASE, dtype=float)

board_data_past = np.copy(board_data_pres)

lifted = None
placed = None

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()

    boardWithSensors()

    if keyboard.is_pressed("="):
        sys.exit()

    if arduino.in_waiting > 0:
        data = arduino.readline().decode('utf-8', errors='ignore').strip().split()
        
        try:
            raw_data = [float(i) for i in data]
            
            if len(raw_data) == 16:
                flat_pres = board_data_pres.flat
                for i in range(16):
                    if raw_data[i] != -1.0:
                        flat_pres[i] = raw_data[i]

        except ValueError:
            pass 

    drawBoard()

    diff = board_data_pres - board_data_past
    if np.sum(np.abs(diff)) > 10:        
        os.system('clear')
        print(board_data_pres.reshape(board_dim))
        board_data_past = np.copy(board_data_pres)

    time.sleep(0.02) 


# -1 (no sensor) --> -
# (510, 530) (sensor, empty) --> " "
# (0, 510) (sensor, black) --> B
# (530, 1024) (sensor, white) --> W