"""Parser de um boletim financeiro da FPF.

Lê o PDF por palavras com coordenadas (pdfplumber) em vez de texto corrido.
Cada valor numérico é atribuído à coluna cujo cabeçalho está mais próximo no
eixo x, o que reassocia preço e arrecadação ao setor da mesma linha mesmo
quando a extração de texto os separa. A tabela de setores pode continuar nas
páginas seguintes; a leitura vai até a linha TOTAIS.

O rótulo de cada linha é separado em setor e categoria casando a categoria
pelo fim do rótulo (cada categoria tem um regime: mercado, socio,
contrato, gratuidade ou nao_vendido):
- segmento que começa com "Lei" vira "Gratuidade legal" (leis municipais de
  gratuidade variam por cidade, então o casamento é por padrão);
- o resto casa com o dicionário em referencias/categorias_boletim.csv, sufixo
  mais longo primeiro. Rótulo que não casa fica sem setor e sem categoria e é
  listado;
- se sobrar no setor um segmento em caixa mista ou "P.C.D.", o casamento é
  parcial e é rejeitado, indo para a mesma lista de revisão.

Linhas vazias do formulário (sem rótulo, sem quantidades, R$ 0,00) são
descartadas e contadas. Extrai o cabeçalho e a tabela, valida cada linha
(vendidos * preço = arrecadação) e a soma contra a linha TOTAIS, e imprime
tudo na tela. Não grava nada em disco.

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
ARQUIVO_CATEGORIAS = RAIZ / "referencias" / "categorias_boletim.csv"

GRATUIDADE_LEGAL = "Gratuidade legal"
# "Lei n. 4046/14", "Lei nº9266/10", "Lei 6145/18", "LEI ..."
PADRAO_LEI = re.compile(r"^lei\b", re.IGNORECASE)
RODAPE = "Federação Paulista de Futebol"
# Detector de casamento parcial. Não usa str.islower: "º" conta como
# minúscula e aparece em setores ("CAMAROTES 3º ANDAR").
MINUSCULA = re.compile(r"[a-zà-öø-ÿ]")
MARCADORES_CATEGORIA = {"P.C.D."}

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


def carregar_categorias(caminho=ARQUIVO_CATEGORIAS):
    """Dicionário {categoria como aparece no boletim: linha do CSV}."""
    with open(caminho, encoding="utf-8", newline="") as f:
        return {l["categoria_boletim"]: l for l in csv.DictReader(f)}


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


def separar_setor_categoria(rotulo, categorias):
    """Casa a categoria pelo fim do rótulo.

    Ordem: primeiro um segmento que começa com "Lei" (gratuidade legal, por
    padrão); depois o dicionário, sufixo mais longo primeiro. O setor precisa
    ter ao menos um segmento. Se o setor que sobra for suspeito, o casamento
    é rejeitado. Devolve dict com setor, categoria, categoria_boletim, regime,
    rotulo_avanti e status ("casado", "parcial_rejeitado", "sem_categoria").
    """
    vazio = {"setor": None, "categoria": None, "categoria_boletim": None,
             "regime": None, "rotulo_avanti": None}
    segs = segmentos(rotulo)
    achado = None
    for i in range(1, len(segs)):
        if PADRAO_LEI.match(segs[i]):
            achado = i, {"categoria": GRATUIDADE_LEGAL, "regime": "gratuidade",
                         "rotulo_avanti": None}
            break
    if achado is None:
        for i in range(1, len(segs)):
            sufixo = " - ".join(segs[i:])
            if sufixo in categorias:
                c = categorias[sufixo]
                achado = i, {"categoria": c["categoria"], "regime": c["regime"],
                             "rotulo_avanti": c["rotulo_avanti"] or None}
                break
    if achado is None:
        return {**vazio, "status": "sem_categoria"}
    i, cat = achado
    if setor_suspeito(segs[:i]):
        return {**vazio, "status": "parcial_rejeitado"}
    return {"setor": " - ".join(segs[:i]), "categoria_boletim": " - ".join(segs[i:]),
            **cat, "status": "casado"}


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


def extrair_tabela(paginas, categorias):
    """paginas: lista de linhas por página. Lê da linha LOCALIDADES da
    primeira página até TOTAIS, atravessando quebras de página. As páginas
    seguintes não repetem o cabeçalho; usa as colunas da primeira."""
    i_cab = next(i for i, l in enumerate(paginas[0]) if texto(l).startswith("LOCALIDADES"))
    centros = centros_colunas(paginas[0][i_cab])
    x_inicio_numeros = min(centros.values()) - 20
    linhas = paginas[0][i_cab + 1:] + [l for pag in paginas[1:] for l in pag]

    linhas_tab, totais, margem, descartadas = [], None, [], 0
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
        if eh_linha_vazia(registro):
            descartadas += 1
            continue
        registro.update(separar_setor_categoria(rotulo, categorias))
        linhas_tab.append(registro)
    if totais is None:
        raise ValueError("Linha TOTAIS não encontrada")
    return linhas_tab, totais, margem, descartadas


def validar(linhas_tab, totais):
    problemas = []
    for k, r in enumerate(linhas_tab, 1):
        faltando = [c for c in COLUNAS if c not in r]
        if faltando:
            problemas.append(f"linha {k} ({r['rotulo']}): colunas ausentes {faltando}")
            continue
        if r["VENDIDOS"] * r["PREÇO"] != r["ARRECADAÇÃO"]:
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
    w_c = max(len(r["categoria"] or "?") for r in linhas_tab)
    print(f"  {'#':>2}  {'Setor':<{w_s}}  {'Categoria':<{w_c}}  {'Regime':<11}  {'A venda':>7}  "
          f"{'Devolv.':>7}  {'Vendidos':>8}  {'Preço':>8}  {'Arrecadação':>13}")
    for k, r in enumerate(linhas_tab, 1):
        print(f"  {k:>2}  {r['setor'] or '?':<{w_s}}  {r['categoria'] or '?':<{w_c}}  "
              f"{r['regime'] or '?':<11}  "
              f"{fmt_br(r['A VENDA'], 0):>7}  {fmt_br(r['DEVOLVIDOS'], 0):>7}  "
              f"{fmt_br(r['VENDIDOS'], 0):>8}  {fmt_br(r['PREÇO']):>8}  "
              f"{fmt_br(r['ARRECADAÇÃO']):>13}")
    print(f"  {'':>2}  {'TOTAIS':<{w_s}}  {'':<{w_c}}  {'':<11}  {fmt_br(totais['A VENDA'], 0):>7}  "
          f"{fmt_br(totais['DEVOLVIDOS'], 0):>7}  {fmt_br(totais['VENDIDOS'], 0):>8}  "
          f"{'':>8}  {fmt_br(totais['ARRECADAÇÃO']):>13}")
    print()
    print(f"Linhas de setor extraídas: {len(linhas_tab)}")
    print(f"Linhas vazias do formulário descartadas: {descartadas}")
    sem_categoria = [r["rotulo"] for r in linhas_tab if r["status"] == "sem_categoria"]
    parciais = [r["rotulo"] for r in linhas_tab if r["status"] == "parcial_rejeitado"]
    print(f"Rótulos sem categoria no dicionário: {sem_categoria or 'nenhum'}")
    print(f"Casamentos parciais rejeitados: {parciais or 'nenhum'}")
    leis = sorted({r["categoria_boletim"] for r in linhas_tab
                   if r["categoria"] == GRATUIDADE_LEGAL})
    print(f"Gratuidade legal, texto original: {leis or 'nenhuma'}")
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
