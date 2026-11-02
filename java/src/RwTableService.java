/**
 * Implementação em que um único lock de leitura e escrita protege toda a 
 * tabela concorrente, de modo que as operações {@code get} e {@code scan} 
 * possam ocorrer ao mesmo tempo, e somente a operação {@code put} exclua 
 * as demais operações
 */
public class RwTableService implements Harness.TableService {
    /** Parâmetros da carga */
    private final Harness.Params params;

    /**
     * Cria o serviço
     * @param params parâmetros da carga
     */
    public RwTableService(Harness.Params params) {
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
