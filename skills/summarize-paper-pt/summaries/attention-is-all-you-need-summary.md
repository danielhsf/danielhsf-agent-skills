# Attention Is All You Need

> **Autores:** Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin (Google Brain, Google Research e University of Toronto) · **Ano:** 2017 · **Publicado em:** NIPS 2017 (31st Conference on Neural Information Processing Systems)
> **Link/DOI:** arXiv:1706.03762 · Código: https://github.com/tensorflow/tensor2tensor

## Resumo em uma frase
O artigo propõe o *Transformer*, uma arquitetura de rede neural para tradução e outras tarefas de sequência que abandona completamente a recorrência e as convoluções, apoiando-se apenas em mecanismos de *attention* — e com isso treina muito mais rápido e alcança resultados estado-da-arte.

## Contexto e problema
- As melhores abordagens da época para *sequence transduction* (transformar uma sequência em outra, como traduzir um texto) eram redes recorrentes (*RNNs*, *LSTMs*, *GRUs*) e convolucionais.
- Redes recorrentes processam a sequência **posição por posição**, de forma inerentemente sequencial: para calcular o estado da palavra atual, é preciso ter calculado o da anterior. Isso impede a paralelização dentro de cada exemplo e vira gargalo em sequências longas.
- O *attention* — mecanismo que permite ao modelo "olhar" para qualquer parte da entrada independentemente da distância — já era usado, mas quase sempre **acoplado** a uma rede recorrente. Faltava um modelo que dependesse *só* de *attention*.

## Metodologia
O Transformer mantém a estrutura *encoder-decoder* clássica (um bloco lê a entrada, outro gera a saída palavra a palavra, de modo *auto-regressivo* — cada palavra gerada vira entrada para a próxima), mas troca a recorrência por *attention*. Componentes principais:

- **Self-attention (auto-atenção):** mecanismo que relaciona diferentes posições de uma *mesma* sequência para construir sua representação. Cada palavra pode "consultar" todas as outras diretamente, em um único passo — daí a paralelização e os caminhos curtos entre dependências distantes.
- **Scaled Dot-Product Attention:** o coração do modelo. Cada posição gera uma *query* (Q), e cada posição oferece uma *key* (K) e um *value* (V). A relevância entre uma query e uma key é o produto escalar entre elas; os pesos resultantes ponderam os values:

  $$\text{Attention}(Q,K,V) = \text{softmax}\!\left(\frac{QK^{T}}{\sqrt{d_k}}\right)V$$

  - $Q, K, V$: matrizes de *queries*, *keys* e *values*.
  - $QK^{T}$: mede a compatibilidade entre cada query e cada key (quão relevante uma posição é para outra).
  - $\sqrt{d_k}$: fator de escala ($d_k$ = dimensão das keys). Sem ele, para dimensões grandes os produtos escalares ficam muito grandes e empurram o *softmax* para regiões de gradiente quase nulo, atrapalhando o treino.
  - *softmax*: transforma as compatibilidades em pesos que somam 1; o resultado é uma média ponderada dos values.

- **Multi-Head Attention:** em vez de uma única atenção, o modelo projeta Q, K e V em $h = 8$ "cabeças" paralelas de menor dimensão, aplica a atenção em cada uma e concatena. Isso deixa o modelo atender simultaneamente a informações de diferentes *subespaços de representação* (p. ex. relações sintáticas e semânticas distintas).
- **Positional Encoding:** como não há recorrência nem convolução, o modelo não sabe a *ordem* das palavras. Os autores somam às *embeddings* de entrada vetores baseados em funções seno e cosseno de frequências diferentes, injetando informação de posição.
- **Feed-forward por posição:** cada camada tem também uma pequena rede totalmente conectada (duas transformações lineares com ReLU no meio) aplicada a cada posição.
- **Detalhes de arquitetura:** *encoder* e *decoder* têm $N = 6$ camadas empilhadas; $d_{model} = 512$; conexões residuais + *layer normalization* em cada sub-camada; no *decoder*, a auto-atenção é mascarada para impedir que uma posição "veja o futuro".

**Configuração experimental:** treinado no WMT 2014 inglês→alemão (~4,5 mi de pares de frases) e inglês→francês (~36 mi), com *byte-pair encoding*. Hardware: 1 máquina com 8 GPUs NVIDIA P100. O modelo *base* treinou por ~12 h (100 mil passos); o modelo *big*, por 3,5 dias (300 mil passos). Otimizador Adam com *learning rate* variável (*warmup* + decaimento), *dropout* e *label smoothing* como regularização.

## Resultados principais
Tradução automática (BLEU — quanto maior, melhor):

| Modelo | EN→DE | EN→FR | Custo de treino (FLOPs) |
|---|---|---|---|
| GNMT + RL (Google) | 24,6 | 39,92 | 2,3·10¹⁹ / 1,4·10²⁰ |
| ConvS2S | 25,16 | 40,46 | 9,6·10¹⁸ / 1,5·10²⁰ |
| GNMT + RL Ensemble | 26,30 | 41,16 | 1,8·10²⁰ / 1,1·10²¹ |
| **Transformer (base)** | 27,3 | 38,1 | **3,3·10¹⁸** |
| **Transformer (big)** | **28,4** | **41,8** | 2,3·10¹⁹ |

- No EN→DE, o Transformer *big* alcança **28,4 BLEU**, superando em mais de **2 BLEU** todos os modelos anteriores, inclusive *ensembles*.
- No EN→FR, atinge **41,8 BLEU** (a Tabela 2 reporta 41,8; o texto da seção de resultados menciona 41,0), um novo estado-da-arte para modelo único, a **menos de 1/4 do custo** de treino do melhor modelo anterior.
- Mesmo o modelo *base* supera todos os modelos publicados até então, a uma fração do custo computacional.
- **Estudos de ablação (Tabela 3):** atenção com uma única cabeça é ~0,9 BLEU pior que a melhor configuração, mas cabeças demais também pioram; reduzir $d_k$ prejudica a qualidade; modelos maiores são melhores; *dropout* ajuda contra *overfitting*; *embeddings* de posição aprendidas dão resultado praticamente idêntico ao das funções senoidais.
- **Generalização:** aplicado a *constituency parsing* do inglês (Penn Treebank), o Transformer atinge 91,3 F1 (só WSJ) e 92,7 F1 (semi-supervisionado), superando quase todos os modelos anteriores mesmo com pouco ajuste específico à tarefa.

## Conclusões e limitações
- O Transformer é o **primeiro modelo de transdução de sequências baseado inteiramente em atenção**, substituindo as camadas recorrentes por *multi-head self-attention*.
- Principais ganhos: treino significativamente mais rápido (por ser paralelizável) e qualidade estado-da-arte em tradução.
- Os autores se dizem animados para estender a abordagem a outras modalidades (imagens, áudio, vídeo) e a investigar mecanismos de atenção **local/restrita** para lidar eficientemente com entradas e saídas muito grandes — reconhecendo implicitamente que a atenção plena tem custo $O(n^2 \cdot d)$, quadrático no comprimento da sequência.
- Tornar a geração menos sequencial é apontado como objetivo de pesquisa futura (o *decoder* ainda gera palavra a palavra).

## Por que este artigo importa
- Introduziu a arquitetura **Transformer**, que se tornou a base de praticamente toda a IA moderna de linguagem — de BERT e GPT aos LLMs atuais.
- Mostrou que **paralelização e atenção** podem substituir a recorrência sem perda de qualidade, destravando o treino em escala que viabilizou os modelos gigantes de hoje.
- A ideia de *self-attention* extrapolou o NLP e hoje é central também em visão computacional, áudio e modelos multimodais.
