"""Roda o parser nos boletins de data/01_raw e grava data/03_processed/boletins.csv.

Uma linha por linha da tabela de setores de cada boletim. Linhas em
revisão (sem categoria, subtipo desconhecido, Lei ou Decreto com preço)
entram no CSV com setor e categoria vazios e o status correspondente.
Arquivos que o parser não consegue ler até TOTAIS são abortados e listados.

Lacuna conhecida: 2025_57 fica fora da base (ver LACUNAS_CONHECIDAS).

No fim imprime o relatório do lote: arquivos lidos, abortados, falhas de
validação, linhas descartadas, rótulos em revisão, setores distintos,
distribuição por regime e número de jogos distintos.

Uso, a partir da raiz do repositório:
    python scripts/03_lote_boletins.py
"""

import csv
import importlib.util
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "01_raw"
SAIDA = RAIZ / "data" / "03_processed" / "boletins.csv"

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
COLUNAS_CSV = (["ano", "jogo"] + CAMPOS_CABECALHO +
               ["rotulo", "setor", "subtipo", "categoria", "categoria_boletim", "regime",
                "rotulo_avanti", "status", "a_venda", "devolvidos", "vendidos",
                "preco", "preco_derivado", "preco_quebrado", "preco_regulado",
                "meia_fora_da_metade", "arrecadacao", "linha_fecha", "totais_conferem"])
REVISAO = "(revisão)"
REGIMES = ["mercado", "socio", "contrato", "promocional", "gratuidade", "nao_vendido", REVISAO]


def pct(parte, todo):
    return f"{100 * parte / todo:.1f}" if todo else "-"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    categorias = parser.carregar_categorias()

    registros, abortados = [], []
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
            arq = PASTA_RAW / str(ano) / f"{ano}_{jogo}.pdf"
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

            for l in r["linhas"]:
                status[l["status"]] += 1
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
                fecha = ("VENDIDOS" in l and "PREÇO" in l and "ARRECADAÇÃO" in l
                         and not l["preco_derivado"]
                         and l["VENDIDOS"] * l["PREÇO"] == l["ARRECADAÇÃO"])
                registros.append({
                    "ano": ano, "jogo": jogo,
                    **{c: cab.get(c, "") for c in CAMPOS_CABECALHO},
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

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_CSV, lineterminator="\n")
        w.writeheader()
        w.writerows(registros)

    esperados = sum(JOGOS_POR_ANO.values())
    jogos = {(r["ano"], r["jogo"]) for r in registros}
    print(f"Arquivos esperados: {esperados}")
    print(f"Processados até o fim: {esperados - len(abortados)}")
    print(f"Abortados: {len(abortados)}")
    for nome, erro in abortados:
        lacuna = LACUNAS_CONHECIDAS.get(nome)
        print(f"  {nome}: {'lacuna conhecida, ' + lacuna if lacuna else erro}")
    print(f"Registros gravados em {SAIDA.relative_to(RAIZ)}: {len(registros)}")
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
