/**
 * ARQUIVO DOS ALUNOS — versão Coarse da tabela concorrente.
 *
 * <p>Leia 'Descrição do problema' e 'Implementação' no README antes de começar e
 * justifique no relatório cada escolha de sincronização.</p>
 */
public class CoarseTableService implements Harness.TableService {
    /** Parâmetros da carga */
    private final Harness.Params params;

    /**
     * Cria o serviço
     * @param params parâmetros da carga
     */
    public CoarseTableService(Harness.Params params) {
        this.params = params;
        // TODO: estado compartilhado e mecanismos de sincronização
    }

    /** {@inheritDoc} */
    @Override public int get(int key) { throw new UnsupportedOperationException("TODO"); }

    /** {@inheritDoc} */
    @Override public void put(int key, int value) { throw new UnsupportedOperationException("TODO"); }

    /** {@inheritDoc} */
    @Override public int scan(int lo, int hi) { throw new UnsupportedOperationException("TODO"); }

    /** {@inheritDoc} */
    @Override public Harness.Stats stats() { throw new UnsupportedOperationException("TODO"); }
}
