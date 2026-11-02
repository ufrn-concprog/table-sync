/**
 * @file    main.cpp
 * @brief   Ponto de entrada da aplicação.
 * @details Executa a carga com um pipeline concorrente: um produtor entrega as
 *          sessões, por uma fila limitada, às threads; todas começam juntas
 *          por uma porta de largada e o tempo medido (wall) exclui a criação das
 *          threads.
 */

#include <barrier>
using std::barrier;

#include <cstdio>
using std::fprintf;
using std::printf;

#include <cstdlib>
using std::atoi;

#include <memory>
using std::make_unique;
using std::unique_ptr;

#include <string>
using std::string;

#include <thread>
using std::thread;

#include <vector>
using std::vector;

#include "bounded_queue.h"
#include "coarse_service.h"
#include "fine_service.h"
#include "harness.h"

#include "rw_service.h"
using harness::Session;
using harness::SessionRecord;
using harness::SessionRunner;
using harness::TableService;
using harness::Workload;

/**
 * @brief Função principal da aplicação.
 * @param argc Número de argumentos de linha de comando.
 * @param argv Vetor de argumentos de linha de comando.
 * @return 0 se a execução foi bem-sucedida; 1 caso contrário.
 */
int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "uso: %s <carga> [--workers N] [--impl coarse|rw|fine] [-o arquivo]\n", argv[0]);
        return 1;
    }
    string workload_path = argv[1], impl = "coarse", output = "events.log";
    int workers = 16;
    for (int i = 2; i < argc; ++i) {
        string a = argv[i];
        if ((a == "--workers" || a == "-w") && i + 1 < argc) workers = atoi(argv[++i]);
        else if (a == "--impl" && i + 1 < argc) impl = argv[++i];
        else if (a == "-o" && i + 1 < argc) output = argv[++i];
        else { fprintf(stderr, "argumento desconhecido: %s\n", a.c_str()); return 1; }
    }

    Workload wl = harness::load_workload(workload_path);
    unique_ptr<TableService> service;
    if (impl == "coarse") service = make_unique<CoarseTableService>(wl.params);
    else if (impl == "rw") service = make_unique<RwTableService>(wl.params);
    else if (impl == "fine") service = make_unique<FineTableService>(wl.params);
    else { fprintf(stderr, "--impl deve ser coarse, rw ou fine\n"); return 1; }
    service->start();

    BoundedQueue queue(QUEUE_CAPACITY);
    std::barrier gate(workers + 2);                         // trabalhadoras + produtor + principal
    vector<vector<SessionRecord>> outs(workers);   // um vetor de registros por thread
    vector<thread> threads;
    for (int i = 0; i < workers; ++i) {
        threads.emplace_back([&, i] {
            SessionRunner runner(*service, outs[i]);
            gate.arrive_and_wait();
            while (const Session* s = queue.take()) runner.run(*s);
        });
    }
    threads.emplace_back([&] {                                   // produtor
        gate.arrive_and_wait();
        for (const auto& s : wl.sessions) queue.put(&s);
        queue.close();
    });
    gate.arrive_and_wait();
    int64_t t0 = harness::now_ns();
    for (auto& t : threads) t.join();
    int64_t wall = harness::now_ns() - t0;

    service->close();
    harness::write_log(output, outs, service->stats(), workers, wall);
    printf("%zu sessoes em %.3f s -> %s\n", wl.sessions.size(), wall / 1e9, output.c_str());
}
