# Bilheteria do Paulistão: como o público responde ao preço do ingresso

Este projeto mede a elasticidade-preço da demanda por ingresso no
Paulistão Série A1, em 389 boletins financeiros oficiais de 2023 a 2026,
com efeito fixo de partida e de setor.

Quando um setor fica 10% mais caro que os outros setores do mesmo jogo, o
público dele cai cerca de 4,4%. A elasticidade estimada é -0,468, com
intervalo de confiança de 95% de -0,883 a -0,053. A demanda é inelástica
em todo o intervalo.

O número vale para preço relativo entre setores da mesma partida. Esta
base não mede o efeito de uma alta geral de preço, pelo motivo na
limitação 1.

## Problema

Os 20 maiores clubes brasileiros fecharam 2025 com receita somada de cerca
de R$ 15 bilhões e dívida somada de R$ 16 bilhões (levantamento Sports
Value de 2026 e levantamento financeiro anual da EY). A receita cresce e a
dívida cresce mais rápido.

Bilheteria é uma das poucas receitas que o clube controla por inteiro.
Direito de TV depende de contrato coletivo, patrocínio depende de mercado,
transferência depende de terceiros. O preço do ingresso é decisão interna,
tomada toda semana, em geral por intuição e costume.

A pergunta deste projeto é como a demanda por ingresso responde ao preço.

## Método

### Dados

O boletim financeiro de cada partida fica em URL determinística no site da
FPF. A coleta (`scripts/01_coleta_boletins.py`) baixou os 389 boletins das
temporadas 2023 (109 jogos), 2024 (104), 2025 (104) e 2026 (72). Os PDFs da
coleta ficam fora do repositório; quatro boletins ficam versionados em
`tests/fixtures/` para os testes (ver Fonte e direitos).

### Extração e validação

O parser (`scripts/02_parser_boletim.py`) lê o PDF por palavras com
coordenadas e atribui cada valor à coluna cujo cabeçalho está mais
próximo. O lote (`scripts/03_lote_boletins.py`) processou 388 boletins até
o fim e gravou 12.241 linhas em `data/03_processed/boletins.csv`. Um
boletim, 2025_57, ficou fora (ver Limitações).

Duas conferências rodam em todo boletim, e nenhuma falhou. O que elas
garantem é menos do que o nome sugere:

- **Linha contra TOTAIS.** A soma das linhas bate com a linha TOTAIS do
  boletim. Como linhas e TOTAIS são lidos pela mesma regra de proximidade
  de coluna, um deslocamento igual nos dois passaria. A conferência garante
  ausência de deslocamento assimétrico entre linhas e totais, não que a
  coluna esteja certa.
- **Vendidos x preço = arrecadação.** Só é informativa onde preço e
  quantidade são positivos e o preço é impresso: 11.484 das 12.241 linhas.
  Em 673 linhas (5,5%), todas de gratuidade, o preço é zero e a conta é
  0 = 0. Em 84 linhas de Fiel Torcedor o preço é derivado da própria
  arrecadação, e a tolerância aceita é o limite do arredondamento a
  centavos, então ali a conferência não pode falhar.
- **A venda - devolvidos = vendidos** é trivial na base: devolvidos é zero
  nas 12.241 linhas, e a venda é igual a vendidos em todas.

Há testes de regressão em `tests/`, incluindo um gabarito lido à mão do
boletim 2026_72 que cobre vendidos, a venda, devolvidos, preço e
arrecadação de cada linha, e testes de unidade da geometria do parser.

### Classificação

Cada rótulo de setor vira setor, subtipo e categoria, por dicionário
explícito em `referencias/`. Toda categoria recebe um regime: mercado,
sócio, contrato, gratuidade, não vendido ou promocional. Nome de clube e
de estádio também passam por dicionário. Nenhum rótulo, clube ou estádio
fica sem correspondência.

A tabela `referencias/razao_categoria_inteira.csv` mede a razão entre o
preço de cada categoria de mercado e a Inteira de mercado do mesmo setor e
jogo (do mesmo subtipo, ou sem subtipo quando não há), **antes** da guarda
que tira de mercado a Meia fora da metade. A coluna de situação diz onde a
linha terminou. A Inteira não entra na tabela: é a referência, e
compará-la consigo mesma daria 1 por construção.

| Categoria | Situação final | Observações | % exatamente metade | Razão mediana sobre a Inteira | Mínima | Máxima |
|---|---|---|---|---|---|---|
| Meia | mercado | 2.140 | 99,9 | 0,500 | 0,333 | 0,500 |
| Meia | contrato (subtipo Cativa) | 20 | 15,0 | 0,250 | 0,226 | 0,500 |
| Meia | revisão | 6 | 0,0 | 0,437 | 0,224 | 0,841 |
| Meia Promocional | mercado | 54 | 100,0 | 0,500 | 0,500 | 0,500 |
| PCR | mercado | 31 | 96,8 | 0,500 | 0,500 | 1,000 |
| Acompanhante | mercado | 16 | 0,0 | 1,000 | 1,000 | 1,000 |
| Meia Social | mercado | 10 | 0,0 | 0,550 | 0,246 | 0,563 |
| Solidário | mercado | 10 | 0,0 | 0,551 | 0,551 | 0,551 |
| Meia Solidária | mercado | 3 | 0,0 | 0,555 | 0,551 | 0,828 |
| Menor | mercado | 2 | 50,0 | 0,750 | 0,500 | 1,000 |
| Meia legal | mercado | 1 | 100,0 | 0,500 | 0,500 | 0,500 |
| Meia legal | gratuidade | 1 | 0,0 | 0,000 | 0,000 | 0,000 |

Antes da guarda, 2.166 Meias têm Inteira de referência. 2.140 (98,8%)
custam exatamente metade, com tolerância de R$ 0,01. As 26 restantes vão
de 0,224 a 0,841 da Inteira:

- 17 são Meia de cadeira cativa, que o subtipo já põe no regime contrato;
- 6 saem de mercado pela guarda e ficam em revisão (`revisao_meia`), com
  2.693 ingressos, entre elas a Meia patrocinada de 2024_44 a R$ 20 sobre
  Inteira de R$ 30 e quatro Meias escalonadas de 2024_40;
- 3 são P.C.D. - Meia do Palmeiras, que ficam em mercado como preço de
  acessibilidade.

Das Meias que ficaram em mercado, 2.137 de 2.140 são exatamente metade; as
3 restantes são as de P.C.D. O 99,9% da tabela, portanto, é em parte
consequência da guarda, e a dispersão real antes dela é a dos 2.166.

As outras categorias de mercado também são a Inteira vezes uma constante
(1,00 para Acompanhante, 0,50 para Meia Promocional e PCR), ou a Meia
acrescida de 10% de taxa de conveniência (Meia Social e Solidário, cerca
de 0,55 da Inteira e de 1,10 da Meia). As exceções: 4 linhas de Meia
Social num setor de preço escalonado de 2024_40, uma de PCR igual à
Inteira, uma de Meia Solidária a 0,83 e uma de Menor igual à Inteira
(2023_2). Com isso, a decisão de preço do clube em cada setor é
unidimensional: o preço da Inteira. As demais categorias seguem a Inteira
por lei ou por regra fixa e são marcadas como `preco_regulado`.

### Unidade e modelo

A unidade de análise é setor x jogo. O preço é o da Inteira do setor
(regime mercado, preço não regulado). A quantidade é a soma de todos os
ingressos de regime mercado vendidos no setor, inclusive Meia, porque quem
escolhe o setor pelo preço da Inteira pode comprar a Meia. Setor é
identificado por mandante e nome do setor.

A especificação principal (E2) é

log(ingressos) = beta x log(preço) + efeito fixo de partida + efeito fixo de setor

com erro padrão agrupado por jogo. O efeito fixo de partida absorve tudo o
que é comum ao jogo: adversário, data, estádio, momento do campeonato,
nível geral de preço. O efeito fixo de setor absorve o que é permanente no
setor: localização, conforto, tamanho. Sobra para identificar o beta a
variação do preço de um setor em relação aos outros setores do mesmo jogo,
de um jogo para outro.

Antes de qualquer resultado foram declaradas três especificações: E1, só
com efeito fixo de partida; E2, a principal; E3, E2 em cada temporada. As
três estão no resultado. A estimação usa `linearmodels.PanelOLS`, e o beta
de E2 foi conferido contra uma implementação própria (centralização
alternada seguida de OLS): os dois coincidem até a precisão de máquina
(diferença de 3,3 x 10^-16).

Notebooks: `04_descritiva`, `05_modelo` e `06_receita`, em `notebooks/`.

## Resultado

### Elasticidade

| Especificação | beta | Erro padrão | IC 95% | Obs. | Jogos | Setores |
|---|---|---|---|---|---|---|
| E1: efeito fixo de partida | -0,769 | 0,113 | [-0,991; -0,547] | 2.212 | 387 | 337 |
| **E2: partida e setor (principal)** | **-0,468** | **0,212** | **[-0,883; -0,053]** | 2.212 | 387 | 337 |
| E3: E2 em 2023 | -1,191 | 0,434 | [-2,044; -0,338] | 630 | 109 | 179 |
| E3: E2 em 2024 | -1,170 | 0,732 | [-2,610; 0,270] | 602 | 104 | 169 |
| E3: E2 em 2025 | -0,321 | 0,340 | [-0,989; 0,348] | 593 | 103 | 131 |
| E3: E2 em 2026 | 0,267 | 0,498 | [-0,716; 1,249] | 387 | 71 | 129 |

Na especificação principal, o beta é -0,468, com IC 95% de -0,883 a
-0,053. O intervalo inteiro fica entre -1 e 0: a demanda de setor é
inelástica em todo o intervalo, e o intervalo exclui zero por pouco.

Por temporada, o resultado não se distingue de ruído. Só 2023 tem
intervalo que exclui zero, 2026 tem sinal positivo, e os quatro intervalos
se sobrepõem.

### Robustez

| Variante de E2 | beta | IC 95% | Obs. | Jogos | Setores |
|---|---|---|---|---|---|
| Setores com >= 3 observações | -0,485 | [-0,887; -0,083] | 2.023 | 369 | 186 |
| Setores com >= 5 observações | -0,529 | [-0,940; -0,117] | 1.895 | 349 | 150 |
| Sem unidades com ocupação aparente >= 0,90 | -0,811 | [-1,311; -0,312] | 1.765 | 364 | 215 |

Retirar setores com poucas observações não muda o resultado. Retirar as
unidades possivelmente esgotadas torna o beta mais negativo, como se espera
de censura por capacidade, e o intervalo atravessa -1.

Recortes por grupo de mandante:

| Recorte de E2 | beta | Erro padrão | IC 95% | Obs. | Jogos | Setores |
|---|---|---|---|---|---|---|
| Completa | -0,468 | 0,212 | [-0,883; -0,053] | 2.212 | 387 | 337 |
| Sem São Paulo, Palmeiras, Santos e Corinthians | -0,647 | 0,245 | [-1,128; -0,165] | 1.094 | 277 | 182 |
| Só esses quatro | -0,231 | 0,372 | [-0,960; 0,499] | 1.118 | 110 | 155 |

Sem os quatro grandes, o beta fica mais negativo e o intervalo continua
excluindo zero. Só com eles, o intervalo atravessa zero. Os intervalos dos
dois grupos se sobrepõem (ver Limitação 5).

Placebo do filtro de censura: com o preço embaralhado dentro de cada jogo,
60 vezes (semente 20261013), o beta médio fica em -0,001 sem o filtro de
ocupação (desvio-padrão de 0,055 entre as repetições) e em +0,001 com ele
(desvio-padrão de 0,051). O filtro desloca o beta médio em +0,002, muito
menos que a dispersão de uma repetição para outra. O filtro, sozinho, não
produz o resultado. Esse desvio-padrão não é medida de incerteza
alternativa: o embaralhamento destrói a dependência dentro do jogo que o
erro agrupado contabiliza, e o intervalo que vale é o agrupado.

![Resíduo contra valor ajustado de E2](figuras/05_modelo/residuo_ajustado_E2.png)

### O que isso implica

Dentro da faixa de preço já praticada, quando um clube encarece um setor
em relação aos outros setores do mesmo jogo, o público desse setor cai
menos que proporcionalmente, e a receita de mercado do setor sobe. Com o
beta de E2, encarecer cada setor em 10% em relação aos demais do jogo
implica +5,2% na receita de mercado do setor, com faixa de +1,1% a +9,5%
pelo IC 95%. Aplicado à arrecadação de mercado do boletim nas unidades da
estimação (R$ 164,2 milhões de 2026), o percentual corresponde a +R$ 8,5
milhões, com faixa de +R$ 1,8 a +R$ 15,5 milhões.

![Variação da receita do setor com preço relativo alterado](figuras/06_receita/variacao_receita.png)

A evidência para aí. Ela não diz o que acontece numa alta geral de preço,
não diz qual é o preço ótimo e não diz que algum clube cobra pouco (ver
Limitações 1, 8 e 10).

## Limitações metodológicas conhecidas

**1. O beta é de setor, com substituição, não de mercado.** O efeito fixo
de partida absorve todo movimento de preço comum aos setores do jogo, então
o beta de -0,468 é identificado só pelo preço de um setor relativo aos
outros do mesmo jogo. Parte da queda de público quando um setor encarece
são pessoas que trocam de setor. Numa alta geral não há para onde trocar,
e a elasticidade de mercado é menor em módulo que -0,468. Esta base não
mede a elasticidade agregada e não tem como medir: exigiria variação de
preço entre partidas com demanda constante, que é justamente o problema de
endogeneidade que o efeito fixo resolve. O efeito fixo de partida reduz o
desvio-padrão de log(preço) de 0,663 para 0,359, e o de setor, para 0,101.
A estimativa vem dessa variação residual pequena.

**2. Endogeneidade residual.** O clube também escolhe o preço de cada
setor. Se ele encarece o setor que espera vender bem naquele jogo, por
motivo que nem o efeito fixo de partida nem o de setor captura, o beta é
puxado em direção a zero. A base não tem instrumento para separar isso.
Sem modelo, preço e público andam juntos entre setores e jogos
(`figuras/04_descritiva/d_preco_publico_setor.png`), porque clube caro é
clube grande. Os efeitos fixos removem essa parte, não a escolha de preço
dentro do jogo.

**3. Censura por capacidade.** Sem laudo técnico de capacidade dos
estádios, não se sabe que setor esgotou. Em setor esgotado, o público
observado é teto, não demanda, e isso puxa o beta para zero. O filtro usado
é proxy: ocupação aparente é o público do setor no jogo dividido pelo maior
público do mesmo setor na base. Excluir as 447 unidades com ocupação
aparente de 0,90 ou mais leva o beta de -0,468 a -0,811. O máximo
histórico subestima a capacidade, então o filtro é conservador e não
resolve a censura.

**4. Parte pequena da base identifica o modelo.** O subconjunto
identificador (regime mercado, preço não regulado) são 2.290 das 12.241
linhas. O regime mercado é 43,4% dos ingressos da base (2.094.600 de
4.821.229). Sócio é 41,8%, contrato 11,0%, gratuidade 2,0%, não vendido
1,7% e promocional 0,1%. A elasticidade vale para o público de mercado,
não para o sócio-torcedor nem para o contrato de longo prazo.

**5. Concentração.** São Paulo, Palmeiras, Santos e Corinthians somam
50,5% das unidades da estimação (1.118 de 2.212 setor-jogos) e 58,0% dos
ingressos de mercado dessas unidades, em 110 dos 387 jogos. O resultado
não é puxado por esses quatro clubes. Sem eles, o beta é -0,647, com IC
95% de -1,128 a -0,165 (1.094 setor-jogos, 277 jogos, 182 setores). Só com
eles, o beta é -0,231, com IC 95% de -0,960 a +0,499 (1.118 setor-jogos,
110 jogos, 155 setores), e o intervalo atravessa zero. Os dois intervalos
se sobrepõem, então não dá para afirmar que os grupos diferem.
*Hipótese, não testada:* clube grande esgota setor com mais frequência, e
a censura puxa o beta para zero (Limitação 3), o que explicaria um beta
menor em módulo entre os quatro grandes.

**6. Anomalia de composição em 2025.** O público de mercado por jogo cai
de 6.043 em 2024 para 3.928 em 2025 e volta a 5.402 em 2026. Ao ritmo de
2024, faltam 217.870 ingressos de mercado em 2025. A queda atinge 8 dos 14
mandantes presentes nas duas temporadas, com Santos a -77%, Mirassol a
-72%, Botafogo a -64%, São Paulo a -56% e Corinthians a -52%; seis
mandantes ficam estáveis ou sobem. Rótulos novos de sócio e contrato em
2025 somam 4.226 ingressos, e o boletim não ficou menos detalhado (31,0
linhas por boletim em 2024 e 33,3 em 2025). A causa é desconhecida e
nenhuma correção foi aplicada.

**7. Taxa de conveniência de 10%.** Em parte dos boletins ela aparece como
categoria própria (Meia Social, Solidário, a 1,10 da Meia). Em outros pode
estar embutida no preço da Inteira. Isso contamina a comparação de nível de
preço entre clubes (`notebooks/04_descritiva`, gráfico c).

**8. Faixa de preço observada.** A conta de receita só vale dentro da
faixa de preço que cada setor já praticou. Com +20% de preço, 30,0% dos
setor-jogos saem da faixa do próprio setor; com -20%, 51,3%; com +10%,
26,3%; com -10%, 42,8%. 142 dos 337 setores praticaram um só preço real em
toda a base, e para eles qualquer variação é extrapolação.

**9. Dados ausentes e inconsistentes na fonte.** O boletim 2025_57 está
fora da base: o cabeçalho da tabela sai embaralhado na extração e a linha
TOTAIS não traz arrecadação, então o jogo não pode ser validado. Os números
não foram digitados à mão. Em 2024_40 (Inter Limeira x São Paulo), 7 linhas
rotuladas Gratuidade têm preço de R$ 89 a R$ 219 e somam R$ 212.586. O
rótulo e o preço se contradizem na fonte, e as linhas ficam em revisão,
fora de qualquer regime.

**10. Recomendar preço não é entrega deste projeto.** Com beta maior que
-1, a receita de bilheteria cresce sem limite com o preço no modelo de
elasticidade constante. Isso é consequência da forma funcional, não do
mundo, e por isso não há preço ótimo a calcular. A conta de receita também
ignora o que o preço afeta além da bilheteria: consumo dentro do estádio,
conversão de sócio, formação de torcedor no longo prazo, ambiente de
estádio cheio e capacidade. O clube pode estar escolhendo o preço atual de
propósito, por esses motivos. Elasticidade menor que 1 em módulo não prova
que o clube cobra pouco.

## Estrutura do repositório

| Caminho | Conteúdo |
|---|---|
| `scripts/01_coleta_boletins.py` | Download dos boletins |
| `scripts/02_parser_boletim.py` | Parser de um boletim |
| `scripts/03_lote_boletins.py` | Lote dos 389 boletins e padronização |
| `referencias/` | Dicionários de categoria, subtipo, clube e estádio; IPCA; razão sobre a Inteira |
| `data/03_processed/` | Base processada e dicionário de colunas |
| `notebooks/` | Descritiva (04), modelo (05) e receita (06) |
| `figuras/` | Gráficos gerados pelos notebooks |
| `tests/` | Testes de regressão do parser e do lote |
| `requirements.txt` | Pacotes e versões usados |
| `LICENSE` | Licença MIT do código |

## Fonte e direitos

Os boletins são da Federação Paulista de Futebol, baixados da URL
determinística
`https://conteudo.fpf.org.br/Competicoes/{ANO}/3973/boletins-financeiros/{N}/boletins/{N}.pdf`,
em que 3973 é o identificador do Paulistão A1 e N é o número do jogo. A
coleta foi feita em 10/10/2026.

A FPF não concedeu licença para este uso, e os termos de uso do site não
foram verificados.

O código deste repositório é licenciado sob MIT (`LICENSE`). A contribuição
do autor sobre os dados derivados (a base processada em
`data/03_processed/`, os dicionários e tabelas em `referencias/`, os
gráficos e o texto) é licenciada sob CC BY 4.0. Nenhuma das duas licenças
cobre o conteúdo original dos boletins da FPF, cujos direitos continuam da
FPF.

`tests/fixtures/` contém quatro boletins oficiais completos (2023_55,
2024_52, 2025_78 e 2026_72), um por temporada. Eles ficam versionados
porque os testes de regressão precisam de PDFs reais: cobrem a tabela em
várias páginas, linhas vazias do formulário, categorias como PCR e Cativa
e o gabarito lido à mão de 2026_72. Os demais PDFs da coleta não estão no
repositório.

## Como reproduzir

Python 3.12.7. Instale as dependências:

```
python -m pip install -r requirements.txt
```

Na raiz do repositório, rode na ordem:

```
python scripts/01_coleta_boletins.py
python scripts/03_lote_boletins.py
python -m unittest discover tests
```

1. `01_coleta_boletins.py` baixa os 389 boletins da FPF para
   `data/01_raw/{ano}/`. Precisa de rede. Os PDFs não estão no repositório.
   A coleta espera 1 segundo entre requisições (opção `--intervalo`), pula
   o que já está em disco e registra falhas sem interromper.
2. `03_lote_boletins.py` roda o parser em todos os boletins, grava
   `data/03_processed/boletins.csv` e `referencias/razao_categoria_inteira.csv`
   e imprime o relatório do lote. Os dois arquivos só são substituídos se
   nenhum boletim fora da lacuna conhecida (2025_57) abortar; sem os PDFs em
   disco, ou com a coleta incompleta, o lote não toca nos arquivos
   versionados e termina com código de saída 1.
3. Os testes conferem o gabarito de 2026_72, os fixtures em
   `tests/fixtures/` e a padronização do CSV.
4. Depois, abra e execute os notebooks em ordem, num ambiente Jupyter:
   `notebooks/04_descritiva.ipynb`, `05_modelo.ipynb` e `06_receita.ipynb`.
   Os gráficos são gravados em `figuras/`. O Jupyter não está em
   `requirements.txt`, que lista só os pacotes que o código importa.

`scripts/02_parser_boletim.py` também roda sozinho sobre um boletim, para
inspeção: `python scripts/02_parser_boletim.py data/01_raw/2026/2026_72.pdf`.
