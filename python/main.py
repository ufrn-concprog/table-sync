"""ARQUIVO FORNECIDO — programa principal (NÃO MODIFICAR).

Executa a carga com um pipeline concorrente: um produtor entrega as sessões, por
uma fila limitada, a ``--workers`` threads; todas começam juntas por uma porta
de largada e o tempo medido (``wall``) exclui a criação das threads.

Uso:
    python3 python/main.py workloads/leitura-1.txt --workers 16 --impl rw -o events.log
    python3 tools/validate_log.py workloads/leitura-1.txt events.log
"""
import argparse
import os
import threading
import traceback

from harness import SessionRunner, load_workload, now_ns, write_log
from table_service import IMPLEMENTATIONS

QUEUE_CAPACITY = 64


class BoundedQueue:
    """Fila limitada: o produtor espera se cheia; as threads esperam se vazia."""

    def __init__(self, capacity):
        self.capacity, self.items, self.closed = capacity, [], False
        self.cv = threading.Condition()

    def put(self, x):
        with self.cv:
            while len(self.items) >= self.capacity:
                self.cv.wait()
            self.items.append(x)
            self.cv.notify_all()

    def close(self):
        with self.cv:
            self.closed = True
            self.cv.notify_all()

    def take(self):
        """Próximo item, ou None se a fila fechou e esvaziou."""
        with self.cv:
            while not self.items and not self.closed:
                self.cv.wait()
            if not self.items:
                return None
            x = self.items.pop(0)
            self.cv.notify_all()
            return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workload")
    ap.add_argument("-w", "--workers", type=int, default=16, help="número de threads trabalhadoras")
    ap.add_argument("--impl", choices=sorted(IMPLEMENTATIONS), default="coarse")
    ap.add_argument("-o", "--output", default="events.log")
    args = ap.parse_args()

    params, sessions = load_workload(args.workload)
    service = IMPLEMENTATIONS[args.impl](params)
    service.start()

    queue = BoundedQueue(QUEUE_CAPACITY)
    gate = threading.Barrier(args.workers + 2)       # trabalhadoras + produtor + principal
    outs = [[] for _ in range(args.workers)]         # uma lista de registros por thread

    def worker(i):
        try:
            runner = SessionRunner(service, outs[i])
            gate.wait()
            while (session := queue.take()) is not None:
                runner.run(session)
        except BaseException:                 # falha: encerra, em vez de travar o produtor
            traceback.print_exc()
            os._exit(1)

    def producer():
        gate.wait()
        for session in sessions:
            queue.put(session)
        queue.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.workers)]
    threads.append(threading.Thread(target=producer))
    for t in threads:
        t.start()
    gate.wait()
    t0 = now_ns()
    for t in threads:
        t.join()
    wall = now_ns() - t0

    service.close()
    write_log(args.output, outs, service.stats(), args.workers, wall)
    print(f"{len(sessions)} sessoes em {wall / 1e9:.3f} s -> {args.output}")


if __name__ == "__main__":
    main()
