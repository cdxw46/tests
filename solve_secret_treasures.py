#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def decode_uart_bytes_from_csv(csv_path: Path, baud_rate: float = 38400.0) -> list[int]:
    bit_time = 1.0 / baud_rate
    half_bit = bit_time / 2.0

    transitions: list[tuple[float, int]] = []
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            transitions.append((float(row[0]), int(row[1])))

    decoded: list[int] = []
    i = 0
    while i < len(transitions) - 1:
        if transitions[i][1] == 0:
            start_time = transitions[i][0]
            value = 0

            for bit_idx in range(8):
                sample_time = start_time + half_bit + (bit_idx + 1) * bit_time
                state = 0

                for j in range(i, len(transitions)):
                    if transitions[j][0] > sample_time:
                        state = transitions[j - 1][1]
                        break

                if state == 1:
                    value |= 1 << bit_idx

            decoded.append(value)

            stop_time = start_time + bit_time * 9.5
            while i < len(transitions) and transitions[i][0] < stop_time:
                i += 1
        else:
            i += 1

    return decoded


def prng_step(state: int) -> tuple[int, int]:
    state = (0x41C64E6D * state + 0x8042A) & 0xFFFFFFFF

    # Equivalent to state % 0x00FFFFFF (as compiled in random_generator()).
    # Kept explicit to mirror firmware behavior.
    high = ((257 * state) >> 32) & 0xFFFFFFFF
    q = (((state - high) >> 1) + high) >> 23
    value = (state - (q * 0x00FFFFFF)) & 0xFFFFFFFF
    value %= 0x00FFFFFF

    return state, value


def recover_flag_from_seed(seed: int, flash: bytes) -> str:
    state = seed
    out = bytearray()
    for _ in range(49):
        state, r1 = prng_step(state)
        state, r2 = prng_step(state)
        state, r3 = prng_step(state)
        addr = (r1 & 0xFF0000) | (r2 & 0xFF00) | (r3 & 0xFF)
        out.append(flash[addr])
    return out.decode("latin-1")


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve HTB Secret Treasures challenge.")
    parser.add_argument(
        "--csv",
        default="/workspace/saleae-binparser/exported/digital.csv",
        help="Path to exported Saleae CSV (Time [s], Channel 0).",
    )
    parser.add_argument(
        "--flash",
        default="/workspace/hw_secret/flash_memory_dump.bin",
        help="Path to flash memory dump.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    flash_path = Path(args.flash)

    if not csv_path.exists():
        raise SystemExit(f"CSV no encontrado: {csv_path}")
    if not flash_path.exists():
        raise SystemExit(f"Flash dump no encontrado: {flash_path}")

    flash = flash_path.read_bytes()
    decoded_bytes = decode_uart_bytes_from_csv(csv_path)
    digits = "".join(chr(b) for b in decoded_bytes if 48 <= b <= 57)
    candidates = [digits[i : i + 8] for i in range(0, len(digits) - 7, 8)]

    for idx, code in enumerate(candidates):
        seed = int(code)
        candidate = recover_flag_from_seed(seed, flash)
        if candidate.startswith("HTB{") and candidate.endswith("}"):
            print(f"Passcode: {code} (chunk #{idx})")
            print(f"Flag: {candidate}")
            return

    raise SystemExit("No se encontró una flag válida.")


if __name__ == "__main__":
    main()
