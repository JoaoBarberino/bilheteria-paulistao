# CLAUDE.md

Regras do repositório. Lidas no início de toda sessão do Claude Code.

Projeto: análise de elasticidade-preço da demanda por ingresso no futebol
brasileiro, a partir dos boletins financeiros oficiais de partida.

---

## Regra zero

**Nenhuma conclusão sai sem medida de incerteza.**

Se a amostra não sustenta a afirmação, a resposta correta é dizer que não
sustenta. Resultado que não se distingue de ruído é um achado legítimo e
deve ser reportado como tal.

---

## Integridade de dados

- Toda fusão de bases imprime a contagem de linhas **antes e depois**. Nunca
  usar `how='inner'` sem verificar quantas linhas sobreviveram.
- Todo extrator reporta o que extraiu: número de arquivos lidos, número de
  registros, campos faltantes por arquivo.
- Chaves de junção com nomes de clube passam por dicionário de padronização
  explícito. Qualquer nome que não casar é listado, não descartado em
  silêncio.
- Dado bruto nunca é editado no lugar. Fluxo é `01_raw` → `02_interim` →
  `03_processed`, sem volta.

## Validação estatística

- Antes de reportar qualquer efeito, calcular erro padrão e intervalo de
  confiança.
- Hiperparâmetro e limiar **nunca** são escolhidos no conjunto de teste. Se
  isso acontecer por algum motivo, o número reportado é identificado como
  teto otimista, não como desempenho.
- Ótimo encontrado na borda do espaço de busca é sinal de perseguição de
  ruído. Investigar antes de aceitar.
- Em qualquer modelo com componente temporal, verificar vazamento de
  informação futura — incluindo dentro de calibração e validação cruzada,
  onde o embaralhamento padrão quebra a ordem cronológica.
- Probabilidade de modelo de árvore não é calibrada por padrão. Se for usada
  como probabilidade, calibrar e **verificar** a calibração, não só aplicá-la.
- Acurácia quase nunca é a métrica certa. Escolher a métrica que responde à
  pergunta do projeto e justificar a escolha.

## Especificidades deste projeto

- **Preço médio realizado** = renda bruta ÷ público pagante. Não é tabela de
  preços. Qualquer texto que trate os dois como a mesma coisa está errado.
- **Endogeneidade** entre preço e demanda é o problema central. Nenhuma
  regressão ingênua de público contra preço vale como resultado. A estratégia
  de identificação usada é declarada no README.
- **Jogos esgotados** são observações censuradas. Tratar explicitamente ou
  excluir com justificativa, nunca ignorar.
- **Sócio-torcedor** afeta a contagem de público pagante. Documentar como o
  boletim classifica antes de calcular qualquer preço.

## Código

- Python. pandas, NumPy, SciPy, scikit-learn, Matplotlib, pdfplumber.
- Notebooks numerados por etapa, um arquivo por etapa, nomes descritivos.
- Caminhos relativos. Nada de caminho absoluto da máquina local.
- Dado bruto pesado não vai para o repositório. `.gitignore` configurado.
- Nada de credencial no código.

## Escrita

- Português do Brasil.
- README na ordem: **problema, método, resultado, limitações metodológicas
  conhecidas**. A seção de limitações é obrigatória e não é opcional nem
  resumida.
- Prosa direta, frases curtas. Sem travessão. Sem linguagem promocional.
- Gráfico sem rótulo de eixo e sem unidade não entra.

## Postura

Aponte erro meu quando encontrar, incluindo erro metodológico no que já está
escrito. Discorde quando discordar, com o motivo. Prefiro corrigir cedo a
descobrir tarde.

Não complique o que é simples. O projeto vale pela análise, não pela
infraestrutura.
