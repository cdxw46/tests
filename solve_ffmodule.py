"""
FFModule - HackTheBox Reversing Challenge Solver
================================================
Jupiter Banking Malware Firefox Module

The malware (ffmodule.exe) is a PE64 injector that:
1. XOR-decrypts shellcode (0x5a4 bytes from .data section) with key 0x72
2. Injects the shellcode into firefox.exe via CreateRemoteThread
3. The shellcode hooks PR_Write in nss3.dll to intercept POST requests
4. Captured POST data is encrypted with a custom cipher and sent to 127.0.0.1:1337

The flag is derived from the encryption key table embedded in the shellcode.
Decrypting 0xFF bytes with the cipher yields the flag, because:
  decrypt(0xFF) = NOT -> NEG -> ROR5 -> SUB key = (-key_byte) & 0xFF

Key table is at shellcode offset 0x263 (32 bytes), revealed after XOR 0x72.
"""

import struct


def rol8(val, n):
    return ((val << n) | (val >> (8 - n))) & 0xFF


def ror8(val, n):
    return ((val >> n) | (val << (8 - n))) & 0xFF


def extract_flag(exe_path):
    with open(exe_path, "rb") as f:
        data = f.read()

    # .data section is at file offset 0x15800 (VA 0x140017000)
    data_section_offset = 0x15800

    # XOR first 0x5a4 bytes with 0x72 to get the shellcode
    shellcode = bytearray(data[data_section_offset : data_section_offset + 0x5A4])
    for i in range(len(shellcode)):
        shellcode[i] ^= 0x72

    # Key table is at shellcode offset 0x263, 32 bytes
    key_table = shellcode[0x263 : 0x263 + 32]

    # Compute the flag by reversing the encryption on 0xFF bytes
    flag = bytearray()
    for i in range(32):
        kb = key_table[i]
        kb = (kb + 0xED) & 0xFF
        kb = rol8(kb, 3)
        kb ^= 0x42
        kb = (-kb) & 0xFF
        flag_byte = (-kb) & 0xFF
        flag.append(flag_byte)

    flag_str = flag.decode("ascii")
    end = flag_str.index("}") + 1
    return flag_str[:end]


if __name__ == "__main__":
    flag = extract_flag("FFModule_extracted/rev_ffmodule/ffmodule.exe")
    print(f"Flag: {flag}")
