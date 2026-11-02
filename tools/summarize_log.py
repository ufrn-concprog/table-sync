"""Resume um log de execução.

Uso:
    python3 tools/summarize_log.py events.log

Mostra o tempo total e a vazão (a partir da linha RUN) e, para cada tipo de
operação (G = get, P = put, S = scan), a quantidade de chamadas e a distribuição
da duração (fim - início), em milissegundos: média, mediana (p50), p95, p99 e máximo.

O log usa campos separados por tabulação. Registros ``OP`` fornecem as durações
das operações; um registro ``RUN`` opcional fornece os dados agregados da
execução e das sessões concluídas.
"""

import collections
import math
import sys


def percentile(sorted_vals, p):
    """Calcula um percentil pela regra da classificação mais próxima.

    Args:
        sorted_vals: Valores em ordem crescente. A sequência deve ser não vazia.
        p: Percentil desejado. Valores fora de ``0`` a ``100`` são limitados
            ao mínimo ou ao máximo da sequência.

    Returns:
        O elemento na posição correspondente, limitado aos extremos da
        sequência para percentis fora desse intervalo.
    """
    k = max(0, min(len(sorted_vals) - 1, math.ceil(p / 100 * len(sorted_vals)) - 1))
    return sorted_vals[k]


def main():
    """Lê um log e imprime estatísticas de duração e vazão.

    Exatamente um argumento é fornecido, que é o caminho do arquivo de log. 
    Se a linha ``RUN`` estiver ausente, ainda apresenta as estatísticas por 
    operação e informa que o log pode estar incompleto.

    Returns:
        Código de saída ``0`` em caso de uso válido ou ``2`` se faltar ou
        sobrar argumento.
    """
    if len(sys.argv) != 2:
        print("uso: python3 tools/summarize_log.py events.log", file=sys.stderr)
        return 2
    durations = collections.defaultdict(list)
    run, sessions = None, set()
    with open(sys.argv[1], encoding="utf-8") as f:
        for line in f:
            c = line.rstrip("\n").split("\t")
            if c[0] == "OP":
                durations[c[3]].append((int(c[7]) - int(c[6])) / 1e6)
                sessions.add(c[1])
            elif c[0] == "RUN":
                run = {k: int(v) for k, v in (t.split("=") for t in c[1:])}
    total_ops = sum(len(v) for v in durations.values())
    if run:
        wall = run["wall_ns"] / 1e9
        print(f"threads: {run['workers']}  tempo: {wall:.3f} s  sessões: {len(sessions)}  "
              f"vazão: {len(sessions) / wall:.1f} sessões/s, {total_ops / wall:.0f} ops/s")
    else:
        print("aviso: log sem linha RUN (execução incompleta)")
    print()
    print(f"{'op':<4}{'n':>9}{'média':>10}{'p50':>10}{'p95':>10}{'p99':>10}{'máx':>10}   (ms)")
    for kind in sorted(durations):
        v = sorted(durations[kind])
        print(f"{kind:<4}{len(v):>9}{sum(v) / len(v):>10.4f}{percentile(v, 50):>10.4f}"
              f"{percentile(v, 95):>10.4f}{percentile(v, 99):>10.4f}{v[-1]:>10.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
