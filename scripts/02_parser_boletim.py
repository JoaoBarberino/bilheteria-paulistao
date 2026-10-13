"""Parser de um boletim financeiro da FPF.

Lê o PDF por palavras com coordenadas (pdfplumber) em vez de texto corrido.
Cada valor numérico é atribuído à coluna cujo cabeçalho está mais próximo no
eixo x, o que reassocia preço e arrecadação ao setor da mesma linha mesmo
quando a extração de texto os separa. A tabela de setores pode continuar nas
páginas seguintes; a leitura vai até a linha TOTAIS.

O rótulo de cada linha vira setor, subtipo e categoria. A categoria casa
pelo fim do rótulo, sufixo mais longo primeiro, contra:
- referencias/categorias_boletim.csv, casamento literal;
- referencias/padroes_categoria.csv, expressão regular (Lei, Decreto, ST,
  Avanti, ...).
Guarda de preço: categoria de regime gratuidade, ou padrão com
guarda_preco=sim, só vale para preço zero; com preço acima de zero a linha
vai para revisão.
Entre setor e categoria pode haver um subtipo (faixa de produto, como
"Geral" ou "Carnê"), listado em referencias/subtipos.csv. Se o subtipo tem
regime próprio, o regime segue o subtipo; senão segue a categoria. Um
segmento em caixa mista que não seja subtipo conhecido manda a linha para
revisão. Rótulo sem categoria também vai para revisão, nunca para chute.
P.C.D. é sempre subtipo. Sozinho no fim do rótulo, vira Inteira ou Meia
pela comparação com a Inteira do mesmo setor no mesmo jogo, ou revisão.

Detector preco_quebrado: preço com centavos diferentes de 00, fora os
derivados. Só marca, não reclassifica.

Meia-entrada é metade da Inteira por lei. Meia fora da metade sai de
mercado e vai para revisão, exceto P.C.D. (ver marcar_meia).

Rótulos quebrados em duas linhas ("... - Carnê de" / números /
"Relacionamento") são juntados. Linhas vazias do formulário (sem rótulo,
sem quantidades, R$ 0,00) são descartadas e contadas. Em Fiel Torcedor com
preço impresso R$ 0,00 e arrecadação positiva, o preço é derivado por
arrecadação / vendidos e marcado como preco_derivado.

Extrai o cabeçalho e a tabela, valida cada linha (vendidos * preço =
arrecadação, exceto preço derivado) e a soma contra a linha TOTAIS, e
imprime tudo na tela. Não grava nada em disco.

Uso, a partir da raiz do repositório:
    python scripts/02_parser_boletim.py
    python scripts/02_parser_boletim.py data/01_raw/2026/2026_72.pdf
"""

import csv
import re
import sys
from decimal import Decimal
from pathlib import Path

import pdfplumber

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_PADRAO = RAIZ / "data" / "01_raw" / "2026" / "2026_72.pdf"
PASTA_REFERENCIAS = RAIZ / "referencias"
RODAPE = "Federação Paulista de Futebol"
# Detector de casamento parcial. Não usa str.islower: "º" conta como
# minúscula e aparece em setores ("CAMAROTES 3º ANDAR").
MINUSCULA = re.compile(r"[a-zà-öø-ÿ]")
SUBTIPO_PCD = "P.C.D."
TOLERANCIA_MEIA = Decimal("0.01")
LEI_OU_DECRETO = re.compile(r"(lei|decreto)\b", re.IGNORECASE)
MARCADORES_CATEGORIA = {SUBTIPO_PCD}

COLUNAS = ["A VENDA", "DEVOLVIDOS", "VENDIDOS", "PREÇO", "ARRECADAÇÃO"]

# Palavras na mesma linha visual podem ter "top" ligeiramente diferente.
TOLERANCIA_LINHA = 3.0
# Espaço horizontal acima disso separa blocos na mesma linha
# (ex.: "Jogo: A x B" à esquerda e o nome do estádio à direita).
GAP_BLOCO = 25.0
# A página tem rótulos verticais ("RECEITAS", "DESPESAS") na margem esquerda.
# Palavras que terminam antes deste x ficam fora da tabela. São listadas na
# saída, não descartadas em silêncio.
MARGEM_ESQUERDA = 36.0


def numero_br(texto):
    """'1.344.030,00' -> Decimal('1344030.00'); '1682' -> Decimal('1682')."""
    return Decimal(texto.replace("R$", "").strip().replace(".", "").replace(",", "."))


def eh_numero(texto):
    return re.fullmatch(r"\d{1,3}(\.\d{3})*(,\d{2})?|\d+(,\d{2})?", texto) is not None


def agrupar_linhas(palavras):
    """Agrupa palavras em linhas visuais pela coordenada top."""
    linhas = []
    for p in sorted(palavras, key=lambda p: (p["top"], p["x0"])):
        if linhas and abs(p["top"] - linhas[-1][0]["top"]) <= TOLERANCIA_LINHA:
            linhas[-1].append(p)
        else:
            linhas.append([p])
    return [sorted(l, key=lambda p: p["x0"]) for l in linhas]


def blocos(linha):
    """Divide uma linha em blocos de texto separados por espaço largo."""
    saida, atual = [], [linha[0]]
    for p in linha[1:]:
        if p["x0"] - atual[-1]["x1"] > GAP_BLOCO:
            saida.append(atual)
            atual = [p]
        else:
            atual.append(p)
    saida.append(atual)
    return saida


def texto(ps):
    return " ".join(p["text"] for p in ps)


def extrair_cabecalho(linhas):
    cab = {}
    for i, linha in enumerate(linhas):
        bs = blocos(linha)
        for j, b in enumerate(bs):
            t = texto(b)
            # Rótulo isolado ("Competição:") com o valor no bloco seguinte.
            if t.endswith(":") and j + 1 < len(bs):
                t = f"{t} {texto(bs[j + 1])}"
            if t.startswith("Data:"):
                m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", t)
                if m:
                    cab["data"], cab["horario"] = m.groups()
            elif t.startswith("Jogo:"):
                cab["partida"] = t.removeprefix("Jogo:").strip()
                if " x " in cab["partida"]:
                    cab["mandante"], cab["visitante"] = cab["partida"].split(" x ", 1)
            elif t.startswith("Competição:"):
                cab["competicao"] = t.removeprefix("Competição:").strip()
                # Layout alternativo: "Denominação da" / valor / "Competição:".
                if not cab["competicao"] and i >= 2 and texto(linhas[i - 2]) == "Denominação da":
                    cab["competicao"] = texto(linhas[i - 1])
            elif re.fullmatch(r"\d+/\d{4}", t) and "boletim" not in cab:
                cab["boletim"] = t
            elif t in ("ESTÁDIO", "CIDADE / UF"):
                # O valor fica na linha seguinte, no bloco alinhado ao rótulo.
                x_rotulo = b[0]["x0"]
                seguinte = blocos(linhas[i + 1])
                alvo = min(seguinte, key=lambda s: abs(s[0]["x0"] - x_rotulo))
                chave = "estadio" if t == "ESTÁDIO" else "cidade_uf"
                cab[chave] = texto(alvo)
    if "cidade_uf" in cab:
        cidade, _, uf = cab["cidade_uf"].rpartition(" - ")
        cab["cidade"], cab["uf"] = cidade, uf
    return cab


def _ler_csv(nome):
    with open(PASTA_REFERENCIAS / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def carregar_categorias():
    """Referências de classificação: literais, padrões e subtipos."""
    return {
        "literais": {l["categoria_boletim"]: l for l in _ler_csv("categorias_boletim.csv")},
        "padroes": [{**l, "re": re.compile(l["padrao"])}
                    for l in _ler_csv("padroes_categoria.csv")],
        "subtipos": {l["subtipo"]: l["regime"] or None for l in _ler_csv("subtipos.csv")},
    }


def segmentos(rotulo):
    """Divide o rótulo em ' - ' e remove segmentos vazios.

    'CADEIRA - - - Sócio' -> ['CADEIRA', 'Sócio']
    """
    partes = [p.strip(" -") for p in rotulo.split(" - ")]
    return [p for p in partes if p]


def setor_suspeito(segs_setor):
    """Detector de casamento parcial. Setor é escrito em caixa alta; um
    segmento com letra minúscula, ou um marcador conhecido de categoria,
    indica que parte da categoria ficou no setor. Não classifica: só manda a
    linha para revisão."""
    return any(MINUSCULA.search(s) or s in MARCADORES_CATEGORIA for s in segs_setor)


def casar_categoria(sufixo, refs):
    """Literal primeiro, depois padrões. Devolve a referência ou None."""
    if sufixo in refs["literais"]:
        return {**refs["literais"][sufixo], "guarda_preco": "nao"}
    for p in refs["padroes"]:
        if p["re"].fullmatch(sufixo):
            avanti = sufixo.removeprefix("Avanti").strip(" -") if p["categoria"] == "Avanti" else ""
            return {"categoria": p["categoria"], "regime": p["regime"],
                    "rotulo_avanti": avanti, "guarda_preco": p["guarda_preco"],
                    "preco_regulado": "nao"}
    return None


def separar_setor_categoria(rotulo, refs, preco=None):
    """Separa o rótulo em setor, subtipo e categoria.

    Devolve dict com setor, subtipo, categoria, categoria_boletim, regime,
    rotulo_avanti e status: "casado", "sem_categoria", "subtipo_desconhecido",
    "revisao_preco" (gratuidade com preço acima de zero) ou "pcd_sozinho"
    (resolvido depois por resolver_pcd).
    """
    vazio = {"setor": None, "subtipo": None, "categoria": None, "categoria_boletim": None,
             "regime": None, "rotulo_avanti": None, "preco_regulado": False,
             "lei_preco_zero": False}
    segs = segmentos(rotulo)
    # P.C.D. é condição do comprador, sempre subtipo. Sozinho no fim do
    # rótulo, a categoria sai da aritmética do boletim (resolver_pcd).
    if len(segs) >= 2 and segs[-1] == SUBTIPO_PCD:
        if setor_suspeito(segs[:-1]):
            return {**vazio, "status": "subtipo_desconhecido"}
        return {**vazio, "setor": " - ".join(segs[:-1]), "subtipo": SUBTIPO_PCD,
                "categoria_boletim": SUBTIPO_PCD, "status": "pcd_sozinho"}
    for i in range(1, len(segs)):
        cat = casar_categoria(" - ".join(segs[i:]), refs)
        if cat:
            break
    else:
        return {**vazio, "status": "sem_categoria"}
    prefixo, subtipo = segs[:i], None
    if len(prefixo) >= 2 and prefixo[-1] in refs["subtipos"]:
        subtipo, prefixo = prefixo[-1], prefixo[:-1]
    if setor_suspeito(prefixo):
        return {**vazio, "status": "subtipo_desconhecido"}
    # Guarda: gratuidade não tem preço. Vale para padrões com guarda_preco=sim
    # e para qualquer categoria de regime gratuidade.
    if (cat["guarda_preco"] == "sim" or cat["regime"] == "gratuidade") and preco:
        return {**vazio, "status": "revisao_preco"}
    regime = (refs["subtipos"][subtipo] if subtipo else None) or cat["regime"]
    categoria_boletim = " - ".join(segs[i:])
    regulado = cat["preco_regulado"] == "sim"
    # Categoria de lei ou decreto fora do regime gratuidade (ex.: "Lei
    # nº18.159- Meia entrada"): com preço zero é gratuidade, porque preço zero
    # no subconjunto de mercado estoura o log na estimação; com preço acima de
    # zero fica no regime do dicionário, com preço regulado.
    lei_preco_zero = False
    if regime != "gratuidade" and LEI_OU_DECRETO.match(categoria_boletim) and preco is not None:
        if preco == 0:
            regime, regulado, lei_preco_zero = "gratuidade", False, True
        else:
            regulado = True
    return {"setor": " - ".join(prefixo), "subtipo": subtipo, "categoria": cat["categoria"],
            "categoria_boletim": categoria_boletim, "regime": regime,
            "rotulo_avanti": cat["rotulo_avanti"] or None, "preco_regulado": regulado,
            "lei_preco_zero": lei_preco_zero, "status": "casado"}


def centros_colunas(cab):
    """Centro x de cada cabeçalho de coluna.

    Usa a posição de cada caractere, porque em alguns boletins os títulos
    saem colados numa palavra só ("A VENDADEVOLVIDOSVENDIDOS"). Para
    "A VENDA" usa só "VENDA"; a diferença de centro é de poucos pontos.
    """
    chars = [c for p in cab for c in p["chars"]]
    linha = "".join(c["text"] for c in chars)
    centros = {}
    for nome in COLUNAS:
        alvo = nome.split()[-1]
        i = linha.find(alvo)
        if i < 0:
            raise ValueError(f"Coluna {nome} não encontrada no cabeçalho: {linha!r}")
        centros[nome] = (chars[i]["x0"] + chars[i + len(alvo) - 1]["x1"]) / 2
    return centros


def eh_linha_vazia(registro):
    """Linha em branco do formulário: sem rótulo, sem quantidades, R$ 0,00."""
    return (not registro["rotulo"]
            and not any(c in registro for c in ["A VENDA", "DEVOLVIDOS", "VENDIDOS"])
            and registro.get("PREÇO", 0) == 0 and registro.get("ARRECADAÇÃO", 0) == 0)


def juntar_continuacoes(registros):
    """Junta rótulos quebrados em duas linhas.

    No PDF a linha fica: rótulo sem números, depois números sem rótulo,
    depois o resto do rótulo sem números. Vira um registro só.
    """
    saida, pendente, juntou = [], None, False
    for r in registros:
        tem_valores = any(c in r for c in COLUNAS)
        if r["rotulo"] and not tem_valores:
            if juntou:
                saida[-1]["rotulo"] += " " + r["rotulo"]
                juntou = False
            elif pendente is None:
                pendente = r["rotulo"]
            else:
                saida.append({"rotulo": pendente})
                pendente = r["rotulo"]
            continue
        juntou = False
        if not r["rotulo"] and tem_valores and pendente is not None:
            r = {**r, "rotulo": pendente}
            juntou = True
        elif pendente is not None:
            saida.append({"rotulo": pendente})
        pendente = None
        saida.append(r)
    if pendente is not None:
        saida.append({"rotulo": pendente})
    return saida


def derivar_preco(r):
    """Fiel Torcedor com preço impresso R$ 0,00 e arrecadação positiva: o
    boletim não traz preço unitário. Usa arrecadação / vendidos, que é preço
    médio da linha, não preço de tabela."""
    r["preco_derivado"] = False
    if (r.get("categoria_boletim") == "Fiel Torcedor" and r.get("PREÇO") == 0
            and r.get("ARRECADAÇÃO", 0) > 0 and r.get("VENDIDOS", 0) > 0):
        r["PREÇO"] = (r["ARRECADAÇÃO"] / r["VENDIDOS"]).quantize(Decimal("0.01"))
        r["preco_derivado"] = True


def resolver_pcd(linhas_tab):
    """P.C.D. sozinho: categoria pela aritmética do próprio boletim.

    Compara o preço com a Inteira (sem subtipo) do mesmo setor no mesmo
    jogo. Igual: Inteira. Exatamente metade: Meia. Qualquer outro caso, ou
    setor sem uma única Inteira: revisão ("revisao_pcd"). Grava a decisão
    em pcd_decisao.
    """
    inteiras = {}
    for r in linhas_tab:
        if r["status"] == "casado" and r["categoria"] == "Inteira" and not r["subtipo"]:
            inteiras.setdefault(r["setor"], set()).add(r.get("PREÇO"))
    for r in linhas_tab:
        r["pcd_decisao"] = None
        if r["status"] != "pcd_sozinho":
            continue
        ref = inteiras.get(r["setor"], set())
        preco = r.get("PREÇO")
        if len(ref) == 1 and preco is not None:
            inteira = next(iter(ref))
            if preco == inteira:
                r.update(categoria="Inteira", regime="mercado", status="casado", pcd_decisao="inteira")
                continue
            if preco * 2 == inteira:
                r.update(categoria="Meia", regime="mercado", status="casado", pcd_decisao="meia")
                continue
        r.update(setor=None, subtipo=None, categoria_boletim=None, status="revisao_pcd",
                 pcd_decisao="revisao")


def marcar_meia(linhas_tab):
    """Meia-entrada é, por lei, metade da Inteira.

    meia_fora_da_metade, para categoria Meia: compara com a Inteira de
    regime mercado do mesmo setor e mesmo subtipo; sem ela, com a Inteira
    de mercado do setor sem subtipo. Nunca compara com Inteira de outro
    subtipo (uma Meia local não é medida contra a Inteira de Visitante).
    False se o preço for metade de alguma delas, com tolerância de R$ 0,01;
    True se não for; None se não houver referência, e também para as demais
    categorias.

    Meia fora da metade sai do regime mercado e vai para revisão
    ("revisao_meia"), exceto subtipo P.C.D. (preço de acessibilidade).
    Setor, subtipo e categoria são mantidos para conferência.

    preco_regulado: categoria marcada no dicionário (preço é fração fixa da
    Inteira, medida em referencias/razao_categoria_inteira.csv), categoria de
    lei com preço acima de zero, ou subtipo P.C.D.
    """
    inteiras = {}
    for r in linhas_tab:
        if r["status"] == "casado" and r["categoria"] == "Inteira" and r["regime"] == "mercado":
            inteiras.setdefault((r["setor"], r["subtipo"]), set()).add(r["PREÇO"])
    for r in linhas_tab:
        r["meia_fora_da_metade"] = None
        if r["categoria"] != "Meia" or r.get("PREÇO") is None:
            continue
        ref = inteiras.get((r["setor"], r["subtipo"])) or inteiras.get((r["setor"], None))
        if not ref:
            continue
        fora = all(abs(r["PREÇO"] - i / 2) > TOLERANCIA_MEIA for i in ref)
        r["meia_fora_da_metade"] = fora
        if fora and r["regime"] == "mercado" and r["subtipo"] != SUBTIPO_PCD:
            r.update(regime=None, status="revisao_meia")
    for r in linhas_tab:
        r["preco_regulado"] = bool(r.get("preco_regulado")) or r["subtipo"] == SUBTIPO_PCD


def marcar_preco_quebrado(r):
    """Detector, sem ação: preço com centavos diferentes de 00 que não foi
    derivado. Preço de mercado costuma ser redondo."""
    preco = r.get("PREÇO")
    r["preco_quebrado"] = (not r["preco_derivado"] and preco is not None
                           and preco != preco.to_integral_value())


def extrair_tabela(paginas, refs):
    """paginas: lista de linhas por página. Lê da linha LOCALIDADES da
    primeira página até TOTAIS, atravessando quebras de página. As páginas
    seguintes não repetem o cabeçalho; usa as colunas da primeira."""
    i_cab = next(i for i, l in enumerate(paginas[0]) if texto(l).startswith("LOCALIDADES"))
    centros = centros_colunas(paginas[0][i_cab])
    x_inicio_numeros = min(centros.values()) - 20
    linhas = paginas[0][i_cab + 1:] + [l for pag in paginas[1:] for l in pag]

    brutos, totais, margem = [], None, []
    for linha in linhas:
        margem += [p["text"] for p in linha if p["x1"] < MARGEM_ESQUERDA]
        ps = [p for p in linha if p["x1"] >= MARGEM_ESQUERDA]
        if not ps or texto(ps).startswith(RODAPE):
            continue
        rotulo = texto([p for p in ps if p["x1"] < x_inicio_numeros])
        valores = {}
        for p in ps:
            if p["x1"] < x_inicio_numeros or p["text"] == "R$":
                continue
            # Alguns boletins colam o símbolo no valor: "R$120,00".
            valor = p["text"].removeprefix("R$")
            if not eh_numero(valor):
                raise ValueError(f"Token inesperado na área numérica: {p['text']!r} em {rotulo!r}")
            centro = (p["x0"] + p["x1"]) / 2
            col = min(centros, key=lambda c: abs(centros[c] - centro))
            if col in valores:
                raise ValueError(f"Dois valores na coluna {col} em {rotulo!r}")
            valores[col] = numero_br(valor)
        registro = {"rotulo": rotulo, **valores}
        if rotulo == "TOTAIS":
            totais = registro
            break
        brutos.append(registro)
    if totais is None:
        raise ValueError("Linha TOTAIS não encontrada")

    linhas_tab, descartadas = [], 0
    for registro in juntar_continuacoes(brutos):
        if eh_linha_vazia(registro):
            descartadas += 1
            continue
        registro.update(separar_setor_categoria(registro["rotulo"], refs, registro.get("PREÇO")))
        derivar_preco(registro)
        marcar_preco_quebrado(registro)
        linhas_tab.append(registro)
    resolver_pcd(linhas_tab)
    marcar_meia(linhas_tab)
    return linhas_tab, totais, margem, descartadas


def validar(linhas_tab, totais):
    problemas = []
    for k, r in enumerate(linhas_tab, 1):
        faltando = [c for c in COLUNAS if c not in r]
        if faltando:
            problemas.append(f"linha {k} ({r['rotulo']}): colunas ausentes {faltando}")
            continue
        if not r.get("preco_derivado") and r["VENDIDOS"] * r["PREÇO"] != r["ARRECADAÇÃO"]:
            problemas.append(
                f"linha {k} ({r['rotulo']}): {r['VENDIDOS']} x {r['PREÇO']} = "
                f"{r['VENDIDOS'] * r['PREÇO']}, boletim diz {r['ARRECADAÇÃO']}")
        if r["A VENDA"] - r["DEVOLVIDOS"] != r["VENDIDOS"]:
            problemas.append(
                f"linha {k} ({r['rotulo']}): a venda - devolvidos = "
                f"{r['A VENDA'] - r['DEVOLVIDOS']}, vendidos = {r['VENDIDOS']}")
    for c in ["A VENDA", "DEVOLVIDOS", "VENDIDOS", "ARRECADAÇÃO"]:
        soma = sum(r.get(c, 0) for r in linhas_tab)
        if c not in totais:
            problemas.append(f"TOTAIS: coluna {c} ausente")
        elif soma != totais[c]:
            problemas.append(f"TOTAIS {c}: soma das linhas {soma}, boletim diz {totais[c]}")
    return problemas


def fmt_br(valor, casas=2):
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def imprimir(caminho, cab, linhas_tab, totais, margem, descartadas, problemas):
    print(f"Arquivo: {caminho}")
    print()
    print("CABEÇALHO")
    for chave in ["boletim", "partida", "mandante", "visitante", "data", "horario",
                  "estadio", "cidade", "uf", "competicao"]:
        print(f"  {chave:<11} {cab.get(chave, '<AUSENTE>')}")
    print()
    print("TABELA DE SETORES")
    w_s = max(len(r["setor"] or "?") for r in linhas_tab)
    w_t = max(len(r["subtipo"] or "") for r in linhas_tab + [{"subtipo": "Subtipo"}])
    w_c = max(len(r["categoria"] or "?") for r in linhas_tab)

    def num(r, col, casas=2):
        return fmt_br(r[col], casas) if col in r else "?"

    print(f"  {'#':>2}  {'Setor':<{w_s}}  {'Subtipo':<{w_t}}  {'Categoria':<{w_c}}  {'Regime':<11}  "
          f"{'A venda':>7}  {'Devolv.':>7}  {'Vendidos':>8}  {'Preço':>8}  {'Arrecadação':>13}")
    for k, r in enumerate(linhas_tab, 1):
        print(f"  {k:>2}  {r['setor'] or '?':<{w_s}}  {r['subtipo'] or '':<{w_t}}  "
              f"{r['categoria'] or '?':<{w_c}}  {r['regime'] or '?':<11}  "
              f"{num(r, 'A VENDA', 0):>7}  {num(r, 'DEVOLVIDOS', 0):>7}  "
              f"{num(r, 'VENDIDOS', 0):>8}  {num(r, 'PREÇO'):>8}  "
              f"{num(r, 'ARRECADAÇÃO'):>13}")
    print(f"  {'':>2}  {'TOTAIS':<{w_s}}  {'':<{w_t}}  {'':<{w_c}}  {'':<11}  {fmt_br(totais['A VENDA'], 0):>7}  "
          f"{fmt_br(totais['DEVOLVIDOS'], 0):>7}  {fmt_br(totais['VENDIDOS'], 0):>8}  "
          f"{'':>8}  {fmt_br(totais['ARRECADAÇÃO']):>13}")
    print()
    print(f"Linhas de setor extraídas: {len(linhas_tab)}")
    print(f"Linhas vazias do formulário descartadas: {descartadas}")
    sem_categoria = [r["rotulo"] for r in linhas_tab if r["status"] == "sem_categoria"]
    outros = [f"{r['rotulo']} [{r['status']}]" for r in linhas_tab
              if r["status"] not in ("casado", "sem_categoria")]
    print(f"Rótulos sem categoria no dicionário: {sem_categoria or 'nenhum'}")
    print(f"Outras linhas em revisão: {outros or 'nenhuma'}")
    print(f"Linhas com preço derivado: {sum(r['preco_derivado'] for r in linhas_tab)}")
    leis = sorted({r["categoria_boletim"] for r in linhas_tab
                   if r["regime"] == "gratuidade"})
    print(f"Gratuidades, texto original: {leis or 'nenhuma'}")
    ausentes = [c for c, v in cab.items() if not v]
    print(f"Campos de cabeçalho vazios: {ausentes or 'nenhum'}")
    print(f"Palavras ignoradas na margem esquerda: {' '.join(margem) or 'nenhuma'}")
    print()
    print("VALIDAÇÃO")
    if problemas:
        for p in problemas:
            print(f"  FALHA {p}")
    else:
        print(f"  {len(linhas_tab)} de {len(linhas_tab)} linhas fecham vendidos x preço = arrecadação")
        print("  Soma das linhas bate com TOTAIS em a venda, devolvidos, vendidos e arrecadação")


def processar(caminho, categorias):
    """Lê um boletim inteiro. Devolve dict com cabecalho, linhas, totais,
    margem, descartadas, paginas e problemas."""
    with pdfplumber.open(caminho) as pdf:
        paginas = [agrupar_linhas(pag.extract_words(return_chars=True)) for pag in pdf.pages]
    cab = extrair_cabecalho(paginas[0])
    linhas_tab, totais, margem, descartadas = extrair_tabela(paginas, categorias)
    return {"cabecalho": cab, "linhas": linhas_tab, "totais": totais, "margem": margem,
            "descartadas": descartadas, "paginas": len(paginas),
            "problemas": validar(linhas_tab, totais)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else ARQUIVO_PADRAO
    r = processar(caminho, carregar_categorias())
    cab, linhas_tab, totais = r["cabecalho"], r["linhas"], r["totais"]
    margem, descartadas, problemas = r["margem"], r["descartadas"], r["problemas"]
    imprimir(caminho.relative_to(RAIZ) if caminho.is_absolute() else caminho,
             cab, linhas_tab, totais, margem, descartadas, problemas)
    return linhas_tab, totais


if __name__ == "__main__":
    main()
