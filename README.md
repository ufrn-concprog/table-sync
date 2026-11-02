# Trabalho Prático: Tabela Concorrente

<sub>Última atualização: 01/11/2026</sub><br/>

[![Java](https://img.shields.io/badge/Java-17%2B-orange?logo=java)](https://www.oracle.com/java/technologies/javase-downloads.html)
[![C++](https://img.shields.io/badge/C++-20%2B-green?logo=c%2B%2B)](https://en.cppreference.com/w/cpp/20)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org)

> **Declaração sobre o uso de Inteligência Artificial generativa.** A concepção deste trabalho prático (o tema, o problema, os objetivos de aprendizagem, as regras do serviço e os critérios de avaliação) foi realizada pelo docente. A presente especificação e os códigos-fonte disponibilizados neste repositório foram produzidos com o auxílio de uma ferramenta de Inteligência Artificial generativa (mais precisamente, o Claude, da Anthropic, no modelo Sonnet 5.5), sob a direção, revisão e validação do docente, que permanece integralmente responsável pelos artefatos produzidos e por seu conteúdo. O material foi revisado e testado pelo docente com soluções de referência nas linguagens de programação Java, C++ e Python, mas ainda pode haver erros ou eventuais inconsistências. Destaque-se que esta declaração **não altera** a política de colaboração e de uso de ferramentas de Inteligência Artificial para a entrega a ser realizada, conforme estabelecido na seção [Autoria e política de colaboração](#autoria-e-política-de-colaboração).

## Sumário

- [Objetivo](#objetivo)
- [Descrição do problema](#descrição-do-problema)
- [Material fornecido](#material-fornecido)
- [Tarefas](#tarefas)
  - [Implementação](#implementação)
  - [Experimentação](#experimentação)
  - [Relato](#relato)
- [Autoria e política de colaboração](#autoria-e-política-de-colaboração)
- [Entrega](#entrega)
- [Avaliação](#avaliação)
- [Dúvidas e informações](#dúvidas-e-informações)

## Objetivo

O objetivo deste trabalho prático é projetar, implementar e comparar três formas de sincronizar uma tabela em memória acessada por múltiplas *threads*, em que a maioria das operações realizadas é de leitura sobre essa tabela. O foco do trabalho está em responder duas perguntas:

1. Quando vale a pena permitir que várias *threads* leiam ao mesmo tempo?
2. Quanto se ganha ao dividir a tabela em partes com sincronização independente?

## Descrição do problema

Uma tabela concorrente é uma estrutura em memória que associa chaves a valores e é usada por múltiplas *threads* ao mesmo tempo. Neste trabalho, as chaves são números inteiros de 0 a $k-1$ e os valores também são inteiros.

Em aplicações reais, a grande maioria das operações é de leitura, e as alterações, mesmo que sejam menos frequentes, precisam ser vistas corretamente por todos. Ocasionalmente, uma operação percorre parte da tabela para calcular algum resumo acerca do conteúdo que esteja nela. O desafio é permitir o máximo de paralelismo entre as leituras sem comprometer a correção das escritas.

Três operações básicas podem ser realizadas sobre essa tabela concorrente:

| Operação | Significado |
| :------- | :---------- |
| `get(key)` | Devolve o valor da chave `key`, ou `0` se nenhum valor foi gravado nela ainda. |
| `put(key, value)` | Grava o valor `value` na chave `key`. Uma vez realizada essa operação, toda operação `get` que comece em seguida deve devolver esse valor ou um valor gravado depois dele, nunca um anterior. |
| `scan(lo, hi)` | Devolve quantas chaves de `lo` até `hi-1` têm valor diferente de `0`. |

Além essas três operações, `stats()` devolve ao final da execução três contadores, cada um se referindo ao número de operações `get`, `put` e `scan` que foram realizadas. Esses contadores são atualizados por várias *threads* ao mesmo tempo e devem corresponder exatamente ao que ocorreu, de modo que uma atualização perdida é considerada uma falha.

O serviço da tabela concorrente é um objeto que implementa a interface `TableService`, definida na infraestrutura de execução, com essas quatro operações mais `start()` e `close()`, chamadas pelo programa principal.

## Material fornecido

Para que o foco do trabalho seja a sincronização, este repositório fornece, em Java, C++ e Python:

1. um **gerador de carga**;
2. a **infraestrutura de execução** (*harness*), que lê a carga, cria as *threads*, entrega as sessões a elas, executa as operações no serviço e grava o *log*;
3. um **validador**;
4. um **sumarizador**; e
5. os **esqueletos** das três versões do serviço, a serem completados.

O programa principal (`Main`) também é fornecido, com o *pipeline* concorrente pronto juntamente com as opções de execução. A infraestrutura de execução e o programa principal **não devem ser modificados**.

O repositório está organizado da seguinte forma:

```text
table-sync/
├── author.md
├── README.md
├── cpp/
│   ├── coarse_service.h
│   ├── Doxyfile
│   ├── fine_service.h
│   ├── harness.h
│   ├── rw_service.h
│   ├── main.cpp
│   ├── Makefile
├── java/src/
│   ├── CoarseTableService.java
│   ├── FineTableService.java
│   ├── Harness.java
│   ├── Main.java
│   ├── RwTableService.java
├── python/
│   ├── harness.py
│   ├── main.py
│   ├── table_service.py
├── tools/
│   ├── generate_workload.py
│   ├── summarize_log.py
│   └── validate_log.py
├── workloads/
```

### Carga

O serviço não tem usuários reais, mas sim uma **carga** (*workload*), que consiste em um arquivo de texto que descreve uma sequência de operações que serão realizadas sobre a tabela. Linhas em branco e linhas começadas por `#` são comentários e devem ser ignoradas; as demais são:

- `PARAMS keys=<n>`: uma única linha com o número de chaves ($k$)
- `SESSION <id> <operação> ...`: uma linha por sessão com um identificador inteiro único, em que cada operação é identificada como:
  - `G <key>`, correspondendo a `get(key)`;
  - `P <key> <value>`, correspondendo a `put(key, value)`; e
  - `S <lo> <hi>`, correspondendo a `scan(lo, hi)`.

Um exemplo de um trecho do arquivo de carga seria:

```text
PARAMS keys=1000
SESSION 0 G 7 G 7 G 913
SESSION 1 P 7 501 G 7
SESSION 2 S 0 100 S 100 200
```

A tabela possui 1000 chaves e são realizadas três sessões:

- A sessão `0` tenta realizar três operações `get`, duas sobre a chave `7` e uma sobre a chave `913`;
- A sessão `1` tenta realizar uma operação `put` para gravar o valor `501` sobre a chave `7` e, em seguida, uma operação `get` sobre essa mesma chave;
- A sessão `2` tenta realizar duas operações `scan`, a primeira sobre as chaves de `0` a `100` e a segunda sobre as chaves de `100` a `200`.

Note que as sessões são independentes, mas disputam as mesmas chaves, e a ordem em que o serviço as atende varia de uma execução para outra. É sobre essas condições que as condições de corrida aparecem.

### Gerador de carga

O arquivo [`generate_workload.py`](tools/generate_workload.py), que **não deve ser modificado**, cria a carga de forma determinística: a mesma semente, *perfil* e número de sessões geram sempre o mesmo arquivo. Uma sessão pode ser um dos seguintes três tipos:

1. *leitor*, que realiza apenas operações `get` com 60% dos acessos recaindo sobre 5% das chaves;
2. *escritor*, que realiza de uma a três operações `put`, cada uma seguida de uma operação `get`; e
3. *varredor*, que realiza uma operação `scan` sobre uma faixa de 100 chaves.

O perfil define a porcentagem de sessões de cada tipo: no leitura, 85% são leitoras, 10% escritoras e 5% varredoras; no escrita, 40%, 45% e 15%, respectivamente. O perfil de leitura imita o uso normal, enquanto o perfil de escrita aumenta as alterações e as varreduras, que disputam a tabela com as leituras.

Para executar o gerador de carga, o seguinte comando deve ser utilizado:

```bash
python3 tools/generate_workload.py --profile leitura --seed 1 --sessions 100000 -o workloads/leitura-1.txt
```

sendo indicados o perfil (`leitura` ou `escrita`), a semente, o número de sessões e o caminho do arquivo de saída. Como o gerador de carga é determinístico, a mesma semente, perfil e tamanho geram sempre o mesmo arquivo.

### Infraestrutura de execução

Os arquivos da infraestrutura de execução ([Harness.java](java/src/Harness.java), [harness.h](cpp/harness.h) e [harness.py](python/harness.py)) leem a carga, criam o serviço, executam as sessões e gravam o *log*. O *log* é um arquivo de texto com campos separados por tabulação, com uma linha por operação executada (sessão, posição, tipo, argumentos, instante de início, instante de fim e valor devolvido), uma linha `STATS` com os contadores e uma linha `RUN` com o número de *threads* e o tempo total de execução.

### Validador

O programa [`validate_log.py`](tools/validate_log.py) lê a carga e o *log* e procura por violações. Cada operação é registrada com o instante em que a chamada começou e o instante em que terminou. O validador só aponta uma violação quando **nenhuma** ordem possível a explica. Por exemplo, um `get` que começa depois que um `put` da mesma chave terminou não pode devolver um valor anterior a ele.

Para executar o validador, o seguinte comando deve ser utilizado passando-se como argumentos os arquivos de carga e de *log*, **nessa ordem**:

```bash
python3 tools/validate_log.py workloads/leitura-1.txt events.log
```

Em uma execução sem violações, a saída é parecida com esta:

```text
sessões: 3000  operações registradas: 35540/35540  gets: 30889  puts: 2853  scans: 1798
threads: 16  tempo: 0.063 s  vazão: 567882 ops/s, 47936 sessões/s
RESULTADO: OK (nenhuma violação encontrada)
```

O código de saída é `0` se não houver violações, `1` se houver, e `2` se um arquivo não puder ser lido. As categorias são:

- `completude`: todas as operações foram executadas e registradas uma vez, e a execução terminou;
- `valor-invalido`: uma operação `get` devolveu um valor que nunca foi gravado na chave;
- `valor-obsoleto`: uma operação `get` devolveu um valor já substituído por uma operação `put` concluída antes do início da operação `get`;
- `varredura`: resultado de uma operação `scan` impossível em qualquer ordem; e
- `contadores`: resultado de `stats()` diferente do registrado no *log*.

### Sumarizador

O programa [`summarize_log.py`](tools/summarize_log.py) exibe, para um *log*, o número de *threads*, o tempo total (`wall_ns`, em segundos), a vazão e, para cada tipo de operação, a quantidade de chamadas e a duração de cada chamada, em milissegundos (média, mediana, p95, p99 e máximo).

Para executar o sumarizador, o seguinte comando deve ser utilizado passando como argumento o arquivo de *log*:

```bash
python3 tools/summarize_log.py events.log
```

A saída tem a seguinte forma:

```text
threads: 16  tempo: 0.063 s  sessões: 3000  vazão: 47936.0 sessões/s, 567882 ops/s

op          n     média       p50       p95       p99       máx   (ms)
G       30889    0.0007    0.0006    0.0009    0.0025    0.1461
P        2853    0.0011    0.0008    0.0014    0.0039    0.0926
S        1798    0.0069    0.0053    0.0094    0.0173    1.8538
```

## Tarefas

### Implementação

Implemente o trabalho em **Java, C++ ou Python, obrigatoriamente**. Após clonar este repositório, mantenha **apenas o diretório da linguagem escolhida**, além dos diretórios [`tools`](tools/) e [`workloads`](workloads/). Os arquivos que devem ser editados são **apenas as três versões do serviço**, as quais respeitam as mesmas regras e diferem apenas na sincronização:

1. ***Coarse*** (opção `--impl coarse` no programa principal): um único mecanismo de exclusão mútua (um *lock* ou monitor) protege toda a tabela, e qualquer operação precisa adquiri-lo. É a versão mais simples de provar correta e serve como *baseline*.
2. ***Rw*** (opção `--impl rw` no programa principal): um único *lock* de leitura e escrita protege toda a tabela, de modo que as operações `get` e `scan` possam ocorrer ao mesmo tempo, e somente a operação `put` exclua as demais operações. Em Python, a biblioteca padrão não tem esse tipo de *lock*, portanto, ele deve ser implementado por conta própria (por exemplo, com `Lock` e `Condition`). **A política escolhida para quem espera (prefere leitores, escritores, ou é justa) deve ser documentada**.
3. ***Fine*** (opção `--impl fine` no programa principal): a tabela é dividida em partições, cada uma com a sua sincronização, de modo que operações em chaves de partições diferentes não esperem umas pelas outras. Como a operação `scan` pode atravessar várias partições e não precisa ser atômica, ela pode percorrê-las uma de cada vez. Os contadores também devem ser pensados para não virarem um ponto único de contenção.

Todos os arquivos disponibilizados para a implementação do serviço compilam com sucesso, porém lançam uma exceção (`TODO`) nos métodos a implementar.

As restrições a serem obedecidas são as seguintes:

- a tabela deve ser uma estrutura de dados comum (por exemplo, `HashMap`, `unordered_map`, `dict` ou *array*), protegida pelos mecanismos de sincronização escolhido;
- **não é permitido** usar coleções concorrentes (como `ConcurrentHashMap` em Java ou `tbb::concurrent_*` em C++) nem executores e *pools* de *threads*;
- podem ser utilizados monitores, *locks* (inclusive de leitura e escrita), semáforos e operações atômicas.

Para executar os programas em cada linguagem, os seguintes comandos podem ser utilizados:

```bash
# Java
java -cp out Main workloads/leitura-1.txt --workers 16 --impl rw -o events.log

# C++
./cpp/table_sync workloads/leitura-1.txt --workers 16 --impl rw -o events.log

# Python
python3 python/main.py workloads/leitura-1.txt --workers 16 --impl rw -o events.log

# Validação (qualquer linguagem)
python3 tools/validate_log.py workloads/leitura-1.txt events.log
```

Note que cada um dos programas principais requer os seguintes argumentos:

- o caminho do arquivo de carga;
- `--workers`: o número de *threads* de trabalho;
- `--impl`: a versão do serviço (`coarse`, `rw` ou `fine`); e
- `-o`: o caminho do arquivo de *log* que será produzido.

### Experimentação

A experimentação busca verificar:

1. quando o aumento do número de *threads* reduz o tempo e a partir de que ponto deixa de reduzir;
2. qual versão é a melhor, em que situação e por quanto; e
3. se a resposta muda entre os perfis `leitura` e `escrita`.

Serão realizados dois experimentos, conforme descrito mais adiante, considerando três métricas:

1. o **tempo** (`wall`) medido desde a abertura da porta de largada até o término das sessões, constando na linha `RUN` do *log* (campo `wall_ns`) e no sumarizador;
2. a **vazão** (*throughput*) medida como o número de sessões por segundo; e
3. o ***speed-up***, calculado como $S(n) = T(1) / T(n)$, em que $T(n)$ é o tempo médio com $n$ *threads*, da mesma versão e carga.

Os fatores a serem variados nos dois exprimentos são:

1. o **número de *threads*** (`--workers`), com pelo menos **quatro** valores, incluindo 1 e um valor maior que o número de núcleos da máquina (por exemplo 1, 4, 16 e 64);
2. a **versão**, isto é, `coarse`, `rw`, `fine`; e
3. o **perfil**, `leitura` e `escrita`.

No **Experimento E1 - Escalabilidade e comparação das versões**, devem ser consideradas 3 versões x 2 perfis x 4 valores de *threads*, o que totaliza 120 execuções. Cada versão deve ser examinada quanto à variação do tempo e da vazão em função das *threads*, calculando o *speed-up* e identificando onde ele deixa de crescer. Além disso, deve-se comparar as versões em cada número de *threads* pela razão entre os tempos médios, verificando se a diferença é maior que o desvio padrão. É importante salientar que pode haver condições em que a versão refinada não compensa, e identificá-las é um resultado válido.

No **Experimento E2 - Tempo por operação**, para ao menos uma configuração de cada versão (por exemplo, o maior número de *threads* no perfil `escrita`), deve-se resumir o *log* com o sumarizador e comparar as durações das operações `get`, `put` e `scan`, observando especialmente os percentis altos (p99 e máximo) da operação `put`, que revelam se quem escreve fica esperando atrás de quem lê.

As cargas devem ser geradas **uma única vez para cada perfil** com os seguintes comandos de execução do gerador de carga:

```bash
python3 tools/generate_workload.py --profile leitura --seed 1 --sessions 100000 -o workloads/exp-leitura.txt
python3 tools/generate_workload.py --profile escrita --seed 1 --sessions 100000 -o workloads/exp-escrita.txt
```

Como se tratam de 120 execuções, sugere-se que se automatiz a coleta com um *script* que executa o programa, executa o validador e registra o tempo e se a validação passou; se alguma execução falhar na validação, a coleta deve ser interrompida e o serviço corrigido. Ademais, como cada *log* tem dezenas de megabytes, sugere-se que ele seja apagado depois de validado, guardando apenas os das configurações usadas no Experimento E2. Deve-se chamar atenção ainda para o fato que o validador usa cerca de 600 MB de memória com cargas de 100 mil sessões, então deve-se verificar que a máquina onde os experimentos estão sendo realizados comporta essa capacidade antes de iniciar a coleta.

As execuções devem ser **intercaladas** entre as versões (*coarse*, *rw*, *fine*, *coarse*, ...), de modo que oscilações da máquina afetem as três igualmente. Recomenda-se encerrar outros programas e conectar o computador a uma fonte de alimentação de energia durante as medições. O relatório deve registrar o processador, o número de núcleos, a memória, o sistema operacional, a versão da linguagem e do compilador (ou da máquina virtual Java) e as opções utilizadas. Deve-se calcular a média e o desvio padrão amostral ($n-1$) do tempo e da vazão de cada configuração; uma diferença menor que o desvio padrão não é significativa, e execuções atípicas (*outliers*) **devem ser mantidas e explicadas, não removidas**.

Especificamente para a versão na linguagem Java, **toda execução deve usar `--warmup 2`, opção que já é fornecida pelo `Main`**, que executa o *pipeline* duas vezes, sem medir, antes da execução medida. Para as linguagens C++ e Python, **apenas a primeira execução deve ser descartada**.

### Relato

Finalmente, deverá ser elaborado um relatório contendo, pelo menos as seguintes seções:

1. **Identificação e ambiente**: integrantes, linguagem, ambiente de execução e instruções para compilar e executar.
2. **Projeto da sincronização**: o mecanismo escolhido em cada versão, a justificativa e as alternativas descartadas, incluindo a política de espera da versão *rw* e a forma de dividir a tabela na versão *fine*.
3. **Metodologia**: o que foi medido, como, quantas repetições, o tratamento do *warm-up* (em Java) e como a validação foi feita.
4. **Resultados**: para cada perfil, uma tabela com a média e o desvio padrão do tempo e da vazão de cada versão para cada número de *threads*, dois gráficos (tempo ou vazão em função das *threads*, com as três versões, e o *speed-up*), e a tabela de durações por operação do Experimento E2, informando quantas execuções foram feitas e quantas passaram na validação.
5. **Análise**: explicação, e não só descrição, dos resultados, respondendo:
   - por que *rw* ou *fine* superam (ou não) a *coarse* em cada perfil;
   - o que acontece quando as *threads* excedem os núcleos;
   - como a política da versão *rw* influenciou o tempo da operação `put`;
   - se algum resultado contrariou as expectativas;
   - em Python, como o o efeito do GIL nas medições.

6. **Limitações e trabalhos futuros**: o que os testes não cobrem e o que poderia ser feito com mais tempo.

## Autoria e política de colaboração

Este trabalho deverá ser realizado em equipe composta por **dois estudantes**, sendo importante dividir as tarefas igualmente entre os integrantes, que devem ser capazes de explicar qualquer trecho do código e do relatório. Após a implementação da solução, o arquivo [`author.md`](https://github.com/ufrn-concprog/table-sync/tree/master/author.md) presente no repositório deverá ser editado para incluir as informações de identificação (nome completo e endereço de *e-mail*) dos integrantes da equipe.

O trabalho em cooperação entre os estudantes da turma é estimulado, sendo admissível a discussão de ideias e estratégias. Contudo, tal interação não deve ser entendida como permissão para utilizar parte do código-fonte de colegas, o que pode configurar plágio. **Trabalhos copiados, no todo ou em parte, de outros colegas ou da Internet, ou ainda gerados por ferramentas de Inteligência Artificial, serão anulados e receberão nota zero.**

## Entrega

O sistema de controle de versão [Git](https://git-scm.com) será utilizado para viabilizar a entrega da implementação. Para possibilitar a associação de repositórios Git a cada equipe e reuni-los sob a mesma infraestrutura, foi criada uma atividade (*assignment*) no [Classroom 50](https://classroom50.org/), cujo *link* de acesso está disponível na Turma Virtual do SIGAA. No processo de ingresso na atividade, **cada equipe deve ser obrigatoriamente nomeada com o primeiro nome de cada integrante da equipe**, por exemplo, `Maria&Joao`.

A fim de garantir a boa manutenção do repositório, deve-se ainda configurar corretamente o arquivo `.gitignore` para desconsiderar arquivos que não devam ser versionados, como os executáveis gerados pela compilação do código-fonte, os arquivos de carga e os *logs*. Por outro lado, devem ser mantidos o diretório [`tools`](tools/) e o da linguagem escolhida.

A entrega deste trabalho deverá ser realizada até as **23:59 do dia 16 de novembro de 2026** no respectivo repositório Git da equipe. O relatório, em formato PDF, deverá ser enviado por meio da opção *Tarefas* da Turma Virtual do SIGAA, juntamente com o endereço do repositório, no campo *Comentários*. **Um único membro da equipe deve realizar esse envio**, e não serão aceitos envios por outros meios ou em repositórios que não os descritos nesta especificação. **Apenas o arquivo PDF do relatório deve ser enviado via SIGAA**.

## Avaliação

A avaliação do trabalho contabilizará nota de até 10,0 pontos na 2ª Unidade da disciplina e será feita de acordo com os seguintes critérios:

| Critério | Avaliação | Pontos |
| :------- | :-------- | -----: |
| Corretude | O validador não aponta violações nas execuções de avaliação | 3,0 |
| Projeto da sincronização | Adequação e uso correto dos mecanismos; implementação distinta das três versões do serviço; política de espera da versão *rw* e partições da *fine* justificadas; encerramento correto do programa | 2,5 |
| Rigor experimental | Variação do número de *threads*, versões e perfis; 5 repetições com média e desvio padrão calculados; consideração de *warm-up* em Java; uso do validador; ambiente de execução informado | 1,5 |
| Qualidade do relatório | Relatório com justificativas apropriadas, interpretação dos resultados e limitações | 2,5 |
| Código e repositório | Histórico de *commits* razoável e organização do código | 0,5 |

A implementação realizada será avaliada de forma semiautomatizada pelo docente, com cargas geradas por sementes diferentes das usadas neste documento, nos dois perfis e com 1, 4 e 64 *threads*. Uma violação de uma regra de segurança nessas execuções (por exemplo, uma operação `get` que devolve um valor anterior a uma operação `put` concluído) reduz a nota de corretude proporcionalmente ao número de execuções afetadas. Um programa que trava ou não termina dentro do limite de **60 segundos** por execução tem sua execução considerada inválida, também afetando o critério de corretude na avaliação.

Relatórios cujas conclusões não se sustentam com base nos dados apresentados perdem pontos no critério de qualidade do relatório. De igual modo, usar um mecanismo que funciona, mas sem justificar por que é adequado, vale menos do que usar um mecanismo mais simples e bem justificado, podendo haver redução de pontos no critério referente ao projeto da sincronização.

## Dúvidas e informações

Caso haja qualquer dúvida, questionamento ou necessidade de informação adicional, bem como identificados erros no gerador, no validador ou em qualquer código-fonte fornecido, deve-se enviar um *e-mail* para <everton.cavalcante@ufrn.br>. As correções nos artefatos serão disponibilizadas a toda a turma com a maior brevidade possível.
