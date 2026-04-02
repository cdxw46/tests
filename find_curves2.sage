import sys
p = 115792089237316195423570985008687907853269984665640564039457584007908834671663
target = 8748541127929402731638

results = []
product = 1

for b in range(1, 500):
    if b == 7:
        continue
    if product > target:
        break
    try:
        E = EllipticCurve(GF(p), [0, b])
        order = E.order()
        # Solo buscamos factores primos pequeños dividiendo directamente
        remaining = order
        small_primes = []
        for pr in primes(10**7):
            while remaining % pr == 0:
                remaining //= pr
                if pr not in [f for f in small_primes]:
                    small_primes.append(pr)
            if remaining == 1:
                break
        
        for f in small_primes:
            if gcd(product, f) != 1:
                continue
            # Generar punto de orden f
            tries = 0
            while tries < 20:
                P = E.random_point()
                Q = (order // f) * P
                if Q != E(0) and f * Q == E(0):
                    product *= f
                    results.append((b, f, int(Q[0]), int(Q[1])))
                    print(f"b={b}, factor={f}, product={product}", flush=True)
                    break
                tries += 1
            if product > target:
                print(f"SUFICIENTE!", flush=True)
                break
    except Exception as e:
        pass

print(f"\nProduct: {product}")
print(f"Target:  {target}")
print(f"Enough: {product > target}")
print(f"\nResults:")
for r in results:
    print(r)
