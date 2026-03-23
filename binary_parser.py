import struct

def parse(filename):
    with open(filename, "rb") as f:
        data = f.read()

    offset = 0

    id_len = struct.unpack_from("B", data, offset)[0]
    offset += 1
    set_id = data[offset:offset+id_len].decode("utf-8")
    offset += id_len

    year = struct.unpack_from(">H", data, offset)[0]
    offset += 2
    num_parts = struct.unpack_from(">H", data, offset)[0]
    offset += 2

    name_len = struct.unpack_from("B", data, offset)[0]
    offset += 1
    name = data[offset:offset+name_len].decode("utf-8")
    offset += name_len

    inventory_count = struct.unpack_from(">I", data, offset)[0]
    offset += 4

    print(f"Set ID: {set_id}")
    print(f"Name: {name}")
    print(f"Year: {year}")
    print(f"Num parts: {num_parts}")
    print(f"Inventory entries: {inventory_count}")

    for _ in range(inventory_count):
        brick_id_len = struct.unpack_from("B", data, offset)[0]
        offset += 1
        brick_id = data[offset:offset+brick_id_len].decode("utf-8")
        offset += brick_id_len

        color_id, count = struct.unpack_from(">HH", data, offset)
        offset += 4

        print(f"  Brick {brick_id}, Color {color_id}, Count {count}")

if __name__ == "__main__":
    parse("set.bin")
