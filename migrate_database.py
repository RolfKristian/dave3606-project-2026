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
    drop table if exists lego_set;
    create table lego_set(
        id text not null,
        name text not null,
        year int null,
        category text null,
        preview_image_url text null
    );
    """
)
cur.execute(
    """
    drop table if exists lego_brick;
    create table lego_brick(
        brick_type_id text not null,
        color_id int not null,
        name text not null,
        preview_image_url text null
    );
    """
)
cur.execute(
    """
    drop table if exists lego_inventory;
    create table lego_inventory(
        set_id text not null,
        brick_type_id text not null,
        color_id int not null,
        count int not null
    );
    """
)
cur.close()
conn.commit()
conn.close()
