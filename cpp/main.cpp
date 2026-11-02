/**
 * @file    main.cpp
 * @brief   ARQUIVO FORNECIDO — programa principal (não modificar).
 * @details Executa a carga com um pipeline concorrente: um produtor entrega as sessões, por
 *          uma fila limitada, às --workers threads; todas começam juntas por uma porta de
 *          largada e o tempo medido (wall) exclui a criação das threads.
 *
 *          Uso: ./table_sync workloads/leitura-1.txt --workers 16 --impl rw -o events.log
 */
#include <barrier>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "coarse_service.h"
#include "fine_service.h"
#include "harness.h"
#include "rw_service.h"

namespace {

constexpr size_t QUEUE_CAPACITY = 64;

/** Fila limitada: o produtor espera se cheia; as threads esperam se vazia. */
class BoundedQueue {
public:
    explicit BoundedQueue(size_t capacity) : capacity_(capacity) {}

    void put(const harness::Session* s) {
        std::unique_lock lock(mu_);
        cv_.wait(lock, [&] { return items_.size() < capacity_; });
        items_.push_back(s);
        cv_.notify_all();
    }

    void close() {
        std::lock_guard lock(mu_);
        closed_ = true;
        cv_.notify_all();
    }

    /** Próxima sessão, ou nullptr se a fila fechou e esvaziou. */
    const harness::Session* take() {
        std::unique_lock lock(mu_);
        cv_.wait(lock, [&] { return !items_.empty() || closed_; });
        if (items_.empty()) return nullptr;
        const harness::Session* s = items_.front();
        items_.pop_front();
        cv_.notify_all();
        return s;
    }

private:
    std::mutex mu_;
    std::condition_variable cv_;
    std::deque<const harness::Session*> items_;
    size_t capacity_;
    bool closed_ = false;
};

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "uso: %s <carga> [--workers N] [--impl coarse|rw|fine] [-o arquivo]\n", argv[0]);
        return 1;
    }
    std::string workload_path = argv[1], impl = "coarse", output = "events.log";
    int workers = 16;
    for (int i = 2; i < argc; ++i) {
        std::string a = argv[i];
        if ((a == "--workers" || a == "-w") && i + 1 < argc) workers = std::atoi(argv[++i]);
        else if (a == "--impl" && i + 1 < argc) impl = argv[++i];
        else if (a == "-o" && i + 1 < argc) output = argv[++i];
        else { std::fprintf(stderr, "argumento desconhecido: %s\n", a.c_str()); return 1; }
    }

    harness::Workload wl = harness::load_workload(workload_path);
    std::unique_ptr<harness::TableService> service;
    if (impl == "coarse") service = std::make_unique<CoarseTableService>(wl.params);
    else if (impl == "rw") service = std::make_unique<RwTableService>(wl.params);
    else if (impl == "fine") service = std::make_unique<FineTableService>(wl.params);
    else { std::fprintf(stderr, "--impl deve ser coarse, rw ou fine\n"); return 1; }
    service->start();

    BoundedQueue queue(QUEUE_CAPACITY);
    std::barrier gate(workers + 2);                              // trabalhadoras + produtor + principal
    std::vector<std::vector<harness::Rec>> outs(workers);       // um vetor de registros por thread
    std::vector<std::thread> threads;
    for (int i = 0; i < workers; ++i) {
        threads.emplace_back([&, i] {
            harness::SessionRunner runner(*service, outs[i]);
            gate.arrive_and_wait();
            while (const harness::Session* s = queue.take()) runner.run(*s);
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
    std::printf("%zu sessoes em %.3f s -> %s\n", wl.sessions.size(), wall / 1e9, output.c_str());
}
