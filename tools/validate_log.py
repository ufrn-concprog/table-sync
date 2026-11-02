"""Validador do log de execução.

Uso:
    python3 tools/validate_log.py workloads/leitura-1.txt events.log

Lê a carga e o log produzido pela execução e verifica, apenas a partir dos
registros, se a tabela respeitou as regras. Cada operação é registrada com o
instante de início (s) e de término (e), medidos pelo relógio monotônico do
processo. O efeito real de uma operação ocorreu em algum instante dentro de
[s, e]; por isso, o validador só aponta violações inequívocas, isto é, aquelas
que nenhuma ordenação possível das operações concorrentes consegue explicar.

Formato do log (campos separados por tabulação):
    OP     <sessão> <índice> <tipo> <a> <b> <início-ns> <fim-ns> <resultado>
             G: a = chave, b = '-', resultado = valor lido
             P: a = chave, b = valor gravado, resultado = '-'
             S: a = lo, b = hi, resultado = quantidade contada
    STATS  gets=.. puts=.. scans=..
    RUN    workers=<n> wall_ns=<n>

Código de saída: 0 se não houver violações, 1 se houver, 2 para erro de uso ou formato.
"""

import argparse
import bisect
import collections
import sys

NEG_INF = float("-inf")


class Report:
    """Coleta violações por categoria, na ordem em que aparecem."""

    def __init__(self, max_print):
        self.max_print = max_print
        self.by_cat = collections.OrderedDict()

    def add(self, category, msg):
        self.by_cat.setdefault(category, []).append(msg)

    @property
    def total(self):
        return sum(len(v) for v in self.by_cat.values())

    def print(self):
        for cat, msgs in self.by_cat.items():
            print(f"[{cat}] {len(msgs)} violação(ões)")
            for m in msgs[: self.max_print]:
                print(f"    - {m}")
            if len(msgs) > self.max_print:
                print(f"    ... e mais {len(msgs) - self.max_print}")


def fail_format(msg):
    print(f"erro de formato: {msg}", file=sys.stderr)
    sys.exit(2)


def load_trace(path):
    """Devolve (keys, {sessão: [(tipo, a, b)]}) a partir do arquivo de carga."""
    keys, sessions = None, {}
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tok = line.split()
            if tok[0] == "PARAMS":
                kv = dict(t.split("=") for t in tok[1:])
                keys = int(kv["keys"])
            elif tok[0] == "SESSION":
                ops, i = [], 2
                while i < len(tok):
                    kind = tok[i]
                    if kind == "G":
                        ops.append(("G", int(tok[i + 1]), None)); i += 2
                    elif kind in ("P", "S"):
                        ops.append((kind, int(tok[i + 1]), int(tok[i + 2]))); i += 3
                    else:
                        fail_format(f"{path}:{n}: operação desconhecida '{kind}'")
                sessions[int(tok[1])] = ops
            else:
                fail_format(f"{path}:{n}: registro desconhecido '{tok[0]}'")
    if keys is None:
        fail_format(f"{path}: sem linha PARAMS")
    return keys, sessions


def load_log(path):
    """Devolve (operações, stats, run). Cada operação é uma tupla
    (sessão, índice, tipo, a, b, início, fim, resultado)."""
    ops, stats, run = [], None, None
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            c = line.rstrip("\n").split("\t")
            try:
                if c[0] == "OP":
                    res = None if c[8] == "-" else int(c[8])
                    b = None if c[5] == "-" else int(c[5])
                    ops.append((int(c[1]), int(c[2]), c[3], int(c[4]), b, int(c[6]), int(c[7]), res))
                elif c[0] == "STATS":
                    stats = {k: int(v) for k, v in (t.split("=") for t in c[1:])}
                elif c[0] == "RUN":
                    run = {k: int(v) for k, v in (t.split("=") for t in c[1:])}
                elif c[0].strip():
                    fail_format(f"{path}:{n}: tipo de linha desconhecido '{c[0]}'")
            except (IndexError, ValueError):
                fail_format(f"{path}:{n}: linha mal formada")
    return ops, stats, run


def validate(keys, sessions, ops, stats, run, rep):
    expected = sum(len(v) for v in sessions.values())

    # ---- completude: cada operação da carga aparece exatamente uma vez, com os mesmos argumentos
    seen = {}
    for (sid, idx, kind, a, b, s, e, res) in ops:
        key = (sid, idx)
        if key in seen:
            rep.add("completude", f"sessão {sid}, operação {idx} registrada mais de uma vez")
            continue
        seen[key] = True
        script = sessions.get(sid)
        if script is None or idx >= len(script):
            rep.add("completude", f"sessão {sid}, operação {idx} não existe na carga")
        elif script[idx] != (kind, a, b if kind != "G" else None):
            rep.add("completude", f"sessão {sid}, operação {idx}: registro diferente da carga")
        if e < s:
            rep.add("completude", f"sessão {sid}, operação {idx}: fim anterior ao início")
    missing = expected - len(seen)
    if missing > 0:
        rep.add("completude", f"{missing} operação(ões) da carga sem registro")
    if run is None:
        rep.add("completude", "log sem linha RUN: a execução travou ou foi interrompida")
    if stats is None:
        rep.add("completude", "log sem linha STATS")

    # ---- índices por chave: puts (intervalos) e valor -> put
    puts_by_key = collections.defaultdict(list)       # chave -> [(início, fim, valor)]
    put_of_value = {}                                  # valor -> (chave, início, fim)
    for (sid, idx, kind, a, b, s, e, res) in ops:
        if kind == "P":
            puts_by_key[a].append((s, e, b))
            put_of_value[b] = (a, s, e)
    # para detectar obsolescência: por chave, puts ordenados por fim e máximo prefixo dos inícios
    ends, prefmax = {}, {}
    for k, lst in puts_by_key.items():
        lst.sort(key=lambda t: t[1])
        ends[k] = [t[1] for t in lst]
        m, pm = NEG_INF, []
        for t in lst:
            m = max(m, t[0])
            pm.append(m)
        prefmax[k] = pm
    first_start = {k: min(t[0] for t in v) for k, v in puts_by_key.items()}
    first_end = {k: min(t[1] for t in v) for k, v in puts_by_key.items()}

    # ---- valor-invalido / valor-obsoleto (get)
    for (sid, idx, kind, a, b, s, e, v) in ops:
        if kind != "G":
            continue
        if v is None:
            rep.add("valor-invalido", f"sessão {sid}, get({a}) sem valor registrado")
            continue
        if v == 0:
            p_end = NEG_INF
        else:
            info = put_of_value.get(v)
            if info is None or info[0] != a:
                rep.add("valor-invalido", f"sessão {sid}, get({a}) devolveu {v}, que nunca foi gravado nessa chave")
                continue
            if info[1] > e:
                rep.add("valor-invalido", f"sessão {sid}, get({a}) devolveu {v} antes de o put começar")
                continue
            p_end = info[2]
        # existe put q concluído antes do get e estritamente depois do put que gravou v?
        if a in ends:
            n = bisect.bisect_left(ends[a], s)          # puts com fim < início do get
            if n > 0 and prefmax[a][n - 1] > p_end:
                rep.add("valor-obsoleto",
                        f"sessão {sid}, get({a}) devolveu {v}, mas um put posterior já havia terminado antes do início do get")

    # ---- varredura (scan)
    n_scans = 0
    for (sid, idx, kind, a, b, s, e, c) in ops:
        if kind != "S":
            continue
        n_scans += 1
        lo, hi = a, b
        lower = sum(1 for k in range(lo, hi) if k in first_end and first_end[k] < s)
        upper = sum(1 for k in range(lo, hi) if k in first_start and first_start[k] <= e)
        if c is None or not (lower <= c <= upper):
            rep.add("varredura", f"sessão {sid}, scan({lo},{hi}) devolveu {c}; o intervalo possível era [{lower}, {upper}]")

    # ---- contadores
    cnt = collections.Counter(op[2] for op in ops)
    if stats is not None:
        for name, kind in (("gets", "G"), ("puts", "P"), ("scans", "S")):
            if stats.get(name) != cnt[kind]:
                rep.add("contadores", f"stats().{name} = {stats.get(name)}, mas o log registra {cnt[kind]}")

    return dict(sessions=len(sessions), ops=len(ops), expected=expected,
                gets=cnt["G"], puts=cnt["P"], scans=cnt["S"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace", help="arquivo de carga (workload)")
    ap.add_argument("log", help="log de eventos produzido pela execução")
    ap.add_argument("--max-print", type=int, default=5, help="máximo de exemplos por categoria")
    args = ap.parse_args()
    try:
        keys, sessions = load_trace(args.trace)
        ops, stats, run = load_log(args.log)
    except OSError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    rep = Report(args.max_print)
    sm = validate(keys, sessions, ops, stats, run, rep)
    print(f"sessões: {sm['sessions']}  operações registradas: {sm['ops']}/{sm['expected']}  "
          f"gets: {sm['gets']}  puts: {sm['puts']}  scans: {sm['scans']}")
    if run and run.get("wall_ns", 0) > 0:
        wall = run["wall_ns"] / 1e9
        print(f"threads: {run.get('workers', '?')}  tempo: {wall:.3f} s  vazão: "
              f"{sm['ops'] / wall:.0f} ops/s, {sm['sessions'] / wall:.0f} sessões/s")
    if rep.total == 0:
        print("RESULTADO: OK (nenhuma violação encontrada)")
        return 0
    rep.print()
    print(f"RESULTADO: FALHA ({rep.total} violações em {len(rep.by_cat)} categoria(s))")
    return 1


if __name__ == "__main__":
    sys.exit(main())
