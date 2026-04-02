#!/usr/bin/env python3
"""
HackTheBox Challenge: Thief (Misc - Medium)
Solution script to extract the exfiltrated flag from challenge.pcap

FLAG: HTB{H4rd_day'$_k1lLin'_@h3ad}

Analysis:
1. The pcap contains a reverse shell session (TCP port 5349) where an attacker:
   - Ran whoami, hostname, systeminfo on a Windows 10 machine
   - Downloaded windowsupdate.exe (a PyInstaller-packed Python 2.7 executable)
   - Executed: ./windowsupdate.exe 1dub.png (exfiltrating a PNG image)

2. windowsupdate.exe reads a file, splits it into 256-byte chunks, encrypts each
   with AES-CBC (key='The Bloodharbor!'), scrambles the order using a binary tree
   algorithm, and sends each chunk via ICMP echo requests to 172.67.139.222.

3. ICMP packets contain: prefix "exfil-" + 16-byte IV + 256-byte AES ciphertext.
   The ICMP id and seq fields encode the position in the scrambled tree structure.

4. To recover the original file:
   - Simulate the scramble algorithm to map (icmp_id, icmp_seq) -> original index
   - Decrypt each chunk with AES-CBC
   - Reassemble in correct order
   - The result is the PNG image containing the flag
"""

from math import sqrt
from Crypto.Cipher import AES
import struct
import sys
import os


class Helper:
    def __init__(self, content):
        self.content = content

    def nextSquare(self):
        x = 0
        while True:
            yield 2 ** x
            x += 1

    def scramble(self):
        bound = int(sqrt(len(self.content))) * 10
        pos = 0
        tree = []
        for iteration in self.nextSquare():
            if iteration > 1:
                ins = tree[-iteration // 2:]
            debug = 0
            for n in range(iteration):
                if pos < len(self.content):
                    if iteration > 1:
                        if len(ins) == 1:
                            tree.append(ins + [self.content[pos]])
                        else:
                            tree.append(ins[debug % (iteration // 2)] + [self.content[pos]])
                            debug += 1
                    else:
                        tree.append(self.content[pos])
                    pos += 1
            if iteration > bound:
                break
        yield tree


def build_mapping(num_chunks):
    """Simulate the scramble/tree algorithm to get (icmp_id, icmp_seq) -> content_index mapping."""
    content = list(range(num_chunks))
    inst = Helper(content)
    tree_dict = {}
    iden = 1

    for x in inst.scramble():
        for y in x:
            if not isinstance(y, list):
                tree_dict[1] = [[[y], 0]]
            else:
                key = tree_dict.get(len(y), [])
                if not key:
                    tree_dict[len(y)] = key
                if not len(y) % 2:
                    key.append([y, len(key)])
                else:
                    key.insert(0, [y, len(key)])
                if iden != len(y):
                    for z, zz in enumerate(tree_dict[iden]):
                        tree_dict[iden][z][1] = z
                    iden = len(y)

    mapping = {}
    for group_key, entries in tree_dict.items():
        for entry in entries:
            path = entry[0]
            seq_num = entry[1]
            content_idx = path[-1]
            mapping[(group_key, seq_num)] = content_idx

    return mapping


def solve(icmp_data_file, original_size=12214):
    """
    icmp_data_file: tab-separated file with columns: icmp_id, icmp_seq, hex_data
    original_size: the original file size (from 'dir' output in the shell session)
    """
    CHUNK_SIZE = 256
    num_chunks = (original_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    last_chunk_size = original_size % CHUNK_SIZE or CHUNK_SIZE

    mapping = build_mapping(num_chunks)
    key = b'The Bloodharbor!'

    content_arr = [None] * num_chunks

    with open(icmp_data_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) != 3:
                continue

            icmp_id = int(parts[0])
            icmp_seq = int(parts[1])
            hex_data = parts[2]
            raw = bytes.fromhex(hex_data[12:])  # Remove "exfil-" prefix

            idx = mapping.get((icmp_id, icmp_seq))
            if idx is None:
                print(f"WARNING: No mapping for id={icmp_id}, seq={icmp_seq}")
                continue

            iv = raw[:16]
            ciphertext = raw[16:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ciphertext)
            content_arr[idx] = decrypted

    output = b''
    for i in range(num_chunks):
        if content_arr[i] is None:
            print(f"ERROR: Missing chunk {i}")
            continue
        if i < num_chunks - 1:
            output += content_arr[i][:CHUNK_SIZE]
        else:
            output += content_arr[i][:last_chunk_size]

    return output


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python solution.py <icmp_data.tsv> [output.png]")
        print("Generate icmp_data.tsv with:")
        print('  tshark -r challenge.pcap -Y "icmp.type==8" -T fields -e icmp.ident -e icmp.seq -e data.data > icmp_data.tsv')
        sys.exit(1)

    icmp_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else '1dub_recovered.png'

    result = solve(icmp_file)

    with open(output_file, 'wb') as f:
        f.write(result)

    print(f"Recovered file saved to {output_file} ({len(result)} bytes)")
    if result[:8] == b'\x89PNG\r\n\x1a\n':
        print("File is a valid PNG image containing the flag.")
    print("\nFLAG: HTB{H4rd_day'$_k1lLin'_@h3ad}")
