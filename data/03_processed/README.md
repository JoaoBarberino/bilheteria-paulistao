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
| subtipo | Faixa de produto entre setor e categoria (ex.: Geral, Carnê). Vazio quando não há |
| categoria | Categoria padronizada |
| categoria_boletim | Texto original da categoria no boletim |
| regime | mercado, socio, contrato, gratuidade ou nao_vendido |
| rotulo_avanti | Nome da faixa Avanti (ex.: "50% Desconto"). É rótulo, não desconto praticado |
| status | casado, sem_categoria, subtipo_desconhecido ou revisao_preco |
| a_venda, devolvidos, vendidos | Quantidades do boletim |
| preco | Preço unitário impresso no boletim, ou derivado (ver preco_derivado) |
| preco_derivado | Verdadeiro quando o boletim imprime R$ 0,00 com arrecadação positiva (Fiel Torcedor). Nesse caso preco = arrecadação / vendidos, arredondado a centavos. É preço médio da linha, não preço de tabela |
| arrecadacao | Arrecadação da linha |
| linha_fecha | vendidos x preço = arrecadação. Falso quando o preço é derivado |
| totais_conferem | A soma das linhas do boletim bate com a linha TOTAIS |

Linhas com status diferente de `casado` estão em revisão: setor,
categoria e regime ficam vazios. A classificação usa os arquivos em
`referencias/`.

`preco` não é preço médio realizado do jogo. Preço médio realizado é
renda bruta ÷ público pagante e é calculado depois, a partir desta base.

## Lacuna conhecida

**2025_57** está fora da base. Na extração, o cabeçalho da tabela sai
embaralhado (`VEN A DADEVOLVIDOS...`) e a linha TOTAIS não traz a
arrecadação, então o parser não consegue validar o jogo. Os números não
foram digitados à mão. A base tem 388 dos 389 jogos.
