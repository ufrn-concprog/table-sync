"""Infraestrutura compartilhada de execução da tabela concorrente.

O módulo fornece tipos para representar parâmetros, operações e sessões;
carrega arquivos de carga; executa as operações das sessões sobre o serviço e
grava o log consumido por ``tools/validate_log.py``.
"""

import time
from dataclasses import dataclass

_ORIGIN = time.monotonic_ns()


def now_ns():
    """Retorna o tempo monotônico decorrido desde o início do processo.

    Returns:
        Tempo, em nanossegundos, medido por um relógio monotônico cuja origem é
        o momento em que este módulo foi importado.
    """
    return time.monotonic_ns() - _ORIGIN


@dataclass(frozen=True)
class Params:
    """Parâmetros imutáveis da carga.

    Attributes:
        keys: Quantidade de chaves; as chaves são os inteiros de ``0`` a ``keys-1``.
    """
    keys: int


@dataclass(frozen=True)
class Op:
    """Operação individual de uma sessão.

    Attributes:
        kind: ``G`` (get), ``P`` (put) ou ``S`` (scan).
        a: Chave (``G`` e ``P``) ou limite inferior ``lo`` (``S``).
        b: Valor (``P``) ou limite superior ``hi``, exclusivo (``S``); ``0`` em ``G``.
    """
    kind: str
    a: int
    b: int = 0


@dataclass(frozen=True)
class Session:
    """Sessão de operações.

    Attributes:
        id: Identificador da sessão.
        ops: Tupla imutável de objetos :class:`Op`, na ordem de execução.
    """
    id: int
    ops: tuple


def load_workload(path):
    """Carrega parâmetros e sessões de um arquivo de carga.

    Args:
        path: Caminho do arquivo de carga.
    Returns:
        Tupla ``(params, sessions)`` com um :class:`Params` e 
        uma lista de :class:`Session`.
    Raises:
        OSError: Se o arquivo não puder ser lido.
        ValueError: Se faltar a linha ``PARAMS`` ou houver operação desconhecida.
    """
    params, sessions = None, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tok = line.split()
            if tok[0] == "PARAMS":
                kv = dict(t.split("=") for t in tok[1:])
                params = Params(keys=int(kv["keys"]))
            elif tok[0] == "SESSION":
                ops, i = [], 2
                while i < len(tok):
                    kind = tok[i]
                    if kind == "G":
                        ops.append(Op("G", int(tok[i + 1])))
                        i += 2
                    elif kind in ("P", "S"):
                        ops.append(Op(kind, int(tok[i + 1]), int(tok[i + 2])))
                        i += 3
                    else:
                        raise ValueError(f"operação desconhecida: {kind}")
                sessions.append(Session(int(tok[1]), tuple(ops)))
    if params is None:
        raise ValueError("carga sem linha PARAMS")
    return params, sessions


class TableService:
    """Contrato das implementações da tabela concorrente.

    Todos os métodos podem ser chamados concorrentemente por várias threads.
    """

    def start(self):
        """Prepara o serviço; é chamado uma vez antes de qualquer operação."""

    def close(self):
        """Encerra o serviço; é chamado uma vez depois da última operação.
        Threads auxiliares, se houver, devem ser encerradas aqui.
        """

    def get(self, key):
        """Devolve o valor da chave, ou ``0`` se nenhum valor foi gravado nela.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
        Returns:
            Valor da chave, ou ``0`` se nenhum valor foi gravado nela.
        Raises:
            NotImplementedError: Este método ainda não está implementado.
        """
        raise NotImplementedError

    def put(self, key, value):
        """Grava ``value`` na chave. Depois do retorno, todo ``get`` que comece em
        seguida devolve ``value`` ou um valor gravado depois dele.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
            value: Valor positivo, único em toda a carga.
        Raises:
            NotImplementedError: Este método ainda não está implementado.
        """
        raise NotImplementedError

    def scan(self, lo, hi):
        """Devolve quantas chaves de ``lo`` até ``hi-1`` têm valor diferente de ``0``.

        Args:
            lo: Limite inferior (inclusivo) do intervalo de chaves.
            hi: Limite superior (exclusivo) do intervalo de chaves.
        Returns:
            Quantidade de chaves do intervalo com valor diferente de ``0``.
        Raises:
            NotImplementedError: Este método ainda não está implementado.
        """
        raise NotImplementedError

    def stats(self):
        """Retorna os contadores de operações realizadas até o momento.

        Returns:
            Dicionário com as chaves ``gets``, ``puts`` e ``scans``, cada uma
            com a quantidade de chamadas da operação correspondente.
        Raises:
            NotImplementedError: Este método ainda não está implementado.
        """
        raise NotImplementedError


class SessionRunner:
    """Executa em ordem as operações de uma sessão e registra seus resultados.

    Cada thread deve ter sua própria instância e sua própria lista de saída.
    """

    def __init__(self, service, out):
        """Cria um executor associado a um serviço e a uma lista de saída.

        Args:
            service: Serviço usado para executar as operações.
            out: Lista que receberá os registros produzidos por este executor.
                Cada registro é uma tupla
                ``(sessão, índice, tipo, a, b, início, fim, resultado)``.
        """
        self._svc = service
        self._out = out

    def run(self, session):
        """Executa sequencialmente as operações de uma sessão e registra cada uma.

        Args:
            session: Sessão cujas operações serão executadas.
        Raises:
            ValueError: Se a sessão contiver uma operação de tipo desconhecido.
        """
        sid = session.id
        for idx, op in enumerate(session.ops):
            k = op.kind
            s = now_ns()
            if k == "G":
                res = self._svc.get(op.a)
                b = "-"
            elif k == "P":
                self._svc.put(op.a, op.b)
                res, b = "-", op.b
            elif k == "S":
                res = self._svc.scan(op.a, op.b)
                b = op.b
            else:
                raise ValueError(f"operação desconhecida: {k}")
            e = now_ns()
            self._out.append((sid, idx, k, op.a, b, s, e, res))


def write_log(path, outs, stats, workers, wall_ns):
    """Grava operações, estatísticas e metadados da execução.

    Args:
        path: Caminho do arquivo de log.
        outs: Listas de registros produzidas pelos executores das threads.
        stats: Dicionário de contadores finais do serviço.
        workers: Quantidade de threads.
        wall_ns: Duração total da execução, em nanossegundos.
    """
    with open(path, "w", encoding="utf-8") as f:
        for out in outs:
            for (sid, idx, k, a, b, s, e, res) in out:
                f.write(f"OP\t{sid}\t{idx}\t{k}\t{a}\t{b}\t{s}\t{e}\t{res}\n")
        f.write("STATS\t" + "\t".join(f"{k}={v}" for k, v in stats.items()) + "\n")
        f.write(f"RUN\tworkers={workers}\twall_ns={wall_ns}\n")
