import socket
from random import seed, randint
from hashlib import sha256
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

HOST = "154.57.164.77"
PORT = 31092

private_key = 3262827136301000405966

def recv_until(s, timeout=5):
    s.settimeout(timeout)
    data = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    return data.decode()

# Paso 1: Generar las bases del servidor usando la seed conocida
seed(private_key)
server_bases = []
for i in range(256):
    r = randint(0, 1)
    server_bases.append("Z" if r else "X")

# Enviar las MISMAS bases que el servidor para tener anticorrelación perfecta
user_basis_str = "".join(server_bases)
print(f"User basis (same as server): {user_basis_str[:20]}...")

# Paso 2: Conectar y obtener ciphertext
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

banner = recv_until(s, 3)
print(f"Banner received")

s.send(b"2\n")
recv_until(s, 2)

s.send((user_basis_str + "\n").encode())
resp = recv_until(s, 5)

# Parsear
idx_qk = resp.find("The Quantum key: ")
idx_fe = resp.find("Flag Encrypted: ")

q_user_key_hex = resp[idx_qk+17:idx_qk+17+64]
ct_line = resp[idx_fe+16:]
ct_hex = ct_line.split("\n")[0].strip()

print(f"Quantum user key: {q_user_key_hex}")
print(f"Ciphertext: {ct_hex}")

s.close()

# Paso 3: Reconstruir la clave del servidor
# user_key es hex de los bits de medición del usuario
user_key_bytes = bytes.fromhex(q_user_key_hex)
user_bits = []
for byte in user_key_bytes:
    for bit in range(7, -1, -1):
        user_bits.append((byte >> bit) & 1)

print(f"User bits (first 20): {user_bits[:20]}")

# Anticorrelación: server_bit = 1 - user_bit (cuando bases coinciden)
server_bits = [1 - b for b in user_bits]
print(f"Server bits (first 20): {server_bits[:20]}")

# Server key = SHA256(server_bits as bytes)
def bitsToHash(bits):
    bit_string = ''.join([str(i) for i in bits])
    blocks = bytes([int(bit_string[i:i+8], 2) for i in range(0, len(bit_string), 8)])
    return sha256(blocks).digest()

server_key = bitsToHash(server_bits)
print(f"Server key (AES key): {server_key.hex()}")

# Paso 4: Descifrar
ct = bytes.fromhex(ct_hex)
cipher = AES.new(server_key, AES.MODE_ECB)
plaintext = cipher.decrypt(ct)

try:
    plaintext = unpad(plaintext, 16)
except:
    pass

print(f"\nDecrypted: {plaintext}")
print(f"Flag: {plaintext.decode()}")
