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
| subtipo | Faixa de produto ou condição do comprador entre setor e categoria (ex.: Geral, Carnê, P.C.D.). Vazio quando não há |
| categoria | Categoria padronizada |
| categoria_boletim | Texto original da categoria no boletim. Para TC10 guarda o plano (`TC10 VIP`, `TC10 JUNIOR`, ...) |
| regime | mercado, socio, contrato, promocional, gratuidade ou nao_vendido |
| rotulo_avanti | Nome da faixa Avanti (ex.: "50% Desconto"). É rótulo, não desconto praticado |
| status | casado, sem_categoria, subtipo_desconhecido, revisao_preco ou revisao_pcd |
| a_venda, devolvidos, vendidos | Quantidades do boletim |
| preco | Preço unitário impresso no boletim, ou derivado (ver preco_derivado) |
| preco_derivado | Verdadeiro quando o boletim imprime R$ 0,00 com arrecadação positiva (Fiel Torcedor). Nesse caso preco = arrecadação / vendidos, arredondado a centavos. É preço médio da linha, não preço de tabela |
| preco_quebrado | Detector: preço com centavos diferentes de 00, fora os derivados. Só marca; nada é reclassificado por causa dele |
| arrecadacao | Arrecadação da linha |
| linha_fecha | vendidos x preço = arrecadação. Falso quando o preço é derivado |
| totais_conferem | A soma das linhas do boletim bate com a linha TOTAIS |

Linhas com status diferente de `casado` estão em revisão: setor,
categoria e regime ficam vazios. A classificação usa os arquivos em
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
Sócio, ST, TC10, Avanti, Proprietário, Vitalícia, Smart), o regime segue o
subtipo. Nos demais subtipos (Geral, Especial, Promoção, Portão 22,
P.C.D., Camarote dos Ídolos), o regime segue a categoria.

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
- **Menor, regime mercado.** Duas linhas, `ARQUIBANCADA - Promoção - Menor`.

## Lacuna conhecida

**2025_57** está fora da base. Na extração, o cabeçalho da tabela sai
embaralhado (`VEN A DADEVOLVIDOS...`) e a linha TOTAIS não traz a
arrecadação, então o parser não consegue validar o jogo. Os números não
foram digitados à mão. A base tem 388 dos 389 jogos.

## Inconsistência conhecida da FPF

**2024_40, Inter Limeira x São Paulo, 28/02/2024, Arena BRB.** Sete linhas
com categoria `Gratuidade` têm preço impresso de R$ 89 a R$ 219 e
arrecadação positiva, R$ 212.586 no total (0,075% da receita da base). O
rótulo e o preço se contradizem, e a contradição é da fonte. As linhas
ficam em revisão (`status = revisao_preco`), sem regime.
