import serial
import serial.tools.list_ports
import time
import numpy as np
import os
import chess
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
BLACK = (0, 0, 0)
board_dim = (8, 8)


ports = serial.tools.list_ports.comports()
for port in ports:
	if port.vid is not None or "Arduino" in str(port.description):
		print(f"arduino on: {port.device}, {port.description}")
		print(port.device)

SERIAL_PORT = port.device
baud = 9600

base = np.full(board_dim, -1, dtype=float)
OCC_OFF = 10
DIF_OFF = 100

arduino = serial.Serial(port = SERIAL_PORT, baudrate = baud, timeout = 1)
time.sleep(2)

board_arr = np.full(board_dim, "-", dtype = '<U1')
board_data_pres = np.zeros(board_dim, dtype=float)

board = chess.Board(None)
ref_board = chess.Board()
#ref_board.clear()
#ref_board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))


class Button:
	def __init__(self, x, y, w, h, text, base, hover):
		self.rect = pygame.Rect(x, y, w, h)
		self.text = text
		self.baseColor = base
		self.hoverColor = hover
		self.font = pygame.font.SysFont("Arial", 18)
		self.isHover = False

	def draw(self, surf):
		color = hoverColor if isHover else baseColor
		pygame.draw.rect(surf, color, self.rect)

		textSurf = self.font.render(self.text, True, BLACK)
		textRect = textSurf.get_rect(center=self.rect.center)
		screen.blit(textSurf, textRect)

	def checkHover(self, mousePos):
		self.isHover = self.rect.collidepoint(mousePos)

	def isClicked(self, event, mousePos):
		if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			if self.rect.collidepoint(mousePos):
				return True
			return False


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
	fromSq = indexToMove1(pos1)
	toSq = indexToMove1(pos2)
	return chess.Move(toSq, fromSq)

def indexToMove1(pos1):
	r,c = pos1
	rank = 7-r
	file = c
	return chess.square(file, rank)

def calibrate(sample_time=5.0):
	sums = np.zeros(board_dim, dtype=float)
	count = np.zeros(board_dim, dtype=float)
	
	start_time = time.time()

	while time.time() - start_time < sample_time:
		if arduino.in_waiting > 0:

			data = arduino.readline().decode('utf-8').strip().split()
			try:
				raw_data = [float(x) for x in data]
			except ValueError:
				print("caught midline, restarting")
				continue

			flat_sum = sums.flat
			flat_count = count.flat
			
			for i in range(len(raw_data)):
				if (raw_data[i] > 300): # filter out nonsense values
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
					new_piece = chess.Piece(piece.piece_type, chess.BLACK)
					board.set_piece_at(sq, new_piece)
					#print(indexToMove1((r, c)))

				if (board_data_pres[r,c] < baseVal - OCC_OFF):
					new_piece = chess.Piece(piece.piece_type, chess.WHITE)
					board.set_piece_at(sq, new_piece)
					#print(indexToMove1((r, c)))


time.sleep(2)
print("calibrating")
calibrate(15)
print("calibration done")

board_data_pres = np.copy(base)
board_data_past = np.copy(board_data_pres)


while True:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			sys.exit()

	boardWithSensors()
	drawBoard()
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

	diff = board_data_pres - board_data_past
	board_diff = board_data_pres - board_data_past
	removed = [(r,c) for r,row in enumerate(board_diff) for c,val in enumerate(row) if val < -200]

	if removed:
		squareRemoved = removed[0]
		print(squareRemoved)
		print(indexToMove1(squareRemoved))

		placed = [(r,c) for r,row in enumerate(board_diff) for c,val in enumerate(row) if val > 200]
		if placed:
			squarePlaced = placed[0]
			print(indexToMove1(squarePlaced))	

			move = indexToMove2(squareRemoved, squarePlaced)
			board.push(move)

	print(board_data_pres.reshape(board_dim))
	board_data_past = np.copy(board_data_pres)
	print("detected + " str(move))
	os.system('clear')
