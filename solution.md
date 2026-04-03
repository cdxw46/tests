# Secret Treasures - HTB Challenge Solution

## Flag
`HTB{m3M0ry_5cR4Mbl1Ng_4nd_1CG_423_n07_3n0u9h7!$#}`

## Passcode (Seed)
`73261522`

## Analysis

### Files
- `embedded_software`: ARM ELF binary (Raspberry Pi, wiringPi)
- `flash_memory_dump.bin`: 16MB W25Q128 flash dump
- `input_channel_trace.sal`: Saleae Logic Analyzer capture (serial input)

### Binary Reverse Engineering
The binary:
1. Opens SPI channel 0 (for W25Q128 flash) and serial `/dev/ttyS0` at 38400 baud
2. Reads 8 characters from serial (passcode)
3. Converts to uint32 via `strtoul(buf, 0, 10)` — used as PRNG seed (`next_in_seq`)
4. Initializes W25Q128 flash and reads Unique ID via SPI command 0x4B
5. Compares Unique ID against hardcoded value `d2 66 b4 21 83 51 30 2c`
6. If match: loops 49 times (0x31), each iteration:
   - Calls `random_generator()` 3 times to build a 24-bit flash address
   - Reads 1 byte from flash at that address via SPI read command 0x03
   - Outputs the byte via `putchar()`

### PRNG (Linear Congruential Generator)
```
state = state * 0x41C64E6D + 0x0008042A  (mod 2^32)
result = state % 16777215  (0xFFFFFF)
```

### Solution
Since the passcode is an 8-digit decimal number (max 99999999), brute force is feasible.
For each candidate seed, compute the first 4 flash addresses and check if the bytes
at those addresses spell "HTB{". The seed 73261522 produces the flag.
