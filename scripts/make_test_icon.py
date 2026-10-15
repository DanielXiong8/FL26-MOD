"""make_test_icon.py — create a 256x256 test PNG with distinct pattern."""
import struct, zlib, os

def create_png(width, height, r, g, b, out_path):
    """Create a solid color PNG without PIL."""
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b""
    for y in range(height):
        raw += b"\x00"  # filter: none
        for x in range(width):
            # Add a simple pattern (diagonal stripes)
            if (x + y) % 20 < 10:
                raw += bytes([r, g, b])
            else:
                raw += bytes([min(255, r+40), min(255, g+40), min(255, b+40)])
    
    compressed = zlib.compress(raw)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    
    with open(out_path, "wb") as f:
        f.write(png)
    print(f"-> {out_path} ({len(png)}B)")

# Red-ish test pattern
create_png(256, 256, 255, 0, 0, r"C:\FL26_Mod\saves\test_icon_red.png")
# Blue-ish
create_png(256, 256, 0, 0, 255, r"C:\FL26_Mod\saves\test_icon_blue.png")
