# Chessboard
This contains software compatible with an Arduino UNO R3 linked to 64 analog Hall Effect sensors wired to the Arduino via four multiplexers. Each sensor sits under its own unique square on a standard 8x8 chessboard, on top of which pieces with embedded magnets with polarities corresponding to their side (white/black) are played. 

```chessboard.ino``` is responsible for reading and formatting the raw data directly from the Arduino into a format readable by ```chessboard.py```, which reads the data from the Arduino's serial port. From there, the data is sent to a loopback server ran by ```server.py``` to display the board, evaluation, and move list. 

Features TBA:
- user overrides for misread pieces (take back, redo, force)
- castling detection
- graphically displayed recommended top engine moves
- opening information from the chess ECO
- exporting games as .gifs or PGN; importing/exporting game states as FEN
