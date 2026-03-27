import json
from mock_db import MockDB
from server import get_sets_logic, get_api_set_logic, cache, get_set_binary_data,get_sets_by_column

def AssertionErrorMessage(label,expected,actual):
    return (
        f"\n[Fail] {label} is incorrect" 
        f"\nExpected: {expected}" 
        f"\nActual: {actual}"
    )
    

def find_row(html,row_marker):
    start_row = html.find(row_marker)
    tag_opening = "<td>"
    #Finds the start and end of the td tag: <td>Test Set</td>
    if start_row != -1:
        tdCell_start = html.find("<td>",start_row)
        tdCell_end = html.find("</td>",tdCell_start)
        #Cleans the row for readability
        return html[tdCell_start + len(tag_opening):tdCell_end].strip()
        
    else:
        return "Row missing"


def test_get_sets_logic():
    mock_rows = [
        (1, "Test Set"),
        (2, "Another Set")
    ]
    expected_sql = "SELECT id, name FROM lego_set ORDER BY id"
    mock_db = MockDB({(expected_sql, None): mock_rows})
    html = get_sets_logic(mock_db, "UTF-8")
    
    #For finding the specific html row/tag for assertions
    row_marker_set1 = 'id=1'
    row_marker_set2 = 'id=2'
    
    #Testing to see if the sql is valid
    assert(expected_sql, None) in mock_db.received, "The Sql sent to the database was incorrect"


    #  Test for data verification for set 1
    expected_set1 = "Test Set"
    actual_setRow1 = find_row(html,row_marker_set1)
    assert expected_set1 ==  actual_setRow1, AssertionErrorMessage("Set 1",expected_set1,actual_setRow1)
    
    # Test for data verification for set 2
    expected_set2 = "Another Set"
    actual_setRow2 = find_row(html,row_marker_set2)
    assert expected_set2 == actual_setRow2, AssertionErrorMessage("Set 2", expected_set2,actual_setRow2)


    #Test for set 1 link verfication in html
    expected_link1 = '<a href="/set?id=1">1</a>'
    actual_link1 = find_row(html,row_marker_set1)

    assert expected_link1 in html, AssertionErrorMessage("Set Link",expected_link1,actual_link1)


    #Test for set 2 link verification in html
    expected_link2 = '<a href="/set?id=2">2</a>'
    actual_link2 = find_row(html,row_marker_set2)
    assert expected_link2 in html, AssertionErrorMessage("Set link",expected_link2,actual_link2)

    #Test for encoding verification
    expected_charset = 'charset="UTF-8'
    html_start = html.find("<meta")
    html_end = html.find(">",html_start) + 1
    actual_charset = html[html_start:html_end]
    assert expected_charset in actual_charset, AssertionErrorMessage("Charset",expected_charset,actual_charset)



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

    assert data["id"] == set_id, AssertionErrorMessage("Set Id", set_id, data["id"])
    assert data["name"] == "Dragon", AssertionErrorMessage("Name", "Dragon", data["name"])
    assert data["year"] == 2020, AssertionErrorMessage("Year", 2020, data["year"])
    assert data["category"] == "Ninjago", AssertionErrorMessage("Category", "Ninjago", data["category"])
    assert len(data["inventory"]) == 2, AssertionErrorMessage("Inventory", 2, len(data["inventory"]))

    assert cache.get(set_id) != -1, AssertionErrorMessage("Cache check", "Valid (not -1)", -1)



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

    assert second_json == first_json, AssertionErrorMessage("Json", first_json, second_json)

    assert mock_db.received == [], AssertionErrorMessage("Mock database query", [], mock_db.received)

def test_get_api_set_binary_data():
    set_id = "1234"
    set_row = ("1234", "Dragon", 2020)
    inv_rows = [(1,5,10)]

    mock_db = MockDB({
        ("SELECT id, name, year FROM lego_set WHERE id = %s", (set_id,)): [set_row],
        ("SELECT brick_type_id, color_id, count FROM lego_inventory WHERE set_id = %s", (set_id,)): inv_rows
    })

    binary_data = get_set_binary_data(mock_db,set_id)

    assert isinstance(binary_data,bytearray), "Output should be bytearray"
    assert len(binary_data) > 0, "Binary data should not be empty"


def test_get_sets_by_column():
    query = "SELECT set_id, count FROM lego_inventory WHERE brick_type_id = %s"
    column_names = ["set_id", "count"]
    set_rows = [("4545",1),("111111",10)]
    mock_db = MockDB({(query, ("brick_1",)): set_rows})
    json_result = get_sets_by_column(mock_db,query,"brick_1",column_names)
    data = json.loads(json_result)

    assert len(data) == 2, AssertionErrorMessage("row count", 2, len(data))
    assert data[0]["set_id"] == "4545", AssertionErrorMessage("First row", "4545", data[0]["set_id"])

def test_get_api_set_logic_not_found():
    set_id = "0"
    query = """
        SELECT id, name, year, category, preview_image_url
        FROM lego_set WHERE id = %s
    """
    mock_db = MockDB({
        (query, (set_id,)): [] 
    })
    result = get_api_set_logic(mock_db, set_id)
    assert result is None, AssertionErrorMessage("Missing Set", None, result)

if __name__ == "__main__":
    print("Running tests...")
    test_get_sets_logic()
    test_get_api_set_logic_first_call()
    test_get_api_set_logic_second_call()
    test_get_api_set_binary_data()
    test_get_sets_by_column()
    test_get_api_set_logic_not_found()
    print("All tests passed!")