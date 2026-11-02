"""ARQUIVO DOS ALUNOS — implemente as três versões da tabela concorrente.

CoarseTableService : um único lock protege toda a tabela.
RwTableService     : um único lock de leitura e escrita protege toda a tabela.
FineTableService   : a tabela é dividida em partições com sincronização independente.

Leia a seção 'Descrição do problema' e 'Implementação' do README antes de começar.
Justifique no relatório cada escolha.
"""
from harness import TableService


class CoarseTableService(TableService):
    """Versão grossa: um único mecanismo de exclusão mútua para toda a tabela."""

    def __init__(self, params):
        self.params = params
        # TODO: estado compartilhado e mecanismos de sincronização

    def get(self, key):
        raise NotImplementedError("TODO")

    def put(self, key, value):
        raise NotImplementedError("TODO")

    def scan(self, lo, hi):
        raise NotImplementedError("TODO")

    def stats(self):
        raise NotImplementedError("TODO")


class RwTableService(TableService):
    """Versão com lock de leitura e escrita (em Python, construa o RWLock)."""

    def __init__(self, params):
        self.params = params
        # TODO

    def get(self, key):
        raise NotImplementedError("TODO")

    def put(self, key, value):
        raise NotImplementedError("TODO")

    def scan(self, lo, hi):
        raise NotImplementedError("TODO")

    def stats(self):
        raise NotImplementedError("TODO")


class FineTableService(TableService):
    """Versão fina: partições com sincronização independente."""

    def __init__(self, params):
        self.params = params
        # TODO

    def get(self, key):
        raise NotImplementedError("TODO")

    def put(self, key, value):
        raise NotImplementedError("TODO")

    def scan(self, lo, hi):
        raise NotImplementedError("TODO")

    def stats(self):
        raise NotImplementedError("TODO")


IMPLEMENTATIONS = {
    "coarse": CoarseTableService,
    "rw": RwTableService,
    "fine": FineTableService,
}
