import socket
import json
import ast
from collections import Counter

def solve():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("154.57.164.76", 31876))
    
    def read_until(prompt):
        data = b""
        while prompt.encode() not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        return data.decode()

    print(read_until("Choice > "))
    s.sendall(b"1\n")
    
    print(read_until("> "))
    
    # Construct dummy circuit
    # 16 data-ancilla links, 4 active ancillas
    gates = []
    for i in range(16):
        gates.append(f"CX:{i},{64 + (i%4)}")
    
    payload = ";".join(gates) + "\n"
    s.sendall(payload.encode())
    
    out = read_until("Choice > ")
    print(out)
    
    # Parse results
    # [Oracle] Results: {"0101...": 123, ...}
    for line in out.splitlines():
        if "Results:" in line:
            results_str = line.split("Results:")[1].strip()
            results = json.loads(results_str)
            break
            
    # Majority vote for each bit
    # Note: Qiskit bitstrings are little-endian (rightmost bit is qubit 0)
    # Wait, the secret key is prepared as:
    # for idx, bit in enumerate(self.secret_key):
    #     if bit == "1": circuit.x(idx)
    # So idx 0 corresponds to the first character of secret_key.
    # Qiskit measures qubit 0 into the rightmost bit of the string.
    # So the rightmost bit of the string corresponds to secret_key[0].
    # Let's just count 0s and 1s for each position in the bitstring.
    
    bit_counts = [Counter() for _ in range(64)]
    for bitstring, count in results.items():
        # bitstring is 64 bits long
        # Qiskit order: bitstring[0] is qubit 63, bitstring[63] is qubit 0
        for i, bit in enumerate(reversed(bitstring)):
            bit_counts[i][bit] += count
            
    secret_key = ""
    for i in range(64):
        secret_key += bit_counts[i].most_common(1)[0][0]
        
    print(f"Recovered key: {secret_key}")
    
    s.sendall(b"2\n")
    print(read_until("> "))
    s.sendall(secret_key.encode() + b"\n")
    
    print(s.recv(4096).decode())

if __name__ == "__main__":
    solve()
