/**
 * Implementação em que a tabela concorrente é dividida em partições, 
 * cada uma com a sua sincronização, de modo que operações em chaves de 
 * partições diferentes não esperem umas pelas outras
 */
public class FineTableService implements Harness.TableService {
    /** Parâmetros da carga */
    private final Harness.Params params;

    /**
     * Cria o serviço
     * @param params parâmetros da carga
     */
    public FineTableService(Harness.Params params) {
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

    /** {@inheritDoc} */
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
