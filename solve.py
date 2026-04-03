#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.12/site-packages')
from pwn import *
import threading
import time

context.log_level = 'error'

HOST = '154.57.164.67'
PORT = 30567
NUM_THREADS = 10
SAMPLES_PER_THREAD = 300

flag_seen = [set() for _ in range(20)]
zero_seen = [set() for _ in range(20)]
lock = threading.Lock()
flag_len = [0]
errors = [0]

def worker(tid):
    try:
        r = remote(HOST, PORT)
        for i in range(SAMPLES_PER_THREAD):
            # Get flag
            r.recvuntil(b'option: ')
            r.sendline(b'1')
            enc = r.recvline().strip().decode()
            fb = bytes.fromhex(enc)
            with lock:
                flag_len[0] = len(fb)
                for j in range(len(fb)):
                    flag_seen[j].add(fb[j])

            # Encrypt zeros
            zeros_hex = '00' * len(fb)
            r.recvuntil(b'option: ')
            r.sendline(b'2')
            r.recvuntil(b'plaintext: ')
            r.sendline(zeros_hex.encode())
            enc2 = r.recvline().strip().decode()
            zb = bytes.fromhex(enc2)
            with lock:
                for j in range(len(zb)):
                    zero_seen[j].add(zb[j])

        r.close()
    except Exception as e:
        with lock:
            errors[0] += 1
        print(f"  Thread {tid} error: {e}")

print(f"[*] Lanzando {NUM_THREADS} threads, {SAMPLES_PER_THREAD} muestras cada uno ({NUM_THREADS*SAMPLES_PER_THREAD} total)...")
start = time.time()
threads = []
for t in range(NUM_THREADS):
    th = threading.Thread(target=worker, args=(t,))
    th.start()
    threads.append(th)
    time.sleep(0.2)

for th in threads:
    th.join()

elapsed = time.time() - start
total = NUM_THREADS * SAMPLES_PER_THREAD
fl = flag_len[0]
print(f"[*] {total} muestras recolectadas en {elapsed:.1f}s (errores: {errors[0]})")
print(f"[*] Flag length: {fl} bytes")

all_good = True
for j in range(fl):
    if len(flag_seen[j]) < 255 or len(zero_seen[j]) < 255:
        all_good = False
        print(f"  Posición {j}: flag_seen={len(flag_seen[j])}, zero_seen={len(zero_seen[j])}")

if not all_good:
    print("[!] No tengo suficientes muestras en alguna posición. Necesito más.")
else:
    print("[+] Todas las posiciones tienen 255 valores vistos!")

C = bytearray(fl)
K = bytearray(fl)
for j in range(fl):
    missing_f = [v for v in range(256) if v not in flag_seen[j]]
    missing_z = [v for v in range(256) if v not in zero_seen[j]]
    if len(missing_f) == 1:
        C[j] = missing_f[0]
    else:
        print(f"  [!] flag pos {j}: missing={missing_f}")
        C[j] = missing_f[0] if missing_f else 0
    if len(missing_z) == 1:
        K[j] = missing_z[0]
    else:
        print(f"  [!] zero pos {j}: missing={missing_z}")
        K[j] = missing_z[0] if missing_z else 0

flag = bytes([c ^ k for c, k in zip(C, K)])
print(f"\n[+] FLAG: {flag}")
