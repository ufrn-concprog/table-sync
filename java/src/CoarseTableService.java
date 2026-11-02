/**
 * Implementação de referência da tabela concorrente.
 * 
 * <p>Esta versão deve usar uma estratégia simples e correta para proteger o
 * estado compartilhado.</p>
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

    /** 
     * {@inheritDoc} 
     * @throws UnsupportedOperationException o método ainda não foi implementado
     */
    @Override public int get(int key) { 
        throw new UnsupportedOperationException("TODO"); 
    }

    /** 
     * {@inheritDoc} 
     * @throws UnsupportedOperationException o método ainda não foi implementado
     */
    @Override public void put(int key, int value) { 
        throw new UnsupportedOperationException("TODO"); 
    }
    /** 
     * {@inheritDoc} 
     * @throws UnsupportedOperationException o método ainda não foi implementado
     */
    @Override public int scan(int lo, int hi) { 
        throw new UnsupportedOperationException("TODO"); 
    }

    /** 
     * {@inheritDoc} 
     * @throws UnsupportedOperationException o método ainda não foi implementado
     */
    @Override public Harness.Stats stats() { 
        throw new UnsupportedOperationException("TODO"); 
    }
}
