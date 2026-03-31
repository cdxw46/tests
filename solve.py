import struct
from itertools import permutations

def tea_decrypt_block(v0, v1, key):
    """Standard TEA decryption - 32 rounds"""
    delta = 0x9E3779B9
    total = (delta * 32) & 0xFFFFFFFF  # 0xC6EF3720
    
    for _ in range(32):
        v1 = (v1 - (((v0 << 4) + key[2]) ^ (v0 + total) ^ ((v0 >> 5) + key[3]))) & 0xFFFFFFFF
        v0 = (v0 - (((v1 << 4) + key[0]) ^ (v1 + total) ^ ((v1 >> 5) + key[1]))) & 0xFFFFFFFF
        total = (total - delta) & 0xFFFFFFFF
    
    return v0, v1

encrypted_dwords = [
    0xea0109d5, 0xc8ee03d2,
    0x553f3fc8, 0xa8b34cd9,
    0x3631ad3e, 0x98689219,
    0x4e883f78, 0x082e3c84,
    0x9a6a6cc0, 0x5ab5c6a4
]

# Map (7 cols x 8 rows):
# 0=empty, 1=wall, 2=goal, 3=box, 4=player
game_map = [
    [0, 1, 1, 1, 1, 0, 0],  # row 0
    [1, 1, 4, 2, 1, 0, 0],  # row 1: player(2,1), goal(3,1)
    [1, 0, 3, 0, 1, 0, 0],  # row 2: box(2,2)
    [1, 0, 3, 0, 1, 1, 1],  # row 3: box(2,3)
    [1, 0, 3, 1, 0, 0, 1],  # row 4: box(2,4)
    [1, 2, 0, 0, 0, 2, 1],  # row 5: goal(1,5), goal(5,5)
    [1, 1, 0, 0, 1, 1, 1],  # row 6
    [0, 1, 1, 1, 1, 0, 0],  # row 7
]

# Pixel position formula: X = col*64 + 320, Y = row*64 + 90
def grid_to_pixel(col, row):
    return (col * 64 + 320, row * 64 + 90)

# Goals (value 2) in grid coordinates
goals = [(3, 1), (1, 5), (5, 5)]
# Goals in pixel coordinates
goals_px = [grid_to_pixel(c, r) for c, r in goals]

# Boxes in list order (scanning row by row, left to right):
# box[0] at (2,2), box[1] at (2,3) (moved to 1024,410), box[2] at (2,4)

# TEA key = [Y_box0, X_box0, X_box1, X_box2]
# When all boxes are on goals, positions = goal positions

print("Goals (grid):", goals)
print("Goals (pixel):", goals_px)
print()

for perm in permutations(range(3)):
    # perm[i] = which goal is assigned to box[i]
    g0 = goals_px[perm[0]]  # goal for box[0]
    g1 = goals_px[perm[1]]  # goal for box[1]
    g2 = goals_px[perm[2]]  # goal for box[2]
    
    key = [g0[1], g0[0], g1[0], g2[0]]  # [Y_box0, X_box0, X_box1, X_box2]
    
    # Decrypt all blocks
    decrypted = b""
    for i in range(0, len(encrypted_dwords), 2):
        v0 = encrypted_dwords[i]
        v1 = encrypted_dwords[i + 1]
        d0, d1 = tea_decrypt_block(v0, v1, key)
        decrypted += struct.pack("<II", d0, d1)
    
    # Strip trailing nulls
    decrypted = decrypted.rstrip(b"\x00")
    
    try:
        text = decrypted.decode("ascii", errors="strict")
        if text.startswith("HTB{"):
            print(f"[FOUND FLAG] Permutation {perm}: key={key}")
            print(f"  Flag: {text}")
            print()
    except (UnicodeDecodeError, ValueError):
        pass
    
    # Also print for debugging
    printable = all(32 <= b < 127 for b in decrypted)
    if printable and len(decrypted) > 5:
        text = decrypted.decode("ascii", errors="replace")
        print(f"  Perm {perm}: key={key} -> {repr(text)}")
