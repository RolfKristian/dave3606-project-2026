import psycopg

conn = psycopg.connect(
    host="localhost",
    port=9876,
    dbname="lego-db",
    user="lego",
    password="bricks",
)

cur = conn.cursor()

cur.execute(
    """
    drop table if exists lego_set cascade;
    drop table if exists lego_brick cascade;
    drop table if exists lego_inventory cascade;
    """
)

cur.execute(
    """
    create table lego_set(
        id text not null primary key,
        name text not null,
        year int null,
        category text null,
        preview_image_url text null
    );
    """
)
cur.execute(
    """
    create table lego_brick(
        brick_type_id text not null,
        color_id int not null,
        name text not null,
        preview_image_url text null,
        primary key (brick_type_id, color_id)
    );
    """
)
cur.execute(
    """
    create table lego_inventory(
        set_id text not null,
        brick_type_id text not null,
        color_id int not null,
        count int not null,
        primary key (set_id, brick_type_id, color_id),
        foreign key (set_id) references lego_set(id),
        foreign key (brick_type_id, color_id) references lego_brick(brick_type_id, color_id)
    );
    """
)

# Code that creates indexes on item frequently read from, this is a part of Task 2.

    # - Which LEGO sets contain a specific brick type, regardless of color?
        # We can put a index on lego_inventory(brick_type_id, set_id).

    # - Which LEGO sets contain bricks of a specific color, regardless of type
        # Put index on lego_inventory(color_id, set_id).

    # Explanation for these indexes: A Lego database is often more read-heavy rather than write-heavy. Hence, creating these indexes shoudl speed up select-statements drastically. Insertion and updating will take a bit longer time as the DBClient has to update the underlying B-tree for every query, but this is a good trade-off considering way more reading will be done than writing.

cur.execute("CREATE INDEX IF NOT EXISTS idx_brick_in_sets ON lego_inventory(brick_type_id, set_id);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_color_in_sets ON lego_inventory(color_id, set_id);")

cur.close()
conn.commit()
conn.close()
