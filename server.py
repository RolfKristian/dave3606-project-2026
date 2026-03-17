import json
import html
import psycopg
from flask import Flask, Response, request, jsonify
from time import perf_counter

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}

# Global scope decleration
conn = psycopg.connect(**DB_CONFIG)

@app.route("/")
def index():
    template = open("templates/index.html").read()
    return Response(template)


@app.route("/sets")
def sets():
    template = open("templates/sets.html").read()
    rows = ""

    start_time = perf_counter()
    try:
        with conn.cursor() as cur:
            cur.execute("select id, name from lego_set order by id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                existing_rows = rows
                rows = existing_rows + f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n'
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()

    page_html = template.replace("{ROWS}", rows)
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
        with conn.cursor() as cur:
            query = "SELECT set_id, count FROM lego_inventory WHERE brick_type_id = %s"
            cur.execute(query, (brick_type_id,))

            rows = cur.fetchall()
            for row in rows
                result.add({"set_id": row[0], "count": row[1]})
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500

@app.route("/api/color_id_in_sets/<color_id>")
def get_sets_by_color(color_id):
    try:
        result = []
        with conn.cursor() as cur:
            query = "SELECT set_id, brick_type_id, count FROM lego_inventory WHERE color_id = %s"
            cur.execute(query, (color_id,))

            rows = cur.fetchall()
            for row in rows
                result.append({"set_id": row[0], "brick_type_id": row[1], "count": row[2]})
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"internal server error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.
