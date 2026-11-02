/**
 * @file    rw_service.h
 * @brief   Declara a implementação da versão Rw da tabela concorrente.
 */
#ifndef RW_SERVICE_H
#define RW_SERVICE_H

#include <stdexcept>
using std::logic_error;

#include "harness.h"
using harness::Params;
using harness::Stats;
using harness::TableService;

/**
 * @class   RwTableService
 * @brief   Versão Rw da tabela concorrente.
 */
class RwTableService : public TableService {
public:
    /**
     * @brief Cria o serviço com os parâmetros da carga.
     * @param params Parâmetros da carga.
     */
    explicit RwTableService(const Params& params) : params_(params) {}

    /**
     * @brief Devolve o valor da chave
     * @param key Chave para a qual buscar o valor
     * @return Valor da chave, ou 0 se nenhum valor foi gravado nela.
     * @throws `logic_error`: este método ainda não foi implementado.
     */
    int get([[maybe_unused]] int key) override { 
        throw logic_error("TODO"); 
    }

    /**
     * @brief Grava um valor na chave
     * @param key Chave para a qual gravar o valor
     * @param value Valor a ser gravado
     * @throws `logic_error`: este método ainda não foi implementado.
     */
    void put([[maybe_unused]] int key, [[maybe_unused]] int value) override {
        throw logic_error("TODO");
    }

    /**
     * @brief Realiza uma varredura na tabela
     * @param lo Limite inferior da varredura
     * @param hi Limite superior da varredura
     * @return Quantidade de chaves com valor diferente de 0 no intervalo [lo, hi)
     * @throws `logic_error`: este método ainda não foi implementado.
     */
    int scan([[maybe_unused]] int lo, [[maybe_unused]] int hi) override { 
        throw logic_error("TODO"); 
    }

    /**
     * @brief Devolve as estatísticas do serviço
     * @return Stats contendo os contadores de chamadas de cada operação.
     * @throws `logic_error`: este método ainda não foi implementado.
     */
    Stats stats() override { 
        throw logic_error("TODO"); 
    }

private:
    /** @brief Cópia dos parâmetros usados pelo serviço. */
    Params params_;

    // TODO: implementar o estado compartilhado da tabela e os mecanismos de sincronização
};

#endif
