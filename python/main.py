"""Programa principal.

Executa a carga com um pipeline concorrente: um produtor entrega as sessões, por
uma fila limitada, a um determinado número de threads; todas começam juntas por 
uma porta de largada e o tempo medido (``wall``) exclui a criação das threads.

O módulo define a fila limitada :class:`BoundedQueue`, usada na comunicação entre
o produtor e as threads trabalhadoras, e a função :func:`main`, que interpreta os
argumentos, executa a carga e grava o log.

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
"""Capacidade da fila entre o produtor e as threads trabalhadoras."""


class BoundedQueue:
    """Fila limitada: o produtor espera se cheia; as threads esperam se vazia.
    É segura para uso concorrente.

    Attributes:
        capacity: Quantidade máxima de itens simultâneos na fila.
        items: Itens atualmente enfileirados, do mais antigo ao mais recente.
        closed: Indica se a fila foi fechada para novas inserções.
        cv: Variável de condição que protege o estado da fila.
    """

    def __init__(self, capacity):
        """Cria uma fila vazia.

        Args:
            capacity: Quantidade máxima de itens simultâneos na fila.
        """
        self.capacity, self.items, self.closed = capacity, [], False
        self.cv = threading.Condition()

    def put(self, x):
        """Insere um item, esperando enquanto a fila estiver cheia.

        Args:
            x: Item a inserir.
        """
        with self.cv:
            while len(self.items) >= self.capacity:
                self.cv.wait()
            self.items.append(x)
            self.cv.notify_all()

    def close(self):
        """Fecha a fila, sinalizando que não haverá mais inserções."""
        with self.cv:
            self.closed = True
            self.cv.notify_all()

    def take(self):
        """Remove o próximo item, esperando enquanto a fila estiver vazia.

        Returns:
            O próximo item, ou ``None`` se a fila fechou e esvaziou.
        """
        with self.cv:
            while not self.items and not self.closed:
                self.cv.wait()
            if not self.items:
                return None
            x = self.items.pop(0)
            self.cv.notify_all()
            return x


def main():
    """Executa a carga com o serviço escolhido e grava o log da execução.

    Argumentos de linha de comando: 
    caminho da carga, ``--workers``, ``--impl`` (``coarse``, ``rw`` ou ``fine``) e ``-o``/``--output``. Se uma
    thread trabalhadora falhar, o processo é encerrado com código 1.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("workload")
    ap.add_argument("--workers", type=int, default=16, help="número de threads trabalhadoras")
    ap.add_argument("--impl", choices=sorted(IMPLEMENTATIONS), default="coarse")
    ap.add_argument("-o", "--output", default="events.log")
    args = ap.parse_args()

    params, sessions = load_workload(args.workload)
    service = IMPLEMENTATIONS[args.impl](params)
    service.start()

    queue = BoundedQueue(QUEUE_CAPACITY)
    gate = threading.Barrier(args.workers + 2)  # trabalhadoras + produtor + principal
    outs = [[] for _ in range(args.workers)]    # uma lista de registros por thread

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
