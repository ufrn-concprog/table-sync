import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Infraestrutura de execução da tabela concorrente.
 *
 * <p>Fornece leitura da carga, relógio, executor de sessões e gravação do log
 * consumido pelo validador.</p>
 */
public final class Harness {
    /** Impede a instanciação desta classe utilitária */
    private Harness() {}

    /** Instante monotônico usado como origem para as medições do processo */
    private static final long ORIGIN = System.nanoTime();

    /**
     * Retorna o tempo monotônico decorrido desde o início do processo
     * @return Tempo decorrido em nanossegundos
     */
    public static long nowNs() {
        return System.nanoTime() - ORIGIN;
    }

    /**
     * Parâmetros da carga
     * @param keys quantidade de chaves; as chaves são os inteiros de 0 a keys-1
     */
    public record Params(int keys) {}

    /**
     * Operação individual de uma sessão
     * @param kind  {@code 'G'} (get), {@code 'P'} (put) ou {@code 'S'} (scan)
     * @param a     Chave ({@code G} e {@code P}) ou limite inferior, inclusivo ({@code 'S'})
     * @param b     Valor ({@code P}) ou limite superior, exclusivo ({@code 'S'}); 0 em ({@code G})
     */
    public record Op(char kind, int a, int b) {}

    /**
     * Sessão de operações
     * @param id    Identificador da sessão
     * @param ops   Operações, na ordem de execução
     */
    public record Session(int id, List<Op> ops) {}

    /**
     * Carga completa
     * @param params    Parâmetros da carga
     * @param sessions  Sessões, na ordem do arquivo
     */
    public record Workload(Params params, List<Session> sessions) {}

    /**
     * Contadores agregados do serviço
     * @param gets  Quantidade de chamadas a {@code get}
     * @param puts  Quantidade de chamadas a {@code put}
     * @param scans Quantidade de chamadas a {@code scan}
     */
    public record Stats(long gets, long puts, long scans) {}

    /**
     * Registro de uma operação executada
     * @param session   Identificador da sessão
     * @param idx       Posição da operação na sessão
     * @param kind      Tipo da operação
     * @param a         Primeiro argumento
     * @param b         Segundo argumento
     * @param start     Instante de início, em nanossegundos
     * @param end       Instante de fim, em nanossegundos
     * @param result    Valor devolvido (G e S); sem significado em P
     */
    public record SessionRecord(int session, int idx, char kind, int a, int b, 
        long start, long end, int result) {}

    /**
     * Contrato das implementações da tabela concorrente. Todos os métodos podem
     * ser chamados concorrentemente por várias threads.
     */
    public interface TableService {
        /** Chamado uma vez antes de qualquer operação */
        default void start() {}

        /** Chamado uma vez depois da última operação; encerre aqui threads auxiliares, se houver */
        default void close() {}

        /**
         * Devolve o valor da chave
         * @param key chave, de 0 a {@code keys}-1
         * @return valor gravado, ou 0 se nenhum valor foi gravado na chave
         */
        int get(int key);

        /**
         * Grava o valor na chave. Depois do retorno, todo {@code get} que comece 
         * em seguida devolve este valor ou um valor gravado depois dele.
         * @param key Chave, de 0 a {@code keys}-1
         * @param value Valor positivo, único em toda a carga
         */
        void put(int key, int value);

        /**
         * Conta as chaves de {@code lo} até {@code hi}-1 com valor diferente de 0. 
         * @param lo Limite inferior, inclusivo
         * @param hi Limite superior, exclusivo
         * @return Quantidade de chaves com valor diferente de 0
         */
        int scan(int lo, int hi);

        /**
         * Retorna os contadores do serviço
         * @return Quantidade de chamadas de cada operação realizadas até o momento
         */
        Stats stats();
    }

    /**
     * Lê os parâmetros e as sessões de uma carga
     * @param path Caminho do arquivo de carga
     * @return parâmetros e sessões
     * @throws IOException se o arquivo não puder ser lido ou não tiver a linha 
     *         {@code PARAMS}
     */
    public static Workload loadWorkload(Path path) throws IOException {
        Params params = null;
        List<Session> sessions = new ArrayList<>();
        for (String raw : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] t = line.split("\\s+");
            if (t[0].equals("PARAMS")) {
                for (int i = 1; i < t.length; i++) {
                    String[] kv = t[i].split("=");
                    if (kv[0].equals("keys")) params = new Params(Integer.parseInt(kv[1]));
                }
            } else if (t[0].equals("SESSION")) {
                List<Op> ops = new ArrayList<>();
                for (int i = 2; i < t.length; ) {
                    char k = t[i].charAt(0);
                    if (k == 'G') {
                        ops.add(new Op('G', Integer.parseInt(t[i + 1]), 0));
                        i += 2;
                    } else if (k == 'P' || k == 'S') {
                        ops.add(new Op(k, Integer.parseInt(t[i + 1]), Integer.parseInt(t[i + 2])));
                        i += 3;
                    } else {
                        throw new IOException("operação desconhecida: " + t[i]);
                    }
                }
                sessions.add(new Session(Integer.parseInt(t[1]), List.copyOf(ops)));
            }
        }
        if (params == null) throw new IOException("carga sem linha PARAMS");
        return new Workload(params, sessions);
    }

    /** Executa em ordem as operações de uma sessão e registra seus resultados. */
    public static final class SessionRunner {
        private final TableService svc;
        private final List<SessionRecord> out;

        /**
         * Cria um executor associado a um serviço e a uma lista de saída; 
         * cada thread deve ter sua instância própria do serviço e sua 
         * própria lista de saída.
         * 
         * @param svc Serviço utilizado para executar as operações
         * @param out Lista que receberá os registros das operações
         */
        public SessionRunner(TableService svc, List<SessionRecord> out) {
            this.svc = svc;
            this.out = out;
        }

        /**
         * Executa as operações de uma sessão sequencialmente
         * @param session Sessão a executar
         * @throws IllegalStateException se a operação for desconhecida
         */
        public void run(Session session) {
            List<Op> ops = session.ops();
            for (int idx = 0; idx < ops.size(); idx++) {
                Op op = ops.get(idx);
                long s = Harness.nowNs();
                int res = 0;
                switch (op.kind()) {
                    case 'G' -> res = svc.get(op.a());
                    case 'P' -> svc.put(op.a(), op.b());
                    case 'S' -> res = svc.scan(op.a(), op.b());
                    default -> throw new IllegalStateException("operação desconhecida: " + op.kind());
                }
                long e = Harness.nowNs();
                out.add(new SessionRecord(session.id(), idx, op.kind(), op.a(), op.b(), s, e, res));
            }
        }
    }

    /**
     * Grava no arquivo os registros de operações, as estatísticas e os 
     * metadados da execução
     * @param path      Caminho do arquivo de destino
     * @param outs      Listas de registros das threads trabalhadoras
     * @param st        Estatísticas finais do serviço
     * @param workers   Quantidade de threads trabalhadoras
     * @param wallNs    Duração total da execução em nanossegundos
     * @throws IOException se não for possível gravar o arquivo
     */
    public static void writeLog(Path path, List<List<SessionRecord>> outs, 
        Stats st, int workers, long wallNs) throws IOException {
        try (PrintWriter w = new PrintWriter(Files.newBufferedWriter(path, 
                StandardCharsets.UTF_8))) {
            StringBuilder sb = new StringBuilder();
            for (List<SessionRecord> out : outs) {
                for (SessionRecord r : out) {
                    sb.setLength(0);
                    sb.append("OP\t").append(r.session())
                        .append('\t').append(r.idx()).append('\t').append(r.kind())
                        .append('\t').append(r.a()).append('\t')
                        .append(r.kind() == 'G' ? "-" : String.valueOf(r.b()))
                        .append('\t').append(r.start()).append('\t').append(r.end())
                        .append('\t').append(r.kind() == 'P' ? "-" : String.valueOf(r.result())).append('\n');
                    w.print(sb);
                }
            }
            w.print("STATS\tgets=" + st.gets() + "\tputs=" + st.puts() + 
                "\tscans=" + st.scans() + "\n");
            w.print("RUN\tworkers=" + workers + "\twall_ns=" + wallNs + "\n");
        }
    }
}
