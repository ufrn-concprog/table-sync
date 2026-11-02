/**
 * @file    bounded_queue.h
 * @brief   Declara a fila limitada usada no pipeline concorrente.
 */
#ifndef BOUNDED_QUEUE_H
#define BOUNDED_QUEUE_H

#include <condition_variable>
using std::condition_variable;

#include <deque>
using std::deque;

#include <mutex>
using std::lock_guard;
using std::mutex;
using std::unique_lock;

#include "harness.h"
using harness::Session;

/** @brief Capacidade da fila limitada. */
#define QUEUE_CAPACITY 64

/**
 * @class  BoundedQueue
 * @brief  Fila limitada: o produtor espera se cheia; as threads esperam se vazia.
 */
class BoundedQueue {
public:
    /**
     * @brief Cria a fila com a capacidade especificada.
     * @param capacity Capacidade da fila.
     * @details A fila é limitada: o produtor espera se cheia; as threads esperam se vazia.
     */
    explicit BoundedQueue(size_t capacity) : capacity_(capacity) {}

    /**
     * @brief Insere uma sessão, esperando enquanto a fila estiver cheia.
     * @param s Sessão a inserir.
     */
    void put(const Session* s) {
        unique_lock<mutex> lock(mu_);
        cv_.wait(lock, [&] { return items_.size() < capacity_; });
        items_.push_back(s);
        cv_.notify_all();
    }

    /** @brief Fecha a fila: não haverá mais inserções. */
    void close() {
        lock_guard<mutex> lock(mu_);
        closed_ = true;
        cv_.notify_all();
    }

    /**
     * @brief Remove a próxima sessão, esperando enquanto a fila estiver vazia.
     * @return Próxima sessão, ou nullptr se a fila fechou e esvaziou.
     */
    const Session* take() {
        unique_lock<mutex> lock(mu_);
        cv_.wait(lock, [&] { return !items_.empty() || closed_; });
        if (items_.empty()) return nullptr;
        const Session* s = items_.front();
        items_.pop_front();
        cv_.notify_all();
        return s;
    }

private:
    mutex mu_;
    condition_variable cv_;
    deque<const Session*> items_;
    size_t capacity_;
    bool closed_ = false;
};

#endif  // BOUNDED_QUEUE_H
