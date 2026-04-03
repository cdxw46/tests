import json
import sys
import secrets
from math import pi
from collections import Counter

from qiskit import QuantumCircuit, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel,
    depolarizing_error,
    amplitude_damping_error,
)

class Vault:
    def __init__(self):
        self.visible_bits = 64
        self.secret_key = bin(secrets.randbits(self.visible_bits))[2:].zfill(self.visible_bits)
        self.total_data_qubits = len(self.secret_key)
        self.ancilla_qubits = 16
        self.total_qubits = self.total_data_qubits + self.ancilla_qubits
        self.backend = AerSimulator(method="matrix_product_state")
        self.noise_model = self._build_noise_model()
        self.shots = 4096
        self.idle_cycles = 6
        self.max_circuit_ops = 8 * self.total_data_qubits
        self.min_data_ancilla_links = self.total_data_qubits // 4
        self.min_active_ancillas = self.ancilla_qubits // 4
        self.max_oracle_calls = 1
        self.oracle_calls = 0

    def _build_noise_model(self) -> NoiseModel:
        noise = NoiseModel()
        single_err = depolarizing_error(0.008, 1)
        two_err = depolarizing_error(0.02, 2)
        meas_err = depolarizing_error(0.02, 1)
        noise.add_all_qubit_quantum_error(single_err, ["x", "y", "z", "h", "s", "sdg", "t", "tdg", "rx", "ry", "rz", "p", "id"])
        noise.add_all_qubit_quantum_error(two_err, ["cx", "cz", "swap"])
        noise.add_all_qubit_quantum_error(meas_err, ["measure"])
        return noise

    def _prepare_state(self, circuit: QuantumCircuit):
        for idx, bit in enumerate(self.secret_key):
            if bit == "1":
                circuit.x(idx)

    def _is_valid_qubit(self, index: int) -> bool:
        return 0 <= index < self.total_qubits

    def _register_single_qubit_use(self, qubit: int, stats: dict):
        if qubit >= self.total_data_qubits:
            stats["ancilla_ops"] += 1
            anc_idx = qubit - self.total_data_qubits
            stats["ancilla_touches"][anc_idx] += 1

    def _register_two_qubit_use(self, q1: int, q2: int, stats: dict):
        data_limit = self.total_data_qubits
        q1_is_data = q1 < data_limit
        q2_is_data = q2 < data_limit
        if q1_is_data != q2_is_data:
            stats["data_ancilla_links"] += 1
        if not q1_is_data:
            stats["ancilla_ops"] += 1
            stats["ancilla_touches"][q1 - data_limit] += 1
        if not q2_is_data:
            stats["ancilla_ops"] += 1
            stats["ancilla_touches"][q2 - data_limit] += 1

    def build_circuit(self, raw_instructions: str):
        qc = QuantumCircuit(self.total_qubits)
        self._prepare_state(qc)
        stats = {
            "ops": 0,
            "ancilla_ops": 0,
            "data_ancilla_links": 0,
            "ancilla_touches": [0] * self.ancilla_qubits,
        }
        if not raw_instructions.strip():
            return qc, stats

        instructions = [part.strip() for part in raw_instructions.split(";") if part.strip()]

        single_gates = {"X": qc.x, "Y": qc.y, "Z": qc.z, "H": qc.h, "S": qc.s, "SDG": qc.sdg, "T": qc.t, "TDG": qc.tdg}
        two_gates = {"CX": qc.cx, "CZ": qc.cz, "SWAP": qc.swap}

        for instr in instructions:
            if stats["ops"] >= self.max_circuit_ops:
                break
            try:
                gate, payload = instr.split(":", 1)
                gate = gate.upper().strip()
                params = [int(p.strip()) for p in payload.split(",")]

                if gate in {"RX", "RY", "RZ", "PHASE"} and len(params) == 2:
                    if not self._is_valid_qubit(params[1]):
                        continue
                    angle = params[0] * (pi / 180)
                    if gate == "PHASE":
                        qc.p(angle, params[1])
                    else:
                        getattr(qc, gate.lower())(angle, params[1])
                    stats["ops"] += 1
                    self._register_single_qubit_use(params[1], stats)
                elif gate in single_gates and len(params) == 1:
                    if not self._is_valid_qubit(params[0]):
                        continue
                    single_gates[gate](params[0])
                    stats["ops"] += 1
                    self._register_single_qubit_use(params[0], stats)
                elif gate in two_gates and len(params) == 2:
                    if not self._is_valid_qubit(params[0]) or not self._is_valid_qubit(params[1]):
                        continue
                    two_gates[gate](params[0], params[1])
                    stats["ops"] += 1
                    self._register_two_qubit_use(params[0], params[1], stats)
                elif gate == "CCX" and len(params) == 3:
                    if not all(self._is_valid_qubit(qubit) for qubit in params):
                        continue
                    qc.ccx(params[0], params[1], params[2])
                    stats["ops"] += 1
                    self._register_two_qubit_use(params[0], params[2], stats)
                    self._register_two_qubit_use(params[1], params[2], stats)
            except Exception:
                continue

        return qc, stats

    def _validate_strategy(self, circuit: QuantumCircuit, stats: dict):
        compiled_circuit = transpile(
            circuit,
            optimization_level=3,
            basis_gates=self.noise_model.basis_gates
        )

        circuit_stats = {
            "ops": 0,
            "ancilla_ops": 0,
            "data_ancilla_links": 0,
            "ancilla_touches": [0] * self.ancilla_qubits,
        }

        for inst in compiled_circuit.data:
            gate_name = inst.operation.name
            if gate_name in ['barrier', 'id', 'measure']:
                continue

            qubits = [compiled_circuit.find_bit(q).index for q in inst.qubits]
            circuit_stats["ops"] += 1

            if len(qubits) == 1:
                self._register_single_qubit_use(qubits[0], circuit_stats)
            elif len(qubits) == 2:
                self._register_two_qubit_use(qubits[0], qubits[1], circuit_stats)
            elif len(qubits) == 3:
                self._register_two_qubit_use(qubits[0], qubits[2], circuit_stats)
                self._register_two_qubit_use(qubits[1], qubits[2], circuit_stats)

        if circuit_stats["data_ancilla_links"] < self.min_data_ancilla_links:
            return False, "Circuit rejected: insufficient structural activity."
        active_ancillas = sum(1 for e in circuit_stats["ancilla_touches"] if e > 0)
        if active_ancillas < self.min_active_ancillas:
            return False, "Circuit rejected: insufficient structural activity."

        return True, "ok"

    def run_oracle(self):
        if self.oracle_calls >= self.max_oracle_calls:
            print("\n[Oracle] Access denied: query budget exhausted.")
            return

        print("\n[Oracle] Provide corrective circuit (GATE:p1,p2;...):")
        raw = input("> ")
        circuit, stats = self.build_circuit(raw)
        is_valid, reason = self._validate_strategy(circuit, stats)
        if not is_valid:
            print(f"\n[Oracle] {reason}")
            return

        self.oracle_calls += 1
        for _ in range(self.idle_cycles):
            for i in range(self.total_qubits):
                circuit.id(i)

        creg = ClassicalRegister(self.total_data_qubits)
        circuit.add_register(creg)
        circuit.measure(range(self.total_data_qubits), range(self.total_data_qubits))
        compiled = transpile(circuit, basis_gates=self.noise_model.basis_gates, optimization_level=0)
        result = self.backend.run(compiled, shots=self.shots, noise_model=self.noise_model, memory=True).result()
        print(f"\n[Oracle] Results: {json.dumps(result.get_counts())}")

    def attempt_unlock(self):
        print(f"\n[Vault] ONE ATTEMPT ONLY. Enter the {self.total_data_qubits}-bit access code:")
        code = input("> ").strip()
        if code == self.secret_key:
            print(f"\n[+] Access Granted! The vault opens: {open('flag.txt').read()}")
        else:
            print("\n[-] Access Denied. Security lockdown engaged.")
        sys.exit(0)

    def menu(self):
        banner = """
    ╔══════════════════════════════════════════╗
    ║                NOISY VAULT               ║
    ╚══════════════════════════════════════════╝
    Status: SECURE - Random rotation key engaged
    Warning: Only ONE attempt to unlock
    """
        print(banner)
        while True:
            print("1. Access Quantum Oracle (Single Query)")
            print("2. Enter Vault Access Code (One-Shot)")
            print("3. Exit")
            print()
            choice = input("Choice > ").strip()
            
            if choice == "1":
                self.run_oracle()
            elif choice == "2":
                self.attempt_unlock()
            elif choice == "3":
                break

            print()

if __name__ == "__main__":
    Vault().menu()