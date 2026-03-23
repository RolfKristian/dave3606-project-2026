import json
import gzip
from collections import defaultdict
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=9876,
    dbname="lego-db",
    user="lego",
    password="bricks",
)

with gzip.open("bricklink.json.gz") as f:
    sets = json.load(f)

cur = conn.cursor()

bricks = defaultdict(set)
for s in sets:
    for inv in s["inventory"] or []:
        bricks[(inv["brickId"], inv["colorId"])].add((inv["name"], inv["previewImageUrl"]))

for bc, names_and_urls in bricks.items():
    if len(names_and_urls) != 1:
        raise Exception(f"{bc} {names_and_urls}")
    else:
        name, preview_image_url = list(names_and_urls)[0]
        brick_type_id, color_id = bc
        cur.execute(
            """
            insert into lego_brick(brick_type_id, color_id, name, preview_image_url)
            values (%s, %s, %s, %s)
            """,
            (brick_type_id, color_id, name, preview_image_url)
        )

for i, s in enumerate(sets):
    year = s["year"]
    cur.execute(
        """
        insert into lego_set(id, name, year, category, preview_image_url) values(%s, %s, %s, %s, %s)
        ;
        """,
        (s["setNumber"], s["name"], None if year == 0 else year, s["category"], s["previewImageUrl"])
    )

for i, s in enumerate(sets):
    for inv in s["inventory"] or []:
        cur.execute(
            """
            insert into lego_inventory(set_id, brick_type_id, color_id, count)
            values (%s, %s, %s, %s)
            on conflict (set_id, brick_type_id, color_id) do nothing;
            """,
            (s["setNumber"], inv["brickId"], inv["colorId"], inv["count"])
        )
    if i % 100 == 0:
        print(i)

conn.commit()

cur.close()
conn.close()
