# Limitações e defeitos latentes

As três limitações que mudam como se lê o resultado estão no README
(1. o beta é de setor, não de mercado; 2. fragilidade a escolhas de
especificação; 3. censura por capacidade). As demais estão aqui, com o
mesmo texto e os mesmos números de quando estavam no README.

## Limitações metodológicas

**4. Endogeneidade residual.** O clube também escolhe o preço de cada
setor. Se ele encarece o setor que espera vender bem naquele jogo, por
motivo que nem o efeito fixo de partida nem o de setor captura, o beta é
puxado em direção a zero. A base não tem instrumento para separar isso.
Sem modelo, preço e público andam juntos entre setores e jogos
(`figuras/04_descritiva/d_preco_publico_setor.png`), porque clube caro é
clube grande. Os efeitos fixos removem essa parte, não a escolha de preço
dentro do jogo.

**5. Parte pequena da base identifica o modelo.** O subconjunto
identificador (regime mercado, preço não regulado) são 2.290 das 12.241
linhas. O regime mercado é 43,4% dos ingressos da base (2.094.600 de
4.821.229). Sócio é 41,8%, contrato 11,0%, gratuidade 2,0%, não vendido
1,7% e promocional 0,1%. A elasticidade vale para o público de mercado,
não para o sócio-torcedor nem para o contrato de longo prazo.

**6. Concentração.** São Paulo, Palmeiras, Santos e Corinthians somam
50,5% das unidades da estimação (1.118 de 2.212 setor-jogos) e 58,0% dos
ingressos de mercado dessas unidades, em 110 dos 387 jogos. Com erro
agrupado por jogo e setor, sem eles o beta é -0,647, com IC 95% de -1,413 a
+0,119 (1.094 setor-jogos, 277 jogos, 182 setores). Só com eles, o beta é
-0,231, com IC 95% de -0,924 a +0,463 (1.118 setor-jogos, 110 jogos, 155
setores). Os dois intervalos contêm zero e se sobrepõem, então não dá para
afirmar que os grupos diferem nem que algum deles tem elasticidade
distinguível de zero. O ponto mais negativo sem os quatro grandes indica
que o resultado não é puxado por eles.
*Hipótese, não testada:* clube grande esgota setor com mais frequência, e
a censura puxa o beta para zero (Limitação 3, no README), o que explicaria um beta
menor em módulo entre os quatro grandes.

**7. Anomalia de composição em 2025.** O público de mercado por jogo cai
de 6.043 em 2024 para 3.928 em 2025 e volta a 5.402 em 2026. Ao ritmo de
2024, faltam 217.870 ingressos de mercado em 2025. A queda atinge 8 dos 14
mandantes presentes nas duas temporadas, com Santos a -77%, Mirassol a
-72%, Botafogo a -64%, São Paulo a -56% e Corinthians a -52%; seis
mandantes ficam estáveis ou sobem. Rótulos novos de sócio e contrato em
2025 somam 4.226 ingressos, e o boletim não ficou menos detalhado (31,0
linhas por boletim em 2024 e 33,3 em 2025). A causa é desconhecida e
nenhuma correção foi aplicada.

**8. Taxa de conveniência de 10%.** Em parte dos boletins ela aparece como
categoria própria (Meia Social, Solidário, a 1,10 da Meia). Em outros pode
estar embutida no preço da Inteira. Isso contamina a comparação de nível de
preço entre clubes (`notebooks/04_descritiva`, gráfico c).

**9. Faixa de preço observada.** A conta de receita só vale dentro da
faixa de preço que cada setor já praticou. Com +20% de preço, 30,0% dos
setor-jogos saem da faixa do próprio setor; com -20%, 51,3%; com +10%,
26,3%; com -10%, 42,8%. 142 dos 337 setores praticaram um só preço real em
toda a base, e para eles qualquer variação é extrapolação.

**10. Dados ausentes e inconsistentes na fonte.** O boletim 2025_57 está
fora da base: o cabeçalho da tabela sai embaralhado na extração e a linha
TOTAIS não traz arrecadação, então o jogo não pode ser validado. Os números
não foram digitados à mão. Em 2024_40 (Inter Limeira x São Paulo), 7 linhas
rotuladas Gratuidade têm preço de R$ 89 a R$ 219 e somam R$ 212.586. O
rótulo e o preço se contradizem na fonte, e as linhas ficam em revisão,
fora de qualquer regime.

**11. Recomendar preço não é entrega deste projeto.** Com coeficiente de
arrecadação positivo e constante, a receita do setor cresce sem limite com
o preço no modelo. Isso é consequência da forma funcional, não do mundo, e
por isso não há preço ótimo a calcular. Além disso, o intervalo do
coeficiente contém zero, e nem o sinal do efeito sobre a receita está
estabelecido. A conta de receita também
ignora o que o preço afeta além da bilheteria: consumo dentro do estádio,
conversão de sócio, formação de torcedor no longo prazo, ambiente de
estádio cheio e capacidade. O clube pode estar escolhendo o preço atual de
propósito, por esses motivos.

## Defeitos latentes

Nenhum destes modos de falha contaminou a base atual. São riscos para a
próxima temporada, quando entrarem boletins com rótulos novos.

**Padrões abertos absorvem a cauda da categoria.** Os padrões de
`referencias/padroes_categoria.csv` são testados do sufixo mais longo para
o mais curto, e vários são abertos (`Avanti\b.*`, `ST - .+`, `TC10 .+`,
`Smart .+`, `Proprietário.*`). Um rótulo como
`SETOR - Avanti - 50% Desconto - Meia` sai como categoria Avanti, regime
sócio, e a meia-entrada some sem a linha ir para revisão. O mesmo vale
para `ST - BRANCO - Meia`, `TC10 VIP - Meia`, `Smart Especial - Meia` e
`Proprietário Gold - Meia`, conferidos com o parser atual. O padrão de Lei
também é aberto, mas com preço acima de zero a guarda de preço manda a
linha para revisão; com preço zero, a cauda é absorvida como gratuidade.
Nenhum rótulo real da base tem esse formato hoje. A afirmação de que
nenhum rótulo fica sem categoria, portanto, não quer dizer que todo rótulo
esteja certo: um rótulo novo com essa cauda **não** fica sem
correspondência, e é exatamente esse o problema.

**Detecção de subtipo depende da caixa alta.** O detector de casamento
parcial só dispara quando sobra no setor um segmento com letra minúscula.
Um subtipo novo escrito em caixa alta (por exemplo `SETOR - NOVO SUBTIPO -
Meia`) vira parte do setor e cria um setor espúrio. Um setor legítimo
escrito em caixa mista (`Setor Novo - Inteira`) vai para revisão. Dos 318
setores atuais, nenhum tem letra minúscula, então a heurística depende de
a FPF manter os setores em caixa alta.

**Conferência de TOTAIS com coluna ausente.** A soma que é conferida
contra a linha TOTAIS usa zero como valor padrão quando falta uma coluna
na linha. Uma linha com coluna faltando ainda passa na conferência de
totais, se o boletim também tiver deixado a coluna em branco no total. A
conferência linha a linha acusa a coluna ausente, mas a de totais não.
Nenhuma linha da base atual tem coluna ausente.
