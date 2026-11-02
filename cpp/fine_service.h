/**
 * @file    fine_service.h
 * @brief   ARQUIVO DOS ALUNOS — versão Fine da tabela concorrente.
 * @details Leia 'Descrição do problema' e 'Implementação' no README antes de começar e
 *          justifique no relatório cada escolha de sincronização.
 */
#ifndef FINE_SERVICE_H
#define FINE_SERVICE_H

#include <stdexcept>

#include "harness.h"

/** @brief Versão Fine da tabela concorrente. */
class FineTableService : public harness::TableService {
public:
    /** @brief Cria o serviço com os parâmetros da carga. */
    explicit FineTableService(const harness::Params& params) : params_(params) {}

    int get([[maybe_unused]] int key) override { throw std::logic_error("TODO"); }

    void put([[maybe_unused]] int key, [[maybe_unused]] int value) override { throw std::logic_error("TODO"); }

    int scan([[maybe_unused]] int lo, [[maybe_unused]] int hi) override { throw std::logic_error("TODO"); }

    harness::Stats stats() override { throw std::logic_error("TODO"); }

private:
    /** @brief Cópia dos parâmetros usados pelo serviço. */
    harness::Params params_;

    // TODO: implementar o estado compartilhado e os mecanismos de sincronização
};

#endif
