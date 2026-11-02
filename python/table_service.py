"""Implementação das três versões da tabela concorrente.

- CoarseTableService : um único lock protege toda a tabela.
- RwTableService     : um único lock de leitura e escrita protege toda a tabela.
- FineTableService   : a tabela é dividida em partições com sincronização independente.

O módulo expõe o dicionário :data:`IMPLEMENTATIONS`, que associa o nome de cada
versão à sua classe, usado pela opção ``--impl`` de ``main.py``.
"""
from harness import TableService


class CoarseTableService(TableService):
    """Serviço que protege toda a tabela com um único mecanismo de exclusão mútua.

    Todas as operações são serializadas pelo mesmo lock. Uma chave sem valor
    gravado é lida como ``0``; ``scan`` conta valores diferentes de zero no
    intervalo semiaberto ``[lo, hi)``.

    Args:
        params: Parâmetros da carga (:class:`harness.Params`).
    """

    def __init__(self, params):
        """Cria o serviço.

        Args:
            params: Parâmetros da carga (:class:`harness.Params`).
        """
        self.params = params
        # TODO: estado compartilhado e mecanismos de sincronização

    def get(self, key):
        """Lê o valor de uma chave.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
        Returns:
            Valor gravado na chave, ou ``0`` se ainda não houver valor.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def put(self, key, value):
        """Grava um valor em uma chave.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
            value: Valor positivo a gravar.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def scan(self, lo, hi):
        """Conta as chaves preenchidas em um intervalo.

        Args:
            lo: Limite inferior inclusivo do intervalo.
            hi: Limite superior exclusivo do intervalo.
        Returns:
            Quantidade de chaves do intervalo com valor diferente de ``0``.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def stats(self):
        """Obtém os contadores de operações do serviço.

        Returns:
            Dicionário com as chaves ``gets``, ``puts`` e ``scans`` e suas
            respectivas quantidades de operações.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")


class RwTableService(TableService):
    """Serviço que usa um lock de leitura e escrita para proteger a tabela.

    Operações de leitura podem compartilhar o acesso, enquanto gravações
    exigem acesso exclusivo. Uma chave sem valor gravado é lida como ``0``;
    ``scan`` conta valores diferentes de zero no intervalo semiaberto
    ``[lo, hi)``.

    Args:
        params: Parâmetros da carga (:class:`harness.Params`).
    """

    def __init__(self, params):
        """Cria o serviço.

        Args:
            params: Parâmetros da carga (:class:`harness.Params`).
        """
        self.params = params
        # TODO

    def get(self, key):
        """Lê o valor de uma chave.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
        Returns:
            Valor gravado na chave, ou ``0`` se ainda não houver valor.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def put(self, key, value):
        """Grava um valor em uma chave.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
            value: Valor positivo a gravar.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def scan(self, lo, hi):
        """Conta as chaves preenchidas em um intervalo.

        Args:
            lo: Limite inferior inclusivo do intervalo.
            hi: Limite superior exclusivo do intervalo.
        Returns:
            Quantidade de chaves do intervalo com valor diferente de ``0``.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def stats(self):
        """Obtém os contadores de operações do serviço.

        Returns:
            Dicionário com as chaves ``gets``, ``puts`` e ``scans`` e suas
            respectivas quantidades de operações.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")


class FineTableService(TableService):
    """Serviço que divide a tabela em partições sincronizadas de forma independente.

    Operações em partições distintas podem ocorrer em paralelo. Uma chave sem
    valor gravado é lida como ``0``; ``scan`` conta valores diferentes de zero
    no intervalo semiaberto ``[lo, hi)``.

    Args:
        params: Parâmetros da carga (:class:`harness.Params`).
    """

    def __init__(self, params):
        """Cria o serviço.

        Args:
            params: Parâmetros da carga (:class:`harness.Params`).
        """
        self.params = params
        # TODO

    def get(self, key):
        """Lê o valor de uma chave.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
        Returns:
            Valor gravado na chave, ou ``0`` se ainda não houver valor.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def put(self, key, value):
        """Grava um valor em uma chave.

        Args:
            key: Chave, de ``0`` a ``keys-1``.
            value: Valor positivo a gravar.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def scan(self, lo, hi):
        """Conta as chaves preenchidas em um intervalo.

        Args:
            lo: Limite inferior inclusivo do intervalo.
            hi: Limite superior exclusivo do intervalo.
        Returns:
            Quantidade de chaves do intervalo com valor diferente de ``0``.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")

    def stats(self):
        """Obtém os contadores de operações do serviço.

        Returns:
            Dicionário com as chaves ``gets``, ``puts`` e ``scans`` e suas
            respectivas quantidades de operações.
        Raise:
            NotImplementedError: este método ainda não foi implementado.
        """
        raise NotImplementedError("TODO")


IMPLEMENTATIONS = {
    "coarse": CoarseTableService,
    "rw": RwTableService,
    "fine": FineTableService,
}
"""Versões disponíveis do serviço, indexadas pelo valor de ``--impl``."""
