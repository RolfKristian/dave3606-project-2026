import json
import html
import psycopg
import gzip
import struct
from flask import Flask, Response, request, jsonify
from time import perf_counter
from LRU import LRUCache

app = Flask(__name__)
cache = LRUCache(100)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}

class Database:
    def __init__(self):
        self.conn = psycopg.connect(**DB_CONFIG)
        self.cur = self.conn.cursor()

    def execute_and_fetch_all(self, query, params=None):
        self.cur.execute(query, params)
        return self.cur.fetchall()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

def get_sets_logic(db, encoding):
    with open("templates/sets.html") as template:
        content = template.read()
    
    content = content.replace("charset=\"UTF-8\"", f"charset=\"{encoding}\"")
    
    rows = db.execute_and_fetch_all("SELECT id, name FROM lego_set ORDER BY id")
    
    rows_list = []
    for row in rows:
        html_safe_id = html.escape(str(row[0]))
        html_safe_name = html.escape(str(row[1]))
        rows_list.append(
            f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td>'
            f'<td>{html_safe_name}</td></tr>'
        )
    
    return content.replace("{ROWS}", "\n".join(rows_list))

def get_api_set_logic(db, set_id):
    cached_val = cache.get(set_id)
    if cached_val != -1:
        return cached_val

    set_rows = db.execute_and_fetch_all("""
        SELECT id, name, year, category, preview_image_url
        FROM lego_set WHERE id = %s
    """, (set_id,))

    if not set_rows:
        return None

    set_row = set_rows[0]

    inventory_rows = db.execute_and_fetch_all("""
        SELECT lego_inventory.brick_type_id, lego_inventory.color_id, lego_inventory.count, lego_brick.preview_image_url
        FROM lego_inventory
        LEFT JOIN lego_brick ON (
            lego_inventory.brick_type_id = lego_brick.brick_type_id AND lego_inventory.color_id = lego_brick.color_id 
        )
        WHERE set_id = %s""", (set_id,))

    result = {
        "id": set_row[0],
        "name": set_row[1],
        "year": set_row[2],
        "category": set_row[3],
        "preview_image_url": set_row[4],
        "inventory": [
            {
                "brick_type_id": r[0], "color_id": r[1], "count": r[2], "preview_image_url": r[3]
            } for r in inventory_rows
        ]
    }
    
    json_result = json.dumps(result)
    cache.put(set_id, json_result)
    return json_result


def get_set_binary_data(db, set_id):
    query = "SELECT id, name, year FROM lego_set WHERE id = %s"
    rows = db.execute_and_fetch_all(query, (set_id,))
    row = rows[0] if rows else None

    if not row:
        return None

    set_id_val, name, year = row
    
    query = ("""
            SELECT brick_type_id, color_id, count
            FROM lego_inventory
            WHERE set_id = %s
        """)
    inventory_rows = db.execute_and_fetch_all(query, (set_id,))

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
    return data

def get_sets_by_column(db, query, column, column_names):
    rows = db.execute_and_fetch_all(query,(column,))
    result = [dict(zip(column_names, row)) for row in rows]
    return json.dumps(result)

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
    start_time = perf_counter()
    encoding = request.args.get("charset", "UTF-8").upper()
    supported_encoding = {"UTF-8", "UTF-16"}
    if encoding not in supported_encoding:
        encoding = "UTF-8"
    
    db = Database()
    try:
        html_content = get_sets_logic(db, encoding)
        print(f"Time to render all sets: {perf_counter() - start_time}")
        
        page_html_bytes = html_content.encode(encoding)
        compressed_bytes = gzip.compress(page_html_bytes)
        return Response(compressed_bytes, content_type=f"text/html; charset={encoding}", headers={"Content-Encoding": "gzip", "Cache-Control": "max-age=60"})
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500
    finally:
        db.close()

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
    set_id = request.args.get("id", type=str)
    if not set_id:
        return jsonify({"error": "Missing id parameter"}), 400
    
    db = Database()
    try:
        json_str = get_api_set_logic(db, set_id)
        if json_str is None:
            return jsonify({"error": "Set not found"}), 404
        return Response(json_str, content_type="application/json")
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/set/binary")
def api_set_binary():
    set_id = request.args.get("id")
    if not set_id:
        return Response("Missing id", status=400)

    db = Database()
    try:
        data = get_set_binary_data(db,set_id)
        
        if data is None:
            return Response("Set not found", status =404)

        return Response(bytes(data), content_type="application/octet-stream")
    except Exception as e:
        return Response(str(e), status=500)
    finally:
        db.close()

# Task 2 API endpoints:
@app.route("/api/brick_type_in_sets/<brick_type_id>")
def get_sets_by_brick(brick_type_id):
    db = Database()
    try:
        query = "SELECT set_id, count FROM lego_inventory WHERE brick_type_id = %s"
        column_names = ["set_id", "count"]
        result_json = get_sets_by_column(db, query,brick_type_id,column_names)
        return Response(result_json, content_type="application/json")
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/color_id_in_sets/<color_id>")
def get_sets_by_color(color_id):
    db = Database()
    try:
        query = "SELECT set_id, brick_type_id, count FROM lego_inventory WHERE color_id = %s"
        column_names = ["set_id","brick_type_id","count"]
        result_json = get_sets_by_column(db,query,color_id,column_names)
        return Response(result_json, content_type="application/json")
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500
    finally:
        db.close()

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.
