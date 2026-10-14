"""Coleta dos boletins financeiros do Paulistão A1 (competição 3973 da FPF).

Baixa um PDF por jogo para data/01_raw/{ano}/{ano}_{numero}.pdf, pulando o
que já existe em disco como PDF válido. Falhas são registradas e não
interrompem a coleta. No fim, verifica a integridade de todos os arquivos
esperados e imprime um relatório por ano.

Uso, a partir da raiz do repositório:
    python scripts/01_coleta_boletins.py
    python scripts/01_coleta_boletins.py --anos 2026 --intervalo 2
"""

import argparse
import http.client
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

URL_BASE = "https://conteudo.fpf.org.br/Competicoes"
ID_COMPETICAO = 3973

# Número de jogos por temporada, confirmado sem lacunas.
JOGOS_POR_ANO = {2023: 109, 2024: 104, 2025: 104, 2026: 72}

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "01_raw"
ARQUIVO_LOG = PASTA_RAW / "coleta.log"

TIMEOUT_S = 30
TENTATIVAS = 3
USER_AGENT = ("bilheteria-paulistao/0.1 (pesquisa academica; coleta lenta; "
              "Joao Vitor Agostinetti Barberino; jv.barberino@gmail.com)")


def montar_url(url_base, ano, numero):
    return (f"{url_base}/{ano}/{ID_COMPETICAO}/boletins-financeiros/"
            f"{numero}/boletins/{numero}.pdf")


def caminho_arquivo(ano, numero):
    return PASTA_RAW / str(ano) / f"{ano}_{numero}.pdf"


def pdf_valido(caminho):
    """Checa assinatura %PDF- no início e marcador %%EOF no fim.

    Pega os casos comuns de falha: página HTML salva como .pdf, arquivo
    vazio e download truncado. Não garante que o pdfplumber vá ler o
    conteúdo, isso fica para o extrator.
    """
    if not caminho.exists() or caminho.stat().st_size == 0:
        return False
    with open(caminho, "rb") as f:
        inicio = f.read(1024)
        f.seek(max(0, caminho.stat().st_size - 2048))
        fim = f.read()
    return b"%PDF-" in inicio and b"%%EOF" in fim


def baixar(url, destino):
    """Baixa url para destino via arquivo .part. Devolve None ou a mensagem de erro."""
    requisicao = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    temporario = destino.with_suffix(".part")
    ultimo_erro = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(requisicao, timeout=TIMEOUT_S) as resposta:
                conteudo = resposta.read()
            temporario.write_bytes(conteudo)
            temporario.replace(destino)
            return None
        except urllib.error.HTTPError as erro:
            ultimo_erro = f"HTTP {erro.code}"
            if erro.code == 404:
                break  # não adianta tentar de novo
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as erro:
            # HTTPException cobre IncompleteRead (transferência cortada), que não
            # herda de OSError; vira falha do boletim, sem interromper a coleta.
            ultimo_erro = f"{type(erro).__name__}: {erro}"
        if tentativa < TENTATIVAS:
            time.sleep(2 ** tentativa)
    temporario.unlink(missing_ok=True)
    return ultimo_erro


def registrar(linha):
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{linha}\n")


def coletar(anos, intervalo, url_base):
    resumo = {}
    for ano in anos:
        (PASTA_RAW / str(ano)).mkdir(parents=True, exist_ok=True)
        r = {"esperados": JOGOS_POR_ANO[ano], "baixados": 0, "existentes": 0,
             "falhas": []}
        for numero in range(1, JOGOS_POR_ANO[ano] + 1):
            destino = caminho_arquivo(ano, numero)
            if pdf_valido(destino):
                r["existentes"] += 1
                continue
            # Arquivo ausente ou inválido em disco: baixa (de novo).
            url = montar_url(url_base, ano, numero)
            erro = baixar(url, destino)
            if erro is None:
                r["baixados"] += 1
                status = "OK" if pdf_valido(destino) else "NAO_PDF"
                registrar(f"{status}\t{ano}\t{numero}\t{url}")
            else:
                r["falhas"].append((numero, erro))
                registrar(f"FALHA\t{ano}\t{numero}\t{url}\t{erro}")
            time.sleep(intervalo)
        resumo[ano] = r
        print(f"{ano}: {r['baixados']} baixados, {r['existentes']} já existiam, "
              f"{len(r['falhas'])} falhas")
    return resumo


def verificar(anos):
    """Varre todos os arquivos esperados em disco, inclusive os que já existiam."""
    resultado = {}
    for ano in anos:
        ausentes, invalidos = [], []
        for numero in range(1, JOGOS_POR_ANO[ano] + 1):
            caminho = caminho_arquivo(ano, numero)
            if not caminho.exists():
                ausentes.append(numero)
            elif not pdf_valido(caminho):
                invalidos.append(numero)
        resultado[ano] = {"ausentes": ausentes, "invalidos": invalidos}
    return resultado


def imprimir_relatorio(resumo, verificacao):
    print("\n" + "=" * 72)
    print("RELATÓRIO DA COLETA")
    print("=" * 72)
    print(f"{'Ano':<6}{'Esperados':>10}{'Baixados':>10}{'Existiam':>10}"
          f"{'Falhas':>8}{'Ausentes':>10}{'Não PDF':>9}")
    totais = [0] * 6
    for ano, r in resumo.items():
        v = verificacao[ano]
        linha = [r["esperados"], r["baixados"], r["existentes"],
                 len(r["falhas"]), len(v["ausentes"]), len(v["invalidos"])]
        totais = [t + x for t, x in zip(totais, linha)]
        print(f"{ano:<6}{linha[0]:>10}{linha[1]:>10}{linha[2]:>10}"
              f"{linha[3]:>8}{linha[4]:>10}{linha[5]:>9}")
    print(f"{'Total':<6}{totais[0]:>10}{totais[1]:>10}{totais[2]:>10}"
          f"{totais[3]:>8}{totais[4]:>10}{totais[5]:>9}")

    houve_problema = False
    for ano, r in resumo.items():
        if r["falhas"]:
            houve_problema = True
            print(f"\nFalhas em {ano}:")
            for numero, erro in r["falhas"]:
                print(f"  jogo {numero}: {erro}")
        if verificacao[ano]["invalidos"]:
            houve_problema = True
            print(f"\nArquivos em disco que não são PDF válido em {ano}: "
                  f"{verificacao[ano]['invalidos']}")
    if houve_problema:
        print(f"\nDetalhe em {ARQUIVO_LOG.relative_to(RAIZ)}. Rodar de novo "
              "tenta só os ausentes e inválidos.")
    else:
        print("\nTodos os arquivos esperados estão em disco e são PDF válido.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--anos", type=int, nargs="+", default=list(JOGOS_POR_ANO),
                        choices=list(JOGOS_POR_ANO))
    parser.add_argument("--intervalo", type=float, default=1.0,
                        help="segundos entre requisições (padrão: 1)")
    parser.add_argument("--url-base", default=URL_BASE, help=argparse.SUPPRESS)
    args = parser.parse_args()

    PASTA_RAW.mkdir(parents=True, exist_ok=True)
    resumo = coletar(args.anos, args.intervalo, args.url_base)
    imprimir_relatorio(resumo, verificar(args.anos))


if __name__ == "__main__":
    main()
