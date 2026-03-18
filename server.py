import json
import html
import psycopg
import atexit
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
    template = open("templates/index.html").read()
    return Response(template)


@app.route("/sets")
def sets():
    template = open("templates/sets.html").read()
    rows_list = []

    start_time = perf_counter()
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set ORDER BY id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                rows_list.append(
                    f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td>'
                    f'<td>{html_safe_name}</td></tr>'
                )
        
        print(f"Time to render all sets: {perf_counter() - start_time}")
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500

    page_html = template.replace("{ROWS}", "\n".join(rows_list))
    return Response(page_html, content_type="text/html")


@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    template = open("templates/set.html").read()
    return Response(template)


@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")
    result = {"set_id": set_id}
    json_result = json.dumps(result, indent=4)
    return Response(json_result, content_type="application/json")

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
