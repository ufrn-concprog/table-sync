#!/usr/bin/env python3
"""Gerador de carga da tabela concorrente (table-sync).

Produz um arquivo de texto (a "carga") que descreve, de forma determinística a
partir de uma semente, as sessões de clientes que acessam a tabela. O mesmo
arquivo é lido pelas versões em Java, C++ e Python e pelo validador.

Uso:
    python3 tools/generate_workload.py --profile leitura --seed 1 --sessions 100000 -o workloads/leitura-1.txt

Formato do arquivo (uma linha por registro; '#' inicia comentário):
    PARAMS keys=1000
    SESSION <id> <op> <op> ...
onde cada <op> ocupa de dois a três tokens:
    G <chave>             get: consultar o valor de uma chave
    P <chave> <valor>     put: gravar um valor (positivo e único em toda a carga)
    S <lo> <hi>           scan: contar as chaves de lo a hi-1 com valor diferente de 0
"""
import argparse
import random
import sys

KEYS = 1000
SCAN_SIZE = 100
HOT_KEYS = 50            # 5% das chaves
HOT_FRACTION = 0.6       # fração dos acessos que vai para as chaves "quentes"

PROFILES = {
    # (leitores, escritores, varredores) em pontos percentuais
    "leitura": dict(weights=(85, 10, 5)),
    "escrita": dict(weights=(40, 45, 15)),
}
ARCHETYPES = ["leitor", "escritor", "varredor"]


def pick_key(rng):
    if rng.random() < HOT_FRACTION:
        return rng.randrange(HOT_KEYS)
    return rng.randrange(KEYS)


def build_session(rng, archetype, next_value):
    """Devolve (operações, próximo valor livre)."""
    ops = []
    if archetype == "leitor":
        for _ in range(rng.randint(10, 30)):
            ops.append(("G", pick_key(rng)))
    elif archetype == "escritor":
        for _ in range(rng.randint(1, 3)):
            k = pick_key(rng)
            ops.append(("P", k, next_value))
            next_value += 1
            ops.append(("G", k))
        for _ in range(rng.randint(2, 6)):
            ops.append(("G", pick_key(rng)))
    else:  # varredor
        for _ in range(rng.randint(2, 6)):
            lo = rng.randrange(0, KEYS - SCAN_SIZE + 1)
            ops.append(("S", lo, lo + SCAN_SIZE))
    return ops, next_value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=sorted(PROFILES), default="leitura")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sessions", type=int, default=100000, help="número de sessões (padrão: 100000)")
    ap.add_argument("-o", "--output", default="-", help="arquivo de saída (padrão: saída padrão)")
    args = ap.parse_args()
    if args.sessions < 1:
        ap.error("--sessions deve ser >= 1")

    rng = random.Random(args.seed)
    weights = PROFILES[args.profile]["weights"]
    out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    try:
        out.write(f"# table-sync workload v1 profile={args.profile} seed={args.seed} sessions={args.sessions}\n")
        out.write(f"PARAMS keys={KEYS}\n")
        value = 1
        for sid in range(args.sessions):
            archetype = rng.choices(ARCHETYPES, weights)[0]
            ops, value = build_session(rng, archetype, value)
            out.write(f"SESSION {sid} " + " ".join(" ".join(str(x) for x in op) for op in ops) + "\n")
    finally:
        if out is not sys.stdout:
            out.close()


if __name__ == "__main__":
    main()
