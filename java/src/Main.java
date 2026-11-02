import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CyclicBarrier;

/**
 * Programa principa.
 *
 * <p>Executa a carga com um <em>pipeline</em> concorrente: um produtor entrega 
 * as sessões, por uma fila limitada, a um determinado número de <em>threads</em>; 
 * todas começam juntas por uma porta de largada e o tempo medido ({@code wall}) 
 * exclui a criação das <em>threads</em>.</p>
 *
 * <p>Uso: 
 *    {@code java -cp out Main workloads/leitura-1.txt --workers 16 --impl rw --warmup 2 -o events.log}
 * </p>
 * 
 * <p>A opção {@code --warmup N} executa o <em>pipeline</em> {@code N} vezes, sem 
 * medir e sem gravar log, antes da execução medida (aquecimento da máquina virtual).
 * </p>
 */
public class Main {
    /** Capacidade da fila entre o produtor e as threads trabalhadoras */
    private static final int QUEUE_CAPACITY = 64;

    /** Cria a classe de entrada do programa */
    public Main() {}

    /** Fila limitada: o produtor espera se cheia; as threads esperam se vazia. */
    private static final class BoundedQueue {
        private final ArrayDeque<Harness.Session> items = new ArrayDeque<>();
        private final int capacity;
        private boolean closed;

        /**
         * Cria a fila limitada
         * @param capacity Capacidade máxima da fila
         */
        BoundedQueue(int capacity) { this.capacity = capacity; }

        /**
         * Coloca uma sessão na fila, bloqueando se cheia
         * @param session Sessão a colocar na fila
         * @throws InterruptedException se a thread for interrompida enquanto espera
         */
        synchronized void put(Harness.Session session) throws InterruptedException {
            while (items.size() >= capacity) wait();
            items.add(session);
            notifyAll();
        }

        /** Fecha a fila, liberando as threads que esperam por sessões */
        synchronized void close() { 
            closed = true; 
            notifyAll(); 
        }

        /** 
         * Devolve a próxima sessão, ou {@code null} se a fila fechou e esvaziou. 
         * @return Sessão ou {@code null}
         * @throws InterruptedException se a thread for interrompida enquanto espera
         */
        synchronized Harness.Session take() throws InterruptedException {
            while (items.isEmpty() && !closed) wait();
            if (items.isEmpty()) return null;
            Harness.Session s = items.poll();
            notifyAll();
            return s;
        }
    }

    /**
     * Executa o pipeline uma vez
     * @param params    Parâmetros da carga
     * @param sessions  Sessões a executar
     * @param impl      Nome da implementação: {@code coarse}, {@code rw} ou {@code fine}
     * @param workers   Quantidade de threads trabalhadoras
     * @param out       Ccaminho do arquivo de log, ou {@code null} para não gravá-lo
     * @return Tempo decorrido ({@code wall}) em nanossegundos
     * @throws Exception se ocorrer uma falha durante a execução ou a gravação do log
     */
    static long execute(Harness.Params params, List<Harness.Session> sessions, 
        String impl, int workers, Path out) throws Exception {
        Harness.TableService service = switch (impl) {
            case "coarse" -> new CoarseTableService(params);
            case "rw" -> new RwTableService(params);
            case "fine" -> new FineTableService(params);
            default -> throw new IllegalArgumentException("--impl deve ser coarse, rw ou fine");
        };
        service.start();

        BoundedQueue queue = new BoundedQueue(QUEUE_CAPACITY);
        CyclicBarrier gate = new CyclicBarrier(workers + 2);            // trabalhadoras + produtor + principal
        List<List<Harness.SessionRecord>> outs = new ArrayList<>();
        List<Thread> threads = new ArrayList<>();
        for (int i = 0; i < workers; i++) {
            List<Harness.SessionRecord> recs = new ArrayList<>();       // uma lista de registros por thread
            outs.add(recs);
            threads.add(new Thread(() -> {
                try {
                    Harness.SessionRunner runner = 
                        new Harness.SessionRunner(service, recs);
                    gate.await();
                    Harness.Session s;
                    while ((s = queue.take()) != null) runner.run(s);
                } catch (Throwable e) { 
                    e.printStackTrace();
                    System.exit(1);         // falha: encerra, em vez de travar o produtor
                }
            }));
        }
        threads.add(new Thread(() -> {      // produtor
            try {
                gate.await();
                for (Harness.Session s : sessions) queue.put(s);
                queue.close();
            } catch (Exception e) { 
                throw new RuntimeException(e); 
            }
        }));
        threads.forEach(Thread::start);
        gate.await();
        long t0 = Harness.nowNs();
        for (Thread t : threads) t.join();
        long wall = Harness.nowNs() - t0;

        service.close();
        if (out != null) {
            Harness.writeLog(out, outs, service.stats(), workers, wall);
        }
        return wall;
    }

    /**
     * Analisa os argumentos, executa o aquecimento solicitado e realiza a execução medida
     * @param args Argumentos da linha de comando
     * @throws Exception se a carga, a execução ou a gravação do log falhar
     */
    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("uso: Main <carga> [--workers N] [--impl coarse|rw|fine] [--warmup N] [-o arquivo]");
            System.exit(1);
        }
        Path workloadPath = Path.of(args[0]);
        int workers = 16, warmup = 0;
        String impl = "coarse";
        Path output = Path.of("events.log");
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--workers" -> workers = Integer.parseInt(args[++i]);
                case "--impl" -> impl = args[++i];
                case "--warmup" -> warmup = Integer.parseInt(args[++i]);
                case "-o" -> output = Path.of(args[++i]);
                default -> throw new IllegalArgumentException("argumento desconhecido: " + args[i]);
            }
        }

        Harness.Workload wl = Harness.loadWorkload(workloadPath);
        for (int i = 0; i < warmup; i++) {
            execute(wl.params(), wl.sessions(), impl, workers, null);
        }
        long wall = execute(wl.params(), wl.sessions(), impl, workers, output);
        System.out.printf("%d sessoes em %.3f s -> %s%n", wl.sessions().size(), wall / 1e9, output);
    }
}
