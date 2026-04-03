"""
Solver for "Cascading the Seven Seas" CTF challenge
RITSEC CTF - CSS-based x86 emulator

The challenge implements a full 16-bit x86 CPU emulator entirely in CSS,
using CSS custom properties as registers and memory, and CSS functions
as instruction implementations.

The program is a "Pirate Trivia" quiz with 3 questions:
  1. "Which ocean is the largest?" -> PACIFIC (7 chars)
  2. "Name an aquatic mammal" -> WHALE (5 chars)
  3. "What's the flag?" -> 32-char flag

Flag validation: for each entry (e0, e1, e2, expected) in the data table,
checks that (input[e1] + input[e2]) ^ input[e0] == expected
"""

import re
from z3 import *

with open('challenge.html', 'r') as f:
    content = f.read()

pattern = r'@property --m(\d+)\s*\{[^}]*initial-value:\s*(\d+)'
matches = re.findall(pattern, content)

mem = {}
for addr, val in matches:
    mem[int(addr)] = int(val)

entries = []
for i in range(32):
    base = 800 + i * 8
    e0 = mem.get(base, 0) + mem.get(base+1, 0) * 256
    e1 = mem.get(base+2, 0) + mem.get(base+3, 0) * 256
    e2 = mem.get(base+4, 0) + mem.get(base+5, 0) * 256
    expected = mem.get(base+6, 0) + mem.get(base+7, 0) * 256
    entries.append((e0, e1, e2, expected))

flag = [BitVec(f'f{i}', 16) for i in range(32)]
s = Solver()

s.add(flag[0] == ord('R'))
s.add(flag[1] == ord('S'))
s.add(flag[2] == ord('{'))
s.add(flag[31] == ord('}'))

for i in range(32):
    s.add(flag[i] >= 0x20)
    s.add(flag[i] <= 0x7e)

for e0, e1, e2, exp in entries:
    s.add((flag[e1] + flag[e2]) ^ flag[e0] == exp)

if s.check() == sat:
    m = s.model()
    result = ''.join(chr(m[flag[i]].as_long()) for i in range(32))
    print(f"FLAG: {result}")
else:
    print("No solution found")
