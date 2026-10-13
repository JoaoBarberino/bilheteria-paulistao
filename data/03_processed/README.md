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
| preco_regulado | Verdadeiro para categoria Meia e para subtipo P.C.D. O preço vem de obrigação legal ou de acessibilidade, não de decisão comercial do clube |
| meia_fora_da_metade | Só para categoria Meia. Verdadeiro quando o preço difere em mais de R$ 0,01 da metade da Inteira de mercado do mesmo setor e mesmo subtipo (sem ela, da Inteira do setor sem subtipo). Falso quando bate. Vazio quando não há essa Inteira no jogo |
| arrecadacao | Arrecadação da linha |
| linha_fecha | vendidos x preço = arrecadação. Falso quando o preço é derivado |
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
