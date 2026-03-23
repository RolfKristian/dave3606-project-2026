import json
import html
import psycopg
import atexit
import gzip
import struct
from flask import Flask, Response, request, jsonify, g
from time import perf_counter
from psycopg_pool import ConnectionPool

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}

# Use ConnectionPool instead of global definition as it has the same speed. Now every connection wont need to re-autenticate with the DB which saves some time.
db_pool = ConnectionPool(
    conninfo="",
    kwargs=DB_CONFIG,
    min_size=2,
    max_size=4,
    open=True
)

# This ensures Flask returns the connection to the pool at end of each network request.
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db_pool.putconn(db)

def get_conn():
    if 'db' not in g:
        g.db = db_pool.getconn()
    return g.db

@app.route("/")
def index():
    try:
        with open("templates/index.html") as template:
            content = template.read()
            return Response(content)
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500


@app.route("/sets")
def sets():
    rows_list = []
    start_time = perf_counter()

    supported_encodings = {"UTF-16-LE", "UTF-16-BE", "UTF-32-LE", "UTF-32-BE", "UTF-8"}
    encoding = request.args.get("charset", "UTF-8").upper() # This is the user defined encoding from "sets/?charset=UTF-16-LE", with a default value of "UTF-8"
    if encoding not in supported_encodings:
        encoding = "UTF-8"

    try:
        with open("templates/sets.html") as template:
            content = template.read()
            content = content.replace("charset=\"UTF-8\"", f"charset=\"{encoding}\"")

        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set ORDER BY id")
            for row in cur.fetchall():
                html_safe_id = html.escape(str(row[0]))
                html_safe_name = html.escape(str(row[1]))
                rows_list.append(
                    f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td>'
                    f'<td>{html_safe_name}</td></tr>'
                )
        
        print(f"Time to render all sets: {perf_counter() - start_time}")

        page_html = content.replace("{ROWS}", "\n".join(rows_list))

        page_html_bytes = page_html.encode(encoding)
        compressed_bytes = gzip.compress(page_html_bytes)
        return Response(compressed_bytes, content_type=f"text/html; charset={encoding}", headers={"Content-Encoding": "gzip"})
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500

@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    try:
        with open("templates/set.html") as template:
            content = template.read()
        return Response(content)
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500


@app.route("/api/set")
def apiSet():
    try:
        set_id = request.args.get("id", type=str)
        if set_id is None:
            return jsonify({"error": "Missing id parameter"}), 400

        conn = get_conn()
        with conn.cursor() as cur:

            cur.execute("""
                SELECT id, name, year, category, preview_image_url
                FROM lego_set
                WHERE id = %s
            """, (set_id,))
            set_row = cur.fetchone()

            if set_row is None:
                return jsonify({"error": "Set not found"}), 404

            cur.execute("""
                SELECT brick_type_id, color_id, count
                FROM lego_inventory
                WHERE set_id = %s
            """, (set_id,))
            inventory_rows = cur.fetchall()

        result = {
            "id": set_row[0],
            "name": set_row[1],
            "year": set_row[2],
            "category": set_row[3],
            "preview_image_url": set_row[4],
            "inventory": [
                {
                    "brick_type_id": r[0],
                    "color_id": r[1],
                    "count": r[2]
                }
                for r in inventory_rows
            ]
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500


@app.route("/api/set/binary")
def api_set_binary():
    set_id = request.args.get("id")
    if not set_id:
        return Response("Missing id", status=400)

    conn = get_conn()
    with conn.cursor() as cur:

        cur.execute("""
            SELECT id, name, year
            FROM lego_set
            WHERE id = %s
        """, (set_id,))
        row = cur.fetchone()

        if not row:
            return Response("Set not found", status=404)

        set_id_val, name, year = row

        cur.execute("""
            SELECT brick_type_id, color_id, count
            FROM lego_inventory
            WHERE set_id = %s
        """, (set_id,))
        inventory_rows = cur.fetchall()

    num_parts = sum(r[2] for r in inventory_rows)

    data = bytearray()

    set_id_bytes = set_id_val.encode("utf-8")
    data += struct.pack("B", len(set_id_bytes))
    data += set_id_bytes

    data += struct.pack(">H", year)
    data += struct.pack(">H", num_parts)

    name_bytes = name.encode("utf-8")
    data += struct.pack("B", len(name_bytes))
    data += name_bytes

    data += struct.pack(">I", len(inventory_rows))

    for brick_type_id, color_id, count in inventory_rows:
        brick_id_bytes = str(brick_type_id).encode("utf-8")

        data += struct.pack("B", len(brick_id_bytes))
        data += brick_id_bytes

        data += struct.pack(">H", color_id)
        data += struct.pack(">H", count)

    return Response(bytes(data), content_type="application/octet-stream")


# Task 2 API endpoints:
@app.route("/api/brick_type_in_sets/<brick_type_id>")
def get_sets_by_brick(brick_type_id):
    try:
        result = []
        conn = get_conn()
        with conn.cursor() as cur:
            query = "SELECT set_id, count FROM lego_inventory WHERE brick_type_id = %s"
            cur.execute(query, (brick_type_id,))

            rows = cur.fetchall()
            for row in rows:
                result.append({"set_id": row[0], "count": row[1]})
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500

@app.route("/api/color_id_in_sets/<color_id>")
def get_sets_by_color(color_id):
    try:
        result = []
        conn = get_conn()
        with conn.cursor() as cur:
            query = "SELECT set_id, brick_type_id, count FROM lego_inventory WHERE color_id = %s"
            cur.execute(query, (color_id,))

            rows = cur.fetchall()
            for row in rows:
                result.append({"set_id": row[0], "brick_type_id": row[1], "count": row[2]})
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500

# Runs once at server's end and closes all DB connections.
atexit.register(db_pool.close)

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.
