/**
 * @file    harness.h
 * @brief   Infraestrutura de execução da tabela concorrente.
 * @details Fornece leitura da carga, relógio, executor de sessões e gravação do log
 *          consumido pelo validador. ESTE ARQUIVO NÃO DEVE SER MODIFICADO.
 */
#ifndef HARNESS_H
#define HARNESS_H

#include <chrono>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace harness {

/** @brief Retorna o tempo monotônico decorrido desde o início do processo, em nanossegundos. */
inline int64_t now_ns() {
    static const auto origin = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::steady_clock::now() - origin).count();
}

/** @brief Parâmetros da carga. */
struct Params {
    /** @brief Quantidade de chaves; as chaves são os inteiros de 0 a keys-1. */
    int keys = 0;
};

/** @brief Operação individual de uma sessão. */
struct Op {
    char kind;   ///< 'G' (get), 'P' (put) ou 'S' (scan)
    int a;       ///< chave (G e P) ou limite inferior lo (S)
    int b;       ///< valor (P) ou limite superior hi, exclusivo (S); 0 em G
};

/** @brief Sessão de operações de um cliente. */
struct Session {
    int id;                 ///< identificador da sessão
    std::vector<Op> ops;    ///< operações, na ordem de execução
};

/** @brief Carga completa: parâmetros e sessões. */
struct Workload {
    Params params;
    std::vector<Session> sessions;
};

/** @brief Contadores agregados do serviço. */
struct Stats {
    int64_t gets, puts, scans;
};

/** @brief Registro de uma operação executada. */
struct Rec {
    int session, idx;
    char kind;
    int a, b;
    int64_t start, end;
    int result;   ///< valor devolvido (G e S); sem significado em P
};

/**
 * @brief Lê os parâmetros e as sessões de um arquivo de carga.
 * @throws std::runtime_error se o arquivo não puder ser lido ou não tiver a linha PARAMS.
 */
inline Workload load_workload(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("não foi possível abrir " + path);
    Workload wl;
    bool has_params = false;
    std::string line;
    while (std::getline(in, line)) {
        std::istringstream ss(line);
        std::string tok;
        if (!(ss >> tok) || tok[0] == '#') continue;
        if (tok == "PARAMS") {
            while (ss >> tok) {
                auto eq = tok.find('=');
                if (tok.substr(0, eq) == "keys") { wl.params.keys = std::stoi(tok.substr(eq + 1)); has_params = true; }
            }
        } else if (tok == "SESSION") {
            Session s;
            ss >> s.id;
            std::string k;
            while (ss >> k) {
                Op op{k[0], 0, 0};
                if (k == "G") ss >> op.a;
                else if (k == "P" || k == "S") ss >> op.a >> op.b;
                else throw std::runtime_error("operação desconhecida: " + k);
                s.ops.push_back(op);
            }
            wl.sessions.push_back(std::move(s));
        }
    }
    if (!has_params) throw std::runtime_error("carga sem linha PARAMS");
    return wl;
}

/**
 * @brief Contrato das implementações da tabela concorrente.
 * @details Todos os métodos podem ser chamados concorrentemente por várias threads.
 */
class TableService {
public:
    virtual ~TableService() = default;

    /** @brief Chamado uma vez antes de qualquer operação. */
    virtual void start() {}

    /** @brief Chamado uma vez depois da última operação; encerre aqui threads auxiliares, se houver. */
    virtual void close() {}

    /** @brief Devolve o valor da chave, ou 0 se nenhum valor foi gravado nela. */
    virtual int get(int key) = 0;

    /**
     * @brief Grava o valor na chave.
     * @details Depois do retorno, todo get que comece em seguida devolve este valor
     *          ou um valor gravado depois dele.
     */
    virtual void put(int key, int value) = 0;

    /**
     * @brief Conta as chaves de lo até hi-1 com valor diferente de 0.
     * @details Não precisa ser atômica: cada chave é contada pelo seu estado em algum
     *          instante durante a chamada.
     */
    virtual int scan(int lo, int hi) = 0;

    /** @brief Retorna a quantidade de chamadas de cada operação realizadas até o momento. */
    virtual Stats stats() = 0;
};

/**
 * @brief Executa em ordem as operações de uma sessão e registra seus resultados.
 * @details Cada thread deve ter o seu próprio SessionRunner e o seu próprio vetor de registros.
 */
class SessionRunner {
public:
    SessionRunner(TableService& svc, std::vector<Rec>& out) : svc_(svc), out_(out) {}

    /** @brief Executa sequencialmente as operações de uma sessão. */
    void run(const Session& session) {
        for (size_t idx = 0; idx < session.ops.size(); ++idx) {
            const Op& op = session.ops[idx];
            int64_t s = now_ns();
            int res = 0;
            switch (op.kind) {
                case 'G': res = svc_.get(op.a); break;
                case 'P': svc_.put(op.a, op.b); break;
                case 'S': res = svc_.scan(op.a, op.b); break;
                default: throw std::runtime_error("operação desconhecida");
            }
            int64_t e = now_ns();
            out_.push_back({session.id, static_cast<int>(idx), op.kind, op.a, op.b, s, e, res});
        }
    }

private:
    TableService& svc_;
    std::vector<Rec>& out_;
};

/** @brief Grava no arquivo os registros de operações, as estatísticas e os metadados da execução. */
inline void write_log(const std::string& path, const std::vector<std::vector<Rec>>& outs,
                      const Stats& st, int workers, int64_t wall_ns) {
    std::ofstream f(path);
    if (!f) throw std::runtime_error("não foi possível gravar " + path);
    for (const auto& out : outs) {
        for (const Rec& r : out) {
            f << "OP\t" << r.session << '\t' << r.idx << '\t' << r.kind << '\t' << r.a << '\t';
            if (r.kind == 'G') f << '-'; else f << r.b;
            f << '\t' << r.start << '\t' << r.end << '\t';
            if (r.kind == 'P') f << '-'; else f << r.result;
            f << '\n';
        }
    }
    f << "STATS\tgets=" << st.gets << "\tputs=" << st.puts << "\tscans=" << st.scans << '\n';
    f << "RUN\tworkers=" << workers << "\twall_ns=" << wall_ns << '\n';
}

}  // namespace harness

#endif
