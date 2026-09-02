import chess
import chess.svg
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

state = {
    "fen": chess.STARTING_FEN,
    "data": [[0.0] * 8 for _ in range(8)],
    "moves": [],
}

def render_web_title(title: str) -> str:
    return f'<h1 style="color: #fff; font-family: Arial, sans-serif; margin-bottom: 15px; text-align: center;">{title}</h1>'

def render_text_box(label: str, content: str) -> str:
    return f'''
    <div style="background: #2a2a2a; border: 1px solid #444; padding: 10px; margin-bottom: 15px; color: #ddd; font-family: Arial, sans-serif; font-size: 14px;">
        <strong>{label}:</strong> <span>{content}</span>
    </div>
    '''

def render_scrolling_panel(moves) -> str:
    rows = []
    for i in range(0, len(moves), 2):
        move_num = (i // 2) + 1
        white = moves[i]
        black = moves[i + 1] if i + 1 < len(moves) else ""
        rows.append(
            f'<div style="display: flex; font-family: monospace; font-size: 14px; padding: 4px 0;">'
            f'<span style="width: 35px; color: #888;">{move_num}.</span>'
            f'<span style="flex: 1; color: #ddd;">{white}</span>'
            f'<span style="flex: 1; color: #ddd;">{black}</span>'
            f'</div>'
        )
    moves_html = "".join(rows)
    return f'''
    <div style="width: 220px; height: 435px; background: #2a2a2a; border: 1px solid #3a3a3a; padding: 12px; box-sizing: border-box; overflow-y: auto; display: flex; flex-direction: column;" id="movePanel">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 10px; border-bottom: 1px solid #444; padding-bottom: 6px; color: #fff;">Move History</div>
        {moves_html}
    </div>
    '''

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
            '''text_elements.append(
                f'<text x="{x}" y="{y}" font-size="14" font-weight="bold" fill="red" text-anchor="middle">{val:.0f}</text>'
            )'''

    return svg_raw.replace("</svg>", "".join(text_elements) + "</svg>")

@app.route("/update", methods=["POST"])
def update_state():
    req_data = request.get_json(silent=True) or {}
    if "fen" in req_data:
        state["fen"] = req_data["fen"]
    if "data" in req_data:
        state["data"] = req_data["data"]
    if "moves" in req_data:
        state["moves"] = req_data["moves"]
    if "turn" in req_data:
        state["turn"] = req_data["turn"]
    return jsonify({"status": "ok"})

@app.route("/")
def render_board():
    try:
        board = chess.Board(state["fen"])
    except ValueError:
        return "Invalid FEN string provided", 400
    
    board_svg = generate_board_svg(board, state["data"])
    
    title_html = render_web_title("board")
    panel_html = render_scrolling_panel(state["moves"])
    turn_box = render_text_box("turn", state["turn"])

    html_content = f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="1">
            <style>
                body {{
                    margin: 0;
                    background: #1e1e1e;
                    color: #e0e0e0;
                    font-family: Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }}
                .main-layout {{
                    display: flex;
                    gap: 20px;
                    align-items: flex-start;
                }}
                .sidebar {{
                    display: flex;
                    flex-direction: column;
                    height: 500px;
                }}
            </style>
        </head>
        <body>
            {title_html}
            <div class="main-layout">
                <div>
                    {board_svg}
                </div>
                <div class="sidebar">
                    {turn_box}
                    {panel_html}
                </div>
            </div>
            <script>
                // Auto-scroll move log to bottom on reload
                const panel = document.getElementById('movePanel');
                if (panel) {{
                    panel.scrollTop = panel.scrollHeight;
                }}
            </script>
        </body>
    </html>
    """
    return Response(html_content, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)