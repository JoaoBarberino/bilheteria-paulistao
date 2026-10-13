"""Testes de regressão do parser de boletim.

Uso, a partir da raiz do repositório:
    python -m unittest discover tests
"""

import importlib.util
import unittest
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# O nome do módulo começa com número, então não dá para usar import comum.
_spec = importlib.util.spec_from_file_location(
    "parser_boletim", RAIZ / "scripts" / "02_parser_boletim.py")
parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parser)

# Gabarito lido à mão do boletim 72/2026, Grêmio Novorizontino x Palmeiras,
# 08/03/2026: (setor, categoria, vendidos, preço, arrecadação).
GABARITO_2026_72 = [
    ("ARQUIBANCADA COBERTA", "Inteira", "33", "280.00", "9240.00"),
    ("ARQUIBANCADA COBERTA", "Sócio", "47", "20.00", "940.00"),
    ("ARQUIBANCADA COBERTA", "Gratuidade legal", "28", "0.00", "0.00"),
    ("ARQUIBANCADA GERAL - GERAIS LOCAL", "Inteira", "1682", "130.00", "218660.00"),
    ("ARQUIBANCADA GERAL - GERAIS LOCAL", "Meia", "611", "65.00", "39715.00"),
    ("ARQUIBANCADA GERAL - GERAIS LOCAL", "Sócio", "486", "20.00", "9720.00"),
    ("ARQUIBANCADA GERAL - GERAIS LOCAL", "Gratuidade legal", "985", "0.00", "0.00"),
    ("ARQUIBANCADA GERAL - GERAL CENTRAL", "Visitante - Inteira", "1725", "250.00", "431250.00"),
    ("ARQUIBANCADA GERAL - GERAL CENTRAL", "Visitante - Meia", "615", "125.00", "76875.00"),
    ("ARQUIBANCADA INFERIOR", "Inteira", "112", "250.00", "28000.00"),
    ("ARQUIBANCADA INFERIOR", "Meia", "252", "125.00", "31500.00"),
    ("ARQUIBANCADA INFERIOR", "Sócio", "266", "20.00", "5320.00"),
    ("ARQUIBANCADA INFERIOR", "Gratuidade legal", "300", "0.00", "0.00"),
    ("CAMAROTES", "Carnê de Relacionamento", "27", "20.00", "540.00"),
    ("CATIVAS SÓCIOS", "Sócio", "251", "20.00", "5020.00"),
    ("CATIVAS SÓCIOS", "Gratuidade legal", "124", "0.00", "0.00"),
    ("SETOR B*", "Visitante - Inteira", "1791", "250.00", "447750.00"),
    ("SETOR B*", "Visitante - Meia", "316", "125.00", "39500.00"),
    ("SETOR B*", "Gratuidade legal", "251", "0.00", "0.00"),
]


class TestGabarito2026_72(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = parser.processar(FIXTURES / "2026_72.pdf", parser.carregar_categorias())

    def test_cabecalho(self):
        cab = self.r["cabecalho"]
        self.assertEqual(cab["mandante"], "Grêmio Novorizontino")
        self.assertEqual(cab["visitante"], "Palmeiras")
        self.assertEqual(cab["data"], "08/03/2026")
        self.assertEqual(cab["horario"], "20:30")
        self.assertEqual(cab["estadio"], "Dr. Jorge Ismael de Biasi")
        self.assertEqual(cab["cidade"], "Novo Horizonte")
        self.assertEqual(cab["competicao"], "Paulista - A1- Profissional")

    def test_linhas(self):
        obtido = [(l["setor"], l["categoria"], l["VENDIDOS"], l["PREÇO"], l["ARRECADAÇÃO"])
                  for l in self.r["linhas"]]
        esperado = [(s, c, Decimal(v), Decimal(p), Decimal(a))
                    for s, c, v, p, a in GABARITO_2026_72]
        self.assertEqual(obtido, esperado)

    def test_totais(self):
        self.assertEqual(self.r["totais"]["VENDIDOS"], Decimal("9902"))
        self.assertEqual(self.r["totais"]["ARRECADAÇÃO"], Decimal("1344030.00"))

    def test_sem_problemas(self):
        self.assertEqual(self.r["problemas"], [])


class TestFixtures(unittest.TestCase):
    """Os outros boletins cobrem: tabela em 3 páginas e P.C.D./Especial
    (2023_55), linhas vazias do formulário e VENDA PROIBIDA (2024_52), PCR,
    Cativa e Avanti (2025_78)."""

    def test_todos_validam_e_casam(self):
        categorias = parser.carregar_categorias()
        for pdf in sorted(FIXTURES.glob("*.pdf")):
            with self.subTest(pdf=pdf.name):
                r = parser.processar(pdf, categorias)
                self.assertEqual(r["problemas"], [])
                nao_casados = [l["rotulo"] for l in r["linhas"] if l["status"] != "casado"]
                self.assertEqual(nao_casados, [])

    def test_linhas_vazias_descartadas(self):
        r = parser.processar(FIXTURES / "2024_52.pdf", parser.carregar_categorias())
        self.assertEqual(r["descartadas"], 9)

    def test_pcd_nao_vira_inteira(self):
        r = parser.processar(FIXTURES / "2023_55.pdf", parser.carregar_categorias())
        pcd = [l for l in r["linhas"] if "P.C.D." in l["rotulo"]]
        self.assertTrue(pcd)
        for l in pcd:
            self.assertEqual(l["categoria"], "P.C.D.")
            self.assertEqual(l["regime"], "mercado")


class TestClassificacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.refs = parser.carregar_categorias()

    def test_subtipo(self):
        r = parser.separar_setor_categoria("CABECEIRA PRINCIPAL - SUL - Geral - Inteira", self.refs)
        self.assertEqual((r["setor"], r["subtipo"], r["categoria"], r["regime"]),
                         ("CABECEIRA PRINCIPAL - SUL", "Geral", "Inteira", "mercado"))

    def test_subtipo_contratual_define_regime(self):
        r = parser.separar_setor_categoria("JOHNNIE WALKER - Carnê - Inteira", self.refs)
        self.assertEqual((r["subtipo"], r["categoria"], r["regime"]), ("Carnê", "Inteira", "contrato"))

    def test_lei_com_preco_vai_para_revisao(self):
        r = parser.separar_setor_categoria("ARQUIBANCADA - Lei n. 4046/14 - Novorizonte",
                                           self.refs, Decimal("30.00"))
        self.assertEqual(r["status"], "revisao_preco")

    def test_meia_legal_literal(self):
        r = parser.separar_setor_categoria(
            "ARQUIBANCADA - Lei nº18.159- Meia entrada, menores de 12 anos", self.refs, Decimal("30.00"))
        self.assertEqual((r["categoria"], r["regime"], r["status"]), ("Meia legal", "mercado", "casado"))

    def test_juntar_continuacao(self):
        brutos = [{"rotulo": "SETOR X - Carnê de"},
                  {"rotulo": "", "VENDIDOS": Decimal("218"), "PREÇO": Decimal("20.00")},
                  {"rotulo": "Relacionamento"}]
        self.assertEqual(parser.juntar_continuacoes(brutos),
                         [{"rotulo": "SETOR X - Carnê de Relacionamento",
                           "VENDIDOS": Decimal("218"), "PREÇO": Decimal("20.00")}])

    def test_preco_derivado_fiel_torcedor(self):
        r = {"categoria_boletim": "Fiel Torcedor", "VENDIDOS": Decimal("8109"),
             "PREÇO": Decimal("0.00"), "ARRECADAÇÃO": Decimal("281873.00")}
        parser.derivar_preco(r)
        self.assertTrue(r["preco_derivado"])
        self.assertEqual(r["PREÇO"], Decimal("34.76"))


if __name__ == "__main__":
    unittest.main()
