"""Roda o parser nos boletins de data/01_raw e grava data/03_processed/boletins.csv.

Uma linha por linha da tabela de setores de cada boletim. Linhas em
revisão (sem categoria, subtipo desconhecido, Lei ou Decreto com preço)
entram no CSV com setor e categoria vazios e o status correspondente.
Arquivos que o parser não consegue ler até TOTAIS são abortados e listados.

Lacuna conhecida: 2025_57 fica fora da base (ver LACUNAS_CONHECIDAS).

Os dois arquivos versionados (boletins.csv e
referencias/razao_categoria_inteira.csv) são gravados primeiro em arquivo
temporário e só substituem os versionados depois da verificação de
completude: nenhum abortado fora das lacunas conhecidas, CSV com dados e
tabela de razão não vazia. Se a verificação falhar, os versionados ficam
intactos e o script termina com código de saída 1.

No fim imprime o relatório do lote: arquivos lidos, abortados, falhas de
validação, linhas descartadas, rótulos em revisão, setores distintos,
distribuição por regime e número de jogos distintos.

Uso, a partir da raiz do repositório:
    python scripts/03_lote_boletins.py
    python scripts/03_lote_boletins.py --pasta-raw outro/diretorio
"""

import argparse
import csv
import importlib.util
import os
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from statistics import median
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "01_raw"
SAIDA = RAIZ / "data" / "03_processed" / "boletins.csv"
SAIDA_RAZAO = RAIZ / "referencias" / "razao_categoria_inteira.csv"

JOGOS_POR_ANO = {2023: 109, 2024: 104, 2025: 104, 2026: 72}

# Boletins que ficam fora da base, com o motivo. Não entram números à mão.
LACUNAS_CONHECIDAS = {
    "2025_57.pdf": "cabeçalho da tabela sai embaralhado na extração "
                   "('VEN A DADEVOLVIDOS...') e a linha TOTAIS não traz arrecadação",
}

# O nome do módulo começa com número, então não dá para usar import comum.
_spec = importlib.util.spec_from_file_location(
    "parser_boletim", RAIZ / "scripts" / "02_parser_boletim.py")
parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parser)

CAMPOS_CABECALHO = ["boletim", "mandante", "visitante", "data", "horario",
                    "estadio", "cidade", "uf", "competicao"]
# Colunas do cabeçalho no CSV: o texto do boletim fica em *_boletim e a
# forma padronizada pelos dicionários de referencias/ fica no nome curto.
COLUNAS_CABECALHO_CSV = ["boletim", "mandante_boletim", "mandante", "visitante_boletim",
                         "visitante", "data", "horario", "estadio_boletim", "estadio",
                         "cidade_boletim", "cidade", "uf", "competicao"]
COLUNAS_CSV = (["ano", "jogo"] + COLUNAS_CABECALHO_CSV +
               ["rotulo", "setor", "subtipo", "categoria", "categoria_boletim", "regime",
                "rotulo_avanti", "status", "a_venda", "devolvidos", "vendidos",
                "preco", "preco_derivado", "preco_quebrado", "preco_regulado",
                "meia_fora_da_metade", "arrecadacao", "linha_fecha", "totais_conferem"])
REVISAO = "(revisão)"
REGIMES = ["mercado", "socio", "contrato", "promocional", "gratuidade", "nao_vendido", REVISAO]


def linha_fecha(l):
    """vendidos x preço = arrecadação. Exato quando o preço é impresso; com
    tolerância de vendidos x 0,005 quando é derivado (arredondado a
    centavos), para que uma falha de verdade não se esconda nessas linhas."""
    if not all(c in l for c in ("VENDIDOS", "PREÇO", "ARRECADAÇÃO")):
        return False
    diferenca = abs(l["VENDIDOS"] * l["PREÇO"] - l["ARRECADAÇÃO"])
    if l["preco_derivado"]:
        return diferenca <= l["VENDIDOS"] * Decimal("0.005")
    return diferenca == 0


def tabela_razao(linhas_por_jogo):
    """Razão entre o preço e a Inteira, e entre o preço e a Meia, do mesmo
    setor e mesmo subtipo, no mesmo jogo, por categoria de regime mercado.
    Cada razão só usa linha com uma única referência, de preço acima de
    zero. A razão sobre a Meia é a que revela taxa de conveniência sobre a
    meia-entrada."""
    obs = {"Inteira": defaultdict(list), "Meia": defaultdict(list)}
    for linhas in linhas_por_jogo:
        ref = {"Inteira": defaultdict(set), "Meia": defaultdict(set)}
        for l in linhas:
            if l["status"] == "casado" and l["regime"] == "mercado" and l["categoria"] in ref:
                ref[l["categoria"]][(l["setor"], l["subtipo"])].add(l["PREÇO"])
        for l in linhas:
            if l["regime"] != "mercado" or "PREÇO" not in l:
                continue
            for base in ("Inteira", "Meia"):
                r = ref[base].get((l["setor"], l["subtipo"]), set())
                if len(r) != 1 or next(iter(r)) == 0:
                    continue
                preco_ref = next(iter(r))
                obs[base][l["categoria"]].append(
                    (l["PREÇO"] / preco_ref, l["VENDIDOS"],
                     abs(l["PREÇO"] - preco_ref / 2) <= Decimal("0.01")))
    tabela = []
    for cat, v in sorted(obs["Inteira"].items(), key=lambda x: -len(x[1])):
        razoes = [x[0] for x in v]
        m = [x[0] for x in obs["Meia"].get(cat, [])]
        tabela.append({
            "categoria": cat, "observacoes": len(v), "ingressos": sum(x[1] for x in v),
            "pct_exatamente_metade": f"{100 * sum(x[2] for x in v) / len(v):.1f}",
            "razao_mediana": f"{median(razoes):.4f}", "razao_minima": f"{min(razoes):.4f}",
            "razao_maxima": f"{max(razoes):.4f}",
            "observacoes_sobre_meia": len(m),
            "razao_meia_mediana": f"{median(m):.4f}" if m else "",
            "razao_meia_minima": f"{min(m):.4f}" if m else "",
            "razao_meia_maxima": f"{max(m):.4f}" if m else ""})
    return tabela


def carregar_padronizacao():
    """Dicionários de clube e estádio (referencias/clubes.csv e estadios.csv)."""
    with open(RAIZ / "referencias" / "clubes.csv", encoding="utf-8", newline="") as f:
        clubes = {l["nome_boletim"]: l["clube"] for l in csv.DictReader(f)}
    with open(RAIZ / "referencias" / "estadios.csv", encoding="utf-8", newline="") as f:
        estadios = {l["nome_boletim"]: l for l in csv.DictReader(f)}
    return clubes, estadios


def padronizar(registros, clubes, estadios):
    """Aplica os dicionários ao cabeçalho de cada registro. Nome sem
    correspondência fica com o campo padronizado vazio e é listado."""
    sem = {"clube": set(), "estadio": set()}
    for r in registros:
        for papel in ("mandante", "visitante"):
            nome = r[f"{papel}_boletim"]
            r[papel] = clubes.get(nome, "")
            if nome not in clubes:
                sem["clube"].add(nome)
        e = estadios.get(r["estadio_boletim"])
        if e is None:
            sem["estadio"].add(r["estadio_boletim"])
            r["estadio"], r["cidade"] = "", ""
        else:
            r["estadio"], r["cidade"] = e["estadio"], e["cidade"]
    return sem


def gravar_csv(caminho, linhas, colunas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def contar_linhas(caminho):
    with open(caminho, encoding="utf-8") as f:
        return sum(1 for _ in f)


def verificar_completude(esperados, abortados, tmp_base, tmp_razao):
    """Motivos para NÃO substituir os arquivos versionados. Lista vazia: ok."""
    motivos = []
    desconhecidos = [nome for nome, _ in abortados if nome not in LACUNAS_CONHECIDAS]
    if len(abortados) > len(LACUNAS_CONHECIDAS):
        motivos.append(f"{len(abortados)} boletins abortados; o máximo aceito é "
                       f"{len(LACUNAS_CONHECIDAS)} (lacunas conhecidas)")
    if desconhecidos:
        amostra = ", ".join(desconhecidos[:5]) + (" ..." if len(desconhecidos) > 5 else "")
        motivos.append(f"abortados fora das lacunas conhecidas: {amostra}")
    if contar_linhas(tmp_base) <= 1:
        motivos.append(f"{tmp_base.name} só tem o cabeçalho")
    if contar_linhas(tmp_razao) <= 1:
        motivos.append(f"{tmp_razao.name} só tem o cabeçalho")
    return motivos


def pct(parte, todo):
    return f"{100 * parte / todo:.1f}" if todo else "-"


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args_parser.add_argument("--pasta-raw", type=Path, default=PASTA_RAW,
                             help="diretório com os PDFs por ano (padrão: data/01_raw)")
    args = args_parser.parse_args(argv)
    pasta_raw = args.pasta_raw
    categorias = parser.carregar_categorias()

    registros, abortados = [], []
    linhas_por_jogo = []
    lei_zero = 0
    falha_linha, falha_totais, cab_vazio = [], [], {}
    descartadas = {}
    status = Counter()
    derivados = 0
    pcd = Counter()
    quebrados = []
    menores = []
    meia = Counter()
    meias_fora = []
    em_revisao = Counter()
    setores = set()
    ingressos = defaultdict(Decimal)   # (ano, regime)
    receita = defaultdict(Decimal)

    for ano, n in JOGOS_POR_ANO.items():
        for jogo in range(1, n + 1):
            arq = pasta_raw / str(ano) / f"{ano}_{jogo}.pdf"
            try:
                r = parser.processar(arq, categorias)
            except Exception as e:
                abortados.append((arq.name, repr(e)))
                continue
            cab = r["cabecalho"]
            vazios = [c for c in CAMPOS_CABECALHO if not cab.get(c)]
            if vazios:
                cab_vazio[arq.name] = vazios
            if r["descartadas"]:
                descartadas[arq.name] = r["descartadas"]
            probs_linha = [p for p in r["problemas"] if p.startswith("linha")]
            probs_totais = [p for p in r["problemas"] if p.startswith("TOTAIS")]
            if probs_linha:
                falha_linha.append((arq.name, probs_linha))
            if probs_totais:
                falha_totais.append((arq.name, probs_totais))

            linhas_por_jogo.append(r["linhas"])
            for l in r["linhas"]:
                status[l["status"]] += 1
                lei_zero += l["lei_preco_zero"]
                derivados += l["preco_derivado"]
                if l["pcd_decisao"]:
                    pcd[l["pcd_decisao"]] += 1
                if l["preco_quebrado"]:
                    quebrados.append((arq.stem, l))
                if l["categoria"] == "Meia":
                    meia[l["meia_fora_da_metade"]] += 1
                    if l["meia_fora_da_metade"]:
                        meias_fora.append((arq.stem, l))
                if l["categoria"] == "Menor":
                    ref = sorted({x["PREÇO"] for x in r["linhas"] if x["setor"] == l["setor"]
                                  and x["categoria"] == "Inteira"})
                    menores.append((arq.stem, l, ref))
                if l["status"] != "casado":
                    em_revisao[(l["status"], l["rotulo"])] += 1
                else:
                    setores.add(l["setor"])
                regime = l["regime"] or REVISAO
                ingressos[(ano, regime)] += l.get("VENDIDOS", 0)
                receita[(ano, regime)] += l.get("ARRECADAÇÃO", 0)
                fecha = linha_fecha(l)
                registros.append({
                    "ano": ano, "jogo": jogo,
                    "boletim": cab.get("boletim", ""),
                    "mandante_boletim": cab.get("mandante", ""),
                    "visitante_boletim": cab.get("visitante", ""),
                    "data": cab.get("data", ""), "horario": cab.get("horario", ""),
                    "estadio_boletim": cab.get("estadio", ""),
                    "cidade_boletim": cab.get("cidade", ""),
                    "uf": cab.get("uf", ""), "competicao": cab.get("competicao", ""),
                    "rotulo": l["rotulo"], "setor": l["setor"] or "", "subtipo": l["subtipo"] or "",
                    "categoria": l["categoria"] or "",
                    "categoria_boletim": l["categoria_boletim"] or "",
                    "regime": l["regime"] or "", "rotulo_avanti": l["rotulo_avanti"] or "",
                    "status": l["status"],
                    "a_venda": l.get("A VENDA", ""), "devolvidos": l.get("DEVOLVIDOS", ""),
                    "vendidos": l.get("VENDIDOS", ""), "preco": l.get("PREÇO", ""),
                    "preco_derivado": l["preco_derivado"], "preco_quebrado": l["preco_quebrado"],
                    "preco_regulado": l["preco_regulado"],
                    "meia_fora_da_metade": ("" if l["meia_fora_da_metade"] is None
                                            else l["meia_fora_da_metade"]),
                    "arrecadacao": l.get("ARRECADAÇÃO", ""),
                    "linha_fecha": fecha, "totais_conferem": not probs_totais,
                })

    clubes, estadios = carregar_padronizacao()
    sem = padronizar(registros, clubes, estadios)
    for campo in ("mandante", "visitante", "estadio", "cidade"):
        antes = len({r[f"{campo}_boletim"] for r in registros})
        depois = len({r[campo] for r in registros})
        print(f"{campo}: {antes} nomes distintos no boletim, {depois} depois da padronização")
    print(f"Clubes sem correspondência em referencias/clubes.csv: {sorted(sem['clube']) or 'nenhum'}")
    print(f"Estádios sem correspondência em referencias/estadios.csv: {sorted(sem['estadio']) or 'nenhum'}")
    print()

    # Grava em temporário e só substitui o versionado depois da verificação.
    esperados = sum(JOGOS_POR_ANO.values())
    tabela = tabela_razao(linhas_por_jogo)
    tmp_base = SAIDA.with_name(SAIDA.name + ".tmp")
    tmp_razao = SAIDA_RAZAO.with_name(SAIDA_RAZAO.name + ".tmp")
    gravar_csv(tmp_base, registros, COLUNAS_CSV)
    gravar_csv(tmp_razao, tabela, list(tabela[0]) if tabela else ["categoria"])
    motivos = verificar_completude(esperados, abortados, tmp_base, tmp_razao)
    if motivos:
        tmp_base.unlink(missing_ok=True)
        tmp_razao.unlink(missing_ok=True)
        print(f"Arquivos esperados: {esperados}. Processados até o fim: {esperados - len(abortados)}. "
              f"Abortados: {len(abortados)}.")
        print("NADA FOI SUBSTITUÍDO. Os arquivos versionados continuam como estavam:")
        for m in motivos:
            print(f"  - {m}")
        sys.exit(1)
    os.replace(tmp_base, SAIDA)
    os.replace(tmp_razao, SAIDA_RAZAO)

    jogos = {(r["ano"], r["jogo"]) for r in registros}
    print(f"Arquivos esperados: {esperados}")
    print(f"Processados até o fim: {esperados - len(abortados)}")
    print(f"Abortados: {len(abortados)}")
    for nome, erro in abortados:
        lacuna = LACUNAS_CONHECIDAS.get(nome)
        print(f"  {nome}: {'lacuna conhecida, ' + lacuna if lacuna else erro}")
    print(f"Registros gravados em {SAIDA.relative_to(RAIZ)}: {len(registros)}")
    print(f"linha_fecha False: {sum(not r['linha_fecha'] for r in registros)}")
    print(f"Jogos distintos na base: {len(jogos)}")
    print()
    print(f"Arquivos com falha em vendidos x preço = arrecadação: {len(falha_linha)}")
    for nome, probs in falha_linha:
        for p in probs:
            print(f"  {nome}: {p}")
    print(f"Arquivos com falha na conferência com TOTAIS: {len(falha_totais)}")
    for nome, probs in falha_totais:
        for p in probs:
            print(f"  {nome}: {p}")
    print(f"Linhas vazias descartadas: {sum(descartadas.values())} "
          f"em {len(descartadas)} arquivos")
    print(f"Arquivos com campo de cabeçalho vazio: {len(cab_vazio)}")
    for c, n in Counter(c for v in cab_vazio.values() for c in v).most_common():
        print(f"  {c}: {n}")
    print()
    print(f"Linhas com preço derivado: {derivados}")
    print(f"Linhas casadas: {status['casado']}")
    print(f"Subtipo desconhecido: {status['subtipo_desconhecido']}")
    print(f"Gratuidade com preço (revisão): {status['revisao_preco']}")
    print(f"P.C.D. sozinho: {sum(pcd.values())} linhas. Inteira: {pcd['inteira']}, "
          f"Meia: {pcd['meia']}, revisão: {pcd['revisao']}")
    print(f"Linhas sem categoria: {status['sem_categoria']}")
    ti = sum(ingressos.values())
    tr = sum(v for (_, g), v in ingressos.items() if g == REVISAO)
    print(f"Ingressos em revisão: {tr:,.0f} de {ti:,.0f} ({pct(tr, ti)}%)")
    for (st, rotulo), n in sorted(em_revisao.items()):
        print(f"  ({n}) [{st}] {rotulo}")
    print(f"Setores distintos (linhas casadas): {len(setores)}")
    print()
    print(f"Lei ou decreto com preço zero levado para gratuidade: {lei_zero} linhas")
    mercado_livre = [r for r in registros if r["regime"] == "mercado" and not r["preco_regulado"]]
    print(f"Regime mercado com preco_regulado False: {len(mercado_livre)} linhas, "
          f"{sum(r['vendidos'] for r in mercado_livre):,.0f} ingressos")
    print(f"Razão categoria / Inteira, gravada em {SAIDA_RAZAO.relative_to(RAIZ)}:")
    for t in tabela:
        print("  " + " | ".join(str(v) for v in t.values()))
    print()
    print(f"Categoria Meia: {sum(meia.values())} linhas. meia_fora_da_metade True: {meia[True]}, "
          f"False: {meia[False]}, nula: {meia[None]}")
    n_rev = [(j, l) for j, l in meias_fora if l["status"] == "revisao_meia"]
    print(f"  Saíram de mercado para revisão: {len(n_rev)} linhas, "
          f"{sum(l['VENDIDOS'] for _, l in n_rev):,.0f} ingressos")
    for jogo, l in meias_fora:
        print(f"  {jogo} | {l['rotulo']} | vendidos {l['VENDIDOS']} | preço {l['PREÇO']} | "
              f"{l['status']} | regime {l['regime'] or '-'}")
    print()
    print("Categoria Menor, com a Inteira do mesmo setor no mesmo jogo:")
    for jogo, l, ref in menores:
        print(f"  {jogo} | {l['rotulo']} | vendidos {l['VENDIDOS']} | preço {l['PREÇO']} | "
              f"Inteira do setor: {', '.join(str(p) for p in ref) or 'nenhuma'}")
    print()
    n_ing = sum(l.get("VENDIDOS", 0) for _, l in quebrados)
    print(f"preco_quebrado (detector, sem reclassificação): {len(quebrados)} linhas, "
          f"{n_ing:,.0f} ingressos")
    for jogo, l in quebrados[:15]:
        print(f"  {jogo} | {l['setor'] or '?'} | {l['rotulo']} | {l['PREÇO']}")
    print()

    regimes = REGIMES + sorted({g for _, g in ingressos} - set(REGIMES))
    for titulo, anos in [("Total", list(JOGOS_POR_ANO))] + [(str(a), [a]) for a in JOGOS_POR_ANO]:
        ti = sum(v for (a, _), v in ingressos.items() if a in anos)
        tr = sum(v for (a, _), v in receita.items() if a in anos)
        print(f"Regime, {titulo}: {ti:,.0f} ingressos, R$ {tr:,.2f}")
        for g in regimes:
            i = sum(ingressos[(a, g)] for a in anos)
            rr = sum(receita[(a, g)] for a in anos)
            print(f"  {g:<12} {i:>10,.0f} ({pct(i, ti):>5}%)  R$ {rr:>16,.2f} ({pct(rr, tr):>5}%)")
        print()


if __name__ == "__main__":
    main()
