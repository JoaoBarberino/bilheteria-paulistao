# ipca.csv

IPCA, variação acumulada em 12 meses no mês de dezembro de cada ano (%),
Brasil.

- Fonte: IBGE, Sistema Nacional de Índices de Preços ao Consumidor, SIDRA
  tabela 1737, variável 2265 (IPCA - Variação acumulada em 12 meses).
- Consulta: `https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/202112,202212,202312,202412,202512`
- Data de acesso: 13/10/2026.

Uso: `preco_real` em R$ da temporada 2026. O Paulistão é jogado entre
janeiro e março, então o fator de uma temporada t até a temporada 2026 é o
produto de (1 + IPCA do ano y / 100) para y de t a 2025. Fator 2026 = 1.
O deslocamento de poucos meses entre dezembro e o período dos jogos é uma
aproximação.
