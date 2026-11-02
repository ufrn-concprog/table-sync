/**
 * @file    harness.h
 * @brief   Infraestrutura de execução da tabela concorrente.
 * @details Fornece leitura da carga, relógio, executor de sessões e gravação do log
 *          consumido pelo validador.
 */

#ifndef HARNESS_H
#define HARNESS_H

#include <chrono>
using std::chrono::steady_clock;
using std::chrono::nanoseconds;

#include <cstdint>
using std::int64_t;

#include <fstream>
using std::ifstream;
using std::ofstream;

#include <sstream>
using std::istringstream;
using std::ostringstream;

#include <stdexcept>
using std::runtime_error;

#include <string>
using std::string;

#include <vector>
using std::vector;

namespace harness {

/** 
 * @brief Retorna o tempo monotônico decorrido desde o início do processo, 
 *        em nanossegundos.
 * @return Tempo decorrido desde o início do processo, em nanossegundos.
 */
inline int64_t now_ns() {
    static const auto origin = steady_clock::now();
    return std::chrono::duration_cast<nanoseconds>(steady_clock::now() - origin).count();
}

/** 
 * @struct  Params
 * @brief   Representa os parâmetros da carga.
 */
struct Params {
    /** @brief Quantidade de chaves; as chaves são os inteiros de 0 a keys-1. */
    int keys = 0;
};

/** 
 * @struct  Op
 * @brief   Representa uma operação individual de uma sessão. 
 * @details Cada operação é `get`, `put` ou `scan`, com seus argumentos.
 */
struct Op {
    char kind;   ///< 'G' (get), 'P' (put) ou 'S' (scan)
    int a;       ///< chave (G e P) ou limite inferior lo (S)
    int b;       ///< valor (P) ou limite superior hi, exclusivo (S); 0 em G
};

/** 
 * @struct  Session
 * @brief   Representa uma sessão de operações.
 * @details Cada sessão é composta por uma sequência de operações.
 */
struct Session {
    int id;             ///< identificador da sessão
    vector<Op> ops;     ///< operações, na ordem de execução
};

/** 
 * @struct  Workload
 * @brief   Representa a carga completa, composta por parâmetros e 
 *          sessões de operações.
 */
struct Workload {
    Params params;              ///< parâmetros da carga
    vector<Session> sessions;   ///< sessões de operações
};

/** 
 * @struct  Stats
 * @brief   Contadores agregados do serviço. 
 * @details Cada contador é incrementado a cada chamada de operação correspondente.
 */
struct Stats {
    int64_t gets;   ///< quantidade de chamadas de get
    int64_t puts;   ///< quantidade de chamadas de put
    int64_t scans;  ///< quantidade de chamadas de scan
};

/** 
 * @struct  SessionRecord
 * @brief   Registro de uma operação executada. 
 * @details Contém informações sobre uma operação específica que foi executada.
 */
struct SessionRecord {
    int session;        ///< identificador da sessão
    int idx;            ///< índice da operação na sessão
    char kind;          ///< 'G' (get), 'P' (put) ou 'S' (scan)
    int a;              ///< chave (G e P) ou limite inferior lo (S)
    int b;              ///< valor (P) ou limite superior hi (S); 0 em G
    int64_t start;      ///< instante de início da operação, em nanossegundos
    int64_t end;        ///< instante de término da operação, em nanossegundos
    int result;         ///< valor devolvido (G e S); sem significado em P
};

/**
 * @brief Lê os parâmetros e as sessões de um arquivo de carga.
 * @param path Caminho do arquivo de carga.
 * @return Workload contendo os parâmetros e as sessões lidas.
 * @throws `runtime_error` se o arquivo não puder ser lido ou não tiver a linha PARAMS.
 */
inline Workload load_workload(const string& path) {
    ifstream in(path);
    if (!in) throw runtime_error("não foi possível abrir " + path);
    Workload wl;
    bool has_params = false;
    string line;
    while (getline(in, line)) {
        istringstream ss(line);
        string tok;
        if (!(ss >> tok) || tok[0] == '#') continue;
        if (tok == "PARAMS") {
            while (ss >> tok) {
                auto eq = tok.find('=');
                if (tok.substr(0, eq) == "keys") { wl.params.keys = std::stoi(tok.substr(eq + 1)); has_params = true; }
            }
        } else if (tok == "SESSION") {
            Session s;
            ss >> s.id;
            ss.ignore(); // ignora o caractere de nova linha
            string k;
            while (ss >> k) {
                Op op{k[0], 0, 0};
                if (k == "G") ss >> op.a;
                else if (k == "P" || k == "S") ss >> op.a >> op.b;
                else throw runtime_error("operação desconhecida: " + k);
                s.ops.push_back(op);
            }
            wl.sessions.push_back(std::move(s));
        }
    }
    if (!has_params) throw runtime_error("carga sem linha PARAMS");
    return wl;
}

/**
 * @class   TableService
 * @brief   Contrato das implementações da tabela concorrente.
 * @details Todos os métodos podem ser chamados concorrentemente por várias threads.
 */
class TableService {
public:
    virtual ~TableService() = default;

    /** @brief Chamado uma vez antes de qualquer operação. */
    virtual void start() {}

    /** 
     * @brief Chamado uma vez depois da última operação.
     * @details Este método deve ser utilizado para encerrar threads auxiliares, 
     *          se houver. 
     */
    virtual void close() {}

    /** 
     * @brief Devolve o valor da chave 
     * @param key Chave da qual obter o valor.
     * @return Valor da chave, ou 0 se nenhum valor foi gravado nela.
     */
    virtual int get(int key) = 0;

    /**
     * @brief Grava o valor na chave.
     * @details Depois do retorno, todo `get` que comece em seguida devolve este valor
     *          ou um valor gravado depois dele.
     * @param key Chave na qual gravar o valor.
     * @param value Valor a ser gravado na chave.
     */
    virtual void put(int key, int value) = 0;

    /**
     * @brief Conta as chaves de `lo` até `hi`-1 com valor diferente de 0.
     * @details Não precisa ser atômica: cada chave é contada pelo seu estado em algum
     *          instante durante a chamada.
     * @param lo Limite inferior da contagem (inclusivo).
     * @param hi Limite superior da contagem (exclusivo).]
     * @return Quantidade de chaves com valor diferente de 0 no intervalo [lo, hi).
     */
    virtual int scan(int lo, int hi) = 0;

    /** 
     * @brief Retorna a quantidade de chamadas de cada operação realizadas até o momento.
     * @return Stats contendo os contadores de chamadas de cada operação.
     */
    virtual Stats stats() = 0;
};

/**
 * @class   SessionRunner
 * @brief   Executa em ordem as operações de uma sessão e registra seus resultados.
 * @details Cada thread deve ter sua instância própria de SessionRunner e o seu 
 *          próprio vetor de registros.
 */
class SessionRunner {
public:
    /** 
     * @brief Construtor da classe SessionRunner. 
     * @param svc Referência para o serviço de tabela.
     * @param out Referência para o vetor de registros de sessão.
     */
    SessionRunner(TableService& svc, vector<SessionRecord>& out) : 
        svc_(svc), out_(out) {}

    /** 
     * @brief Executa sequencialmente as operações de uma sessão.
     * @param session Sessão cujas operações serão executadas.
     * @throws `runtime_error` se uma operação desconhecida for encontrada.
     */
    void run(const Session& session) {
        for (size_t idx = 0; idx < session.ops.size(); ++idx) {
            const Op& op = session.ops[idx];
            int64_t s = now_ns();
            int res = 0;
            switch (op.kind) {
                case 'G': res = svc_.get(op.a); break;
                case 'P': svc_.put(op.a, op.b); break;
                case 'S': res = svc_.scan(op.a, op.b); break;
                default: throw runtime_error("operação desconhecida");
            }
            int64_t e = now_ns();
            out_.push_back({session.id, static_cast<int>(idx), 
                op.kind, op.a, op.b, s, e, res});
        }
    }

private:
    /** @brief Referência para o serviço de tabela. */
    TableService& svc_;

    /** @brief Referência para o vetor de registros de sessão. */
    vector<SessionRecord>& out_;
};

/** 
 * @brief Grava no arquivo os registros de operações, as estatísticas e 
 *        os metadados da execução.
 * @param path Caminho do arquivo de saída.
 * @param outs Vetor de vetores de registros de sessão, um vetor por thread.
 * @param st Estatísticas agregadas do serviço.
 * @param workers Quantidade de threads que executaram as sessões.
 * @param wall_ns Tempo total de execução, em nanossegundos.
 * @throws `runtime_error` se o arquivo não puder ser gravado.
 */
inline void write_log(const string& path, const vector<vector<SessionRecord>>& outs,
                      const Stats& st, int workers, int64_t wall_ns) {
    ofstream f(path);
    if (!f) throw runtime_error("não foi possível gravar " + path);
    for (const auto& out : outs) {
        for (const SessionRecord& r : out) {
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
