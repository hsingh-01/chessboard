import serial
import serial.tools.list_ports
import time
import numpy as np
import os
import chess
import keyboard
import sys
import pygame

pygame.init()
CHESS_FONT = pygame.font.SysFont("Arial", 48)
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
SQUARE_SIZE = SCREEN_HEIGHT / 8
WINDOW = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
board_dim = (8, 8)


ports = serial.tools.list_ports.comports()
for port in ports:
	if port.vid is not None or "Arduino" in str(port.description):
		print(f"arduino on: {port.device}, {port.description}")
		print(port.device)
SERIAL_PORT = port.device
baud = 9600

base = np.full(board_dim, -1, dtype=float)
OCC_OFF = 15

arduino = serial.Serial(port = SERIAL_PORT, baudrate = baud, timeout = 1)
time.sleep(2)

board_arr = np.full(board_dim, "-", dtype = '<U1')
board_data_pres = np.zeros(board_dim, dtype=float)

board = chess.Board(None)
ref_board = chess.Board()

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

def calibrate(sample_time=5.0):
	sums = np.zeros(board_dim, dtype=float)
	count = np.zeros(board_dim, dtype=float)
	
	start_time = time.time()

	while time.time() - start_time < sample_time:
		if arduino.in_waiting > 0:

			data = arduino.readline().decode('utf-8').strip().split()
			raw_data = [float(x) for x in data]
			flat_sum = sums.flat
			flat_count = count.flat
			
			for i in range(len(raw_data)):
				if (raw_data[i] > 100): # filter out nonsense values
					flat_sum[i] += raw_data[i]
					flat_count[i] += 1
		time.sleep(0.008)

	flat_base = base.flat
	flat_sum = sums.flat
	flat_count = count.flat

	for i in range(len(flat_count)):
		if flat_count[i] > 0:
			flat_base[i] = flat_sum[i] / flat_count[i]
		else:
			flat_base[i] = -1.0

	active = np.sum(base != -1.0)
	print(f"{active} sensors detected") 

def boardWithSensors():
	board.clear()
	for r in range(8):
		for c in range(8):
			sq = indexToMove1((r,c))
			piece = ref_board.piece_at(sq)
			baseVal = base[r, c]
			if baseVal == -1:
				continue

			if piece is not None:
				if (board_data_pres[r,c] > baseVal + OCC_OFF):
					new_piece = chess.Piece(piece.piece_type, chess.WHITE)
					board.set_piece_at(sq, new_piece)
					#print(indexToMove1((r, c)))

				if (board_data_pres[r,c] < baseVal - OCC_OFF):
					new_piece = chess.Piece(piece.piece_type, chess.BLACK)
					board.set_piece_at(sq, new_piece)
					#print(indexToMove1((r, c)))

time.sleep(2)
print("calibrating")
calibrate(8)
print("calibration done")

board_data_pres = np.copy(base)
board_data_past = np.copy(board_data_pres)

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
			flat_pres = board_data_pres.flat
			for i in range(len(raw_data)):
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

	time.sleep(0.01) 