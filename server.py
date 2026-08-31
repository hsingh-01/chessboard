import chess
import chess.svg
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

state = {
    "fen": chess.STARTING_FEN,
    "data": [[0.0] * 8 for _ in range(8)],
}

def generate_board_svg(board: chess.Board, data_matrix) -> str:
    margin = 15
    sq_size = 45
    svg_raw = chess.svg.board(board=board, size=500)

    text_elements = []
    for r in range(8):
        for c in range(8):
            val = data_matrix[r][c]
            x = margin + (c + 0.5) * sq_size
            y = margin + ((7 - r) + 0.5) * sq_size + 5 
            text_elements.append(
                f'<text x="{x}" y="{y}" font-size="14" font-weight="bold" fill="red" text-anchor="middle">{val:.0f}</text>'
            )

    svg_with_text = svg_raw.replace("</svg>", "".join(text_elements) + "</svg>")
    return f"""
    <html>
        <head><meta http-equiv="refresh" content="1"></head>
        <body style="margin:0; background:#1e1e1e; display:flex; justify-content:center; align-items:center; height:100vh;">
            {svg_with_text}
        </body>
    </html>
    """

@app.route("/update", methods=["POST"])
def update_state():
    req_data = request.get_json(silent=True) or {}
    if "fen" in req_data:
        state["fen"] = req_data["fen"]
    if "data" in req_data:
        state["data"] = req_data["data"]
    return jsonify({"status": "ok"})

@app.route("/")
def render_board():
    try:
        board = chess.Board(state["fen"])
    except ValueError:
        return "Invalid FEN string provided", 400
    html_content = generate_board_svg(board, state["data"])
    return Response(html_content, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)