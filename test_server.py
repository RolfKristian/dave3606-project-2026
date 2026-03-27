import json
from mock_db import MockDB
from server import get_sets_logic, get_api_set_logic, cache



def test_get_sets_logic():
    mock_rows = [
        (1, "Test Set"),
        (2, "Another Set")
    ]

    mock_db = MockDB({
        ("SELECT id, name FROM lego_set ORDER BY id", None): mock_rows
    })

    html = get_sets_logic(mock_db, "UTF-8")

    assert "Test Set" in html
    assert "Another Set" in html

    assert '<a href="/set?id=1">1</a>' in html
    assert '<a href="/set?id=2">2</a>' in html

    assert 'charset="UTF-8"' in html



def test_get_api_set_logic_first_call():
    cache.cache.clear()

    set_id = "1234"

    set_row = [(set_id, "Dragon", 2020, "Ninjago", "img.png")]
    inventory_rows = [
        (1, 5, 10, "brick1.png"),
        (2, 7, 3, "brick2.png")
    ]

    set_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set WHERE id = %s
    """

    inventory_query = """
        SELECT lego_inventory.brick_type_id, lego_inventory.color_id, lego_inventory.count, lego_brick.preview_image_url
        FROM lego_inventory
        LEFT JOIN lego_brick ON (
            lego_inventory.brick_type_id = lego_brick.brick_type_id AND lego_inventory.color_id = lego_brick.color_id 
        )
        WHERE set_id = %s"""

    mock_db = MockDB({
        (set_query, (set_id,)): set_row,
        (inventory_query, (set_id,)): inventory_rows
    })

    json_str = get_api_set_logic(mock_db, set_id)
    data = json.loads(json_str)

    assert data["id"] == set_id
    assert data["name"] == "Dragon"
    assert data["year"] == 2020
    assert data["category"] == "Ninjago"
    assert len(data["inventory"]) == 2

    assert cache.get(set_id) != -1



def test_get_api_set_logic_second_call():
    cache.cache.clear()

    set_id = "1234"

    set_row = [(set_id, "Dragon", 2020, "Ninjago", "img.png")]
    inventory_rows = [
        (1, 5, 10, "brick1.png"),
        (2, 7, 3, "brick2.png")
    ]

    set_query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set WHERE id = %s
    """

    inventory_query = """
        SELECT lego_inventory.brick_type_id, lego_inventory.color_id, lego_inventory.count, lego_brick.preview_image_url
        FROM lego_inventory
        LEFT JOIN lego_brick ON (
            lego_inventory.brick_type_id = lego_brick.brick_type_id AND lego_inventory.color_id = lego_brick.color_id 
        )
        WHERE set_id = %s"""

    mock_db = MockDB({
        (set_query, (set_id,)): set_row,
        (inventory_query, (set_id,)): inventory_rows
    })

    first_json = get_api_set_logic(mock_db, set_id)

    mock_db.received.clear()

    second_json = get_api_set_logic(mock_db, set_id)

    assert second_json == first_json

    assert mock_db.received == []
    