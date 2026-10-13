# data/03_processed

## boletins.csv

Gerado por `python scripts/03_lote_boletins.py` a partir dos PDFs em
`data/01_raw`. Uma linha por linha da tabela de setores de cada boletim do
Paulistão A1, 2023 a 2026. A linha TOTAIS não entra. Linhas vazias do
formulário são descartadas.

| Coluna | Conteúdo |
|---|---|
| ano, jogo | Temporada e número do jogo no boletim da FPF |
| boletim, mandante, visitante, data, horario, estadio, cidade, uf, competicao | Cabeçalho do boletim |
| rotulo | Texto da coluna LOCALIDADES como sai do PDF, com rótulos quebrados em duas linhas já juntados |
| setor | Parte do rótulo antes do subtipo e da categoria |
| subtipo | Faixa de produto ou condição do comprador entre setor e categoria (ex.: Geral, Carnê, Cativa, Visitante, P.C.D.). Vazio quando não há |
| categoria | Categoria padronizada |
| categoria_boletim | Texto original da categoria no boletim. Para TC10 guarda o plano (`TC10 VIP`, `TC10 JUNIOR`, ...) |
| regime | mercado, socio, contrato, promocional, gratuidade ou nao_vendido |
| rotulo_avanti | Nome da faixa Avanti (ex.: "50% Desconto"). É rótulo, não desconto praticado |
| status | casado, sem_categoria, subtipo_desconhecido, revisao_preco, revisao_pcd ou revisao_meia |
| a_venda, devolvidos, vendidos | Quantidades do boletim |
| preco | Preço unitário impresso no boletim, ou derivado (ver preco_derivado) |
| preco_derivado | Verdadeiro quando o boletim imprime R$ 0,00 com arrecadação positiva (Fiel Torcedor). Nesse caso preco = arrecadação / vendidos, arredondado a centavos. É preço médio da linha, não preço de tabela |
| preco_quebrado | Detector: preço com centavos diferentes de 00, fora os derivados. Só marca; nada é reclassificado por causa dele |
| preco_regulado | Verdadeiro quando o preço é fração fixa da Inteira ou vem de obrigação legal ou de acessibilidade: categorias marcadas no dicionário (Meia, Meia Promocional, PCR, Menor, Meia legal, Acompanhante, Solidário), categoria de lei com preço acima de zero e subtipo P.C.D. Ver "Preço regulado" abaixo |
| meia_fora_da_metade | Só para categoria Meia. Verdadeiro quando o preço difere em mais de R$ 0,01 da metade da Inteira de mercado do mesmo setor e mesmo subtipo (sem ela, da Inteira do setor sem subtipo). Falso quando bate. Vazio quando não há essa Inteira no jogo |
| arrecadacao | Arrecadação da linha |
| linha_fecha | vendidos x preço = arrecadação. Comparação exata para preço impresso; para preço derivado, tolerância de vendidos x 0,005, por causa do arredondamento a centavos |
| totais_conferem | A soma das linhas do boletim bate com a linha TOTAIS |

Linhas com status diferente de `casado` estão em revisão e sem regime.
Em `revisao_meia`, setor, subtipo e categoria são mantidos para
conferência; nos demais status ficam vazios. A classificação usa os arquivos em
`referencias/`.

`preco` não é preço médio realizado do jogo. Preço médio realizado é
renda bruta ÷ público pagante e é calculado depois, a partir desta base.

## Regimes

| Regime | Definição |
|---|---|
| mercado | Preço definido por jogo, venda aberta ao público |
| socio | Preço por contrato de associação (sócio-torcedor) |
| contrato | Direito de assento de longo prazo, ou preço fixo que não acompanha o jogo |
| promocional | Preço de canal restrito, não ofertado ao público geral, em que o preço registrado no boletim não é necessariamente o preço efetivamente pago |
| gratuidade | Gratuidade legal ou declarada, com preço zero |
| nao_vendido | Venda proibida ou área restrita |

**Subconjunto de elasticidade: só o regime mercado.** Ficam fora socio,
contrato, promocional, gratuidade e nao_vendido.

Quando o subtipo indica produto contratual ou de associação (Carnê,
Sócio, ST, TC10, Avanti, Proprietário, Vitalícia, Smart, Cativa, Carnê
Cadeira Cativa), o regime segue o subtipo. Nos demais subtipos (Geral,
Especial, Promoção, Portão 22, P.C.D., Camarote dos Ídolos, Visitante), o
regime segue a categoria.

### Decisões e motivos

- **TC10, regime socio.** TC10 é "Torcedor Camisa 10", programa de
  sócio-torcedor da Ponte Preta. Os planos do programa são Arquibancada,
  VIP, Cadeira, Conselheiro, Camarote e Júnior, que é a lista de rótulos
  observada na base. Os 26 rótulos distintos ficam em `categoria_boletim`.
- **Palmeiras Pay, regime promocional.** O setor é exclusivo de
  correntistas do banco digital do clube, não aceita meia-entrada, e
  compras no cartão do banco recebem 50% de cashback. O preço efetivo pode
  ser metade do registrado.
- **Único, regime contrato.** Custa R$ 50 com a Inteira do setor a R$ 220
  e também a R$ 400. Não acompanha o jogo. O "Único" de 2024 (CAMAROTE
  TÉRREO OESTE - CORPORATIVO, de R$ 40 a R$ 60) e o de 2025 (CAMAROTE,
  R$ 99 fixo) podem ser produtos diferentes com o mesmo nome. A evidência
  de 2025 são 2 jogos.
- **Camarote como categoria, regime contrato.** R$ 20 fixo em quatro jogos
  do Mirassol em 2026, em setor sem Inteira, com Inteira de arquibancada a
  R$ 240 no mesmo jogo.
- **P.C.D. é sempre subtipo.** É condição do comprador, como Visitante,
  não faixa de preço. Em "P.C.D. - X", subtipo P.C.D. e categoria X.
  Sozinho, a categoria sai da aritmética do boletim: Inteira se o preço for
  igual à Inteira do mesmo setor no mesmo jogo, Meia se for exatamente
  metade, revisão em qualquer outro caso. "P.C.D. - Acompanhante" vira
  subtipo P.C.D. e categoria Acompanhante.
- **Especial é sempre subtipo**, pelo mesmo motivo.
- **Visitante, Cativa e Carnê Cadeira Cativa são subtipo.** Nenhuma
  categoria do dicionário termina em Meia ou Inteira; o que vem antes é
  subtipo. Visitante é condição do comprador; Cativa e Carnê Cadeira
  Cativa são produtos contratuais, com regime contrato.
- **Meia-entrada é metade da Inteira, por lei.** Meia de regime mercado
  fora da metade sai de mercado e vai para revisão (`revisao_meia`).
  Exceção: subtipo P.C.D., que fica em mercado com `preco_regulado`
  verdadeiro, porque é preço de acessibilidade, não erro. Caso das três
  linhas P.C.D. - Meia do Palmeiras (R$ 30 sobre Inteira de R$ 90, R$ 40
  sobre R$ 120, R$ 30 sobre R$ 80).
- **"Especial - Meia" não é mais literal do dicionário.** Tinha sido posto
  a partir de um caso só (2023_55, R$ 50,43). Esse caso é 0,84 da Inteira
  do setor (R$ 60) e agora está em revisão.
- **Menor, regime mercado.** Duas linhas, `ARQUIBANCADA - Promoção - Menor`.

## Preço regulado

No regime mercado, só Inteira, Meia Social e Meia Solidária ficam com
`preco_regulado` falso. As demais categorias de mercado são a Inteira
multiplicada por uma constante: não contêm variação de preço própria, e
incluí-las no modelo mediria desconto legal em vez de comportamento.

A evidência é medida na base, não suposta: a razão entre o preço de cada
categoria e a Inteira do mesmo setor, mesmo subtipo e mesmo jogo, em
`referencias/razao_categoria_inteira.csv` (gerada por
`scripts/03_lote_boletins.py`).

| Categoria | Observações | Ingressos | % exatamente metade | Razão mediana | Mínima | Máxima |
|---|---|---|---|---|---|---|
| Inteira | 2.335 | 898.596 | 0,0 | 1,0000 | 1,0000 | 1,0000 |
| Meia | 2.126 | 1.085.246 | 100,0 | 0,5000 | 0,5000 | 0,5000 |
| Meia Promocional | 54 | 13.916 | 100,0 | 0,5000 | 0,5000 | 0,5000 |
| PCR | 31 | 290 | 96,8 | 0,5000 | 0,5000 | 1,0000 |
| Acompanhante | 16 | 1.019 | 0,0 | 1,0000 | 1,0000 | 1,0000 |
| Meia Social | 10 | 16.870 | 0,0 | 0,5503 | 0,2462 | 0,5633 |
| Solidário | 10 | 4.155 | 0,0 | 0,5506 | 0,5505 | 0,5506 |
| Meia Solidária | 3 | 1.781 | 0,0 | 0,5546 | 0,5505 | 0,8283 |
| Menor | 1 | 1.201 | 100,0 | 0,5000 | 0,5000 | 0,5000 |
| Meia legal | 1 | 368 | 100,0 | 0,5000 | 0,5000 | 0,5000 |

Ressalvas da medição:

- **Meia Solidária não é fração fixa na base.** São 5 linhas, todas de
  2025_63 (Água Santa), 3 com Inteira de referência. As razões são 0,5505,
  0,5546 e 0,8283. Fica com `preco_regulado` falso até decisão.
- **Menor e Meia legal têm uma observação cada.** Menor de 2023_2 não
  entra na medição, porque o setor não tem Inteira com o mesmo subtipo
  (Promoção); o preço dela é igual à Inteira sem subtipo (ver
  Inconsistências).
- **PCR** tem uma observação a 1,0 (2024_48, B- GOL, R$ 60 com Inteira a
  R$ 60).

**Lei ou decreto com preço zero vai para gratuidade.** Categoria cujo
rótulo casa com lei ou decreto e que o dicionário põe em outro regime
(hoje, "Lei nº18.159- Meia entrada, menores de 12 anos") vai para o regime
gratuidade quando o preço é zero, porque preço zero no subconjunto de
mercado estoura o log na estimação. Com preço acima de zero, fica em
mercado com `preco_regulado` verdadeiro. Caso na base: 2026_68, Portuguesa
SAF, 7 ingressos a R$ 0,00.

## Lacuna conhecida

**2025_57** está fora da base. Na extração, o cabeçalho da tabela sai
embaralhado (`VEN A DADEVOLVIDOS...`) e a linha TOTAIS não traz a
arrecadação, então o parser não consegue validar o jogo. Os números não
foram digitados à mão. A base tem 388 dos 389 jogos.

## Inconsistências conhecidas

**2024_40, Inter Limeira x São Paulo, 28/02/2024, Arena BRB.** Sete linhas
com categoria `Gratuidade` têm preço impresso de R$ 89 a R$ 219 e
arrecadação positiva, R$ 212.586 no total (0,075% da receita da base). O
rótulo e o preço se contradizem, e a contradição é da fonte. No setor
CADEIRA HOSPITALITY OESTE, a Gratuidade custa R$ 219, exatamente o preço
modal da Meia Social do mesmo setor no mesmo jogo (246 ingressos). O mesmo
vale para outros cinco setores do jogo: em cada um, o preço da
"Gratuidade" é igual ao da Meia Social do setor (R$ 131, 109, 153, 98 e
89). O sétimo, N3 - CAMAROTES VIP E VVIP, não tem Meia Social.
Hipótese: erro de preenchimento do formulário da FPF. **Hipótese
documentada, não aplicada.** As linhas permanecem em revisão
(`status = revisao_preco`), sem regime.

**2023_2, ARQUIBANCADA - Promoção - Menor a R$ 60,00**, idêntico à Inteira
do setor. O rótulo diz promoção e o preço não tem desconto. 301
ingressos, mantidos em mercado.

**2024_44, ARQUIBANCADA NORTE OREO - Meia a R$ 20 sobre Inteira de R$ 30.**
Setor patrocinado, preço fora da metade legal. 1.831 ingressos, em
revisão (`status = revisao_meia`).
