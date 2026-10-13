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

_spec_lote = importlib.util.spec_from_file_location(
    "lote_boletins", RAIZ / "scripts" / "03_lote_boletins.py")
lote = importlib.util.module_from_spec(_spec_lote)
_spec_lote.loader.exec_module(lote)

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
    ("ARQUIBANCADA GERAL - GERAL CENTRAL", "Inteira", "1725", "250.00", "431250.00"),
    ("ARQUIBANCADA GERAL - GERAL CENTRAL", "Meia", "615", "125.00", "76875.00"),
    ("ARQUIBANCADA INFERIOR", "Inteira", "112", "250.00", "28000.00"),
    ("ARQUIBANCADA INFERIOR", "Meia", "252", "125.00", "31500.00"),
    ("ARQUIBANCADA INFERIOR", "Sócio", "266", "20.00", "5320.00"),
    ("ARQUIBANCADA INFERIOR", "Gratuidade legal", "300", "0.00", "0.00"),
    ("CAMAROTES", "Carnê de Relacionamento", "27", "20.00", "540.00"),
    ("CATIVAS SÓCIOS", "Sócio", "251", "20.00", "5020.00"),
    ("CATIVAS SÓCIOS", "Gratuidade legal", "124", "0.00", "0.00"),
    ("SETOR B*", "Inteira", "1791", "250.00", "447750.00"),
    ("SETOR B*", "Meia", "316", "125.00", "39500.00"),
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


# Única linha dos fixtures que sai de casado: Meia a R$ 50,43 com Inteira do
# setor a R$ 60,00 (meia fora da metade).
NAO_CASADOS_ESPERADOS = {"2023_55.pdf": ["CAMAROTES 4º ANDAR - Especial - Meia"]}


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
                self.assertEqual(nao_casados, NAO_CASADOS_ESPERADOS.get(pdf.name, []))

    def test_linhas_vazias_descartadas(self):
        r = parser.processar(FIXTURES / "2024_52.pdf", parser.carregar_categorias())
        self.assertEqual(r["descartadas"], 9)

    def test_pcd_e_especial_sao_subtipo_no_fixture(self):
        r = parser.processar(FIXTURES / "2023_55.pdf", parser.carregar_categorias())
        pcd = [l for l in r["linhas"] if "P.C.D." in l["rotulo"]]
        self.assertTrue(pcd)
        for l in pcd:
            self.assertEqual((l["subtipo"], l["categoria"], l["regime"]),
                             ("P.C.D.", "Inteira", "mercado"))
        esp = [l for l in r["linhas"] if l["rotulo"] == "CAMAROTES 4º ANDAR - Especial - Meia"]
        self.assertEqual(len(esp), 1)
        self.assertEqual((esp[0]["setor"], esp[0]["subtipo"], esp[0]["categoria"]),
                         ("CAMAROTES 4º ANDAR", "Especial", "Meia"))


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


class TestDecisoesRegime(unittest.TestCase):
    """Itens 1 a 7 das decisões de regime."""

    @classmethod
    def setUpClass(cls):
        cls.refs = parser.carregar_categorias()

    def sep(self, rotulo, preco=None):
        return parser.separar_setor_categoria(rotulo, self.refs, preco)

    def test_1_tc10_socio_sem_colapsar(self):
        for rotulo, original in [
                ("ARQUIBANCADA - TC10 ARQUIBANCADA", "TC10 ARQUIBANCADA"),
                ("CADEIRA VITALÍCIA - TC10 VITALÍCIA - ADICIONAL", "TC10 VITALÍCIA - ADICIONAL")]:
            r = self.sep(rotulo)
            self.assertEqual((r["categoria"], r["regime"], r["categoria_boletim"]),
                             ("TC10", "socio", original))

    def test_2_palmeiras_pay_promocional(self):
        r = self.sep("C - AMARELO SUPERIOR - - - Palmeiras Pay")
        self.assertEqual((r["setor"], r["categoria"], r["regime"]),
                         ("C - AMARELO SUPERIOR", "Palmeiras Pay", "promocional"))

    def test_3_unico_contrato(self):
        r = self.sep("CAMAROTE TÉRREO OESTE - CORPORATIVO - Único")
        self.assertEqual((r["setor"], r["categoria"], r["regime"]),
                         ("CAMAROTE TÉRREO OESTE - CORPORATIVO", "Único", "contrato"))

    def test_4_camarote_contrato(self):
        r = self.sep("CAMAROTES SETOR 4 - Camarote")
        self.assertEqual((r["setor"], r["categoria"], r["regime"]),
                         ("CAMAROTES SETOR 4", "Camarote", "contrato"))

    def test_5_pcd_com_categoria_e_subtipo(self):
        for rotulo, cat in [("GOL SUL - P.C.D. - Inteira", "Inteira"),
                            ("GOL SUL - P.C.D. - Meia", "Meia"),
                            ("GOL SUL - P.C.D. - Acompanhante", "Acompanhante")]:
            r = self.sep(rotulo)
            self.assertEqual((r["setor"], r["subtipo"], r["categoria"], r["regime"]),
                             ("GOL SUL", "P.C.D.", cat, "mercado"))

    def _linhas_pcd(self, preco_pcd):
        linhas = []
        for rotulo, preco in [("SETOR A - Inteira", "100.00"), ("SETOR A - Meia", "50.00"),
                              ("SETOR A - P.C.D.", preco_pcd)]:
            r = {"rotulo": rotulo, "PREÇO": Decimal(preco)}
            r.update(self.sep(rotulo, r["PREÇO"]))
            linhas.append(r)
        parser.resolver_pcd(linhas)
        return linhas[-1]

    def test_5_pcd_sozinho_pela_aritmetica(self):
        r = self._linhas_pcd("100.00")
        self.assertEqual((r["subtipo"], r["categoria"], r["pcd_decisao"]), ("P.C.D.", "Inteira", "inteira"))
        r = self._linhas_pcd("50.00")
        self.assertEqual((r["subtipo"], r["categoria"], r["pcd_decisao"]), ("P.C.D.", "Meia", "meia"))
        r = self._linhas_pcd("30.00")
        self.assertEqual((r["status"], r["categoria"], r["pcd_decisao"]), ("revisao_pcd", None, "revisao"))

    def test_5_pcd_sozinho_sem_inteira_vai_para_revisao(self):
        r = {"rotulo": "SETOR B - P.C.D.", "PREÇO": Decimal("50.00")}
        r.update(self.sep(r["rotulo"], r["PREÇO"]))
        parser.resolver_pcd([r])
        self.assertEqual(r["status"], "revisao_pcd")

    def test_6_especial_sempre_subtipo(self):
        for rotulo, cat in [("CAMAROTES 4º ANDAR - Especial - Meia", "Meia"),
                            ("TOBOGÃ - Especial - Inteira", "Inteira")]:
            r = self.sep(rotulo)
            self.assertEqual((r["subtipo"], r["categoria"], r["regime"]), ("Especial", cat, "mercado"))
        self.assertNotIn("Especial", self.refs["literais"])

    def test_7_menor_mercado(self):
        r = self.sep("ARQUIBANCADA - Promoção - Menor")
        self.assertEqual((r["setor"], r["subtipo"], r["categoria"], r["regime"]),
                         ("ARQUIBANCADA", "Promoção", "Menor", "mercado"))


def _linha(rotulo, preco, refs):
    r = {"rotulo": rotulo, "PREÇO": Decimal(preco)}
    r.update(parser.separar_setor_categoria(rotulo, refs, r["PREÇO"]))
    return r


class TestMeiaRegulada(unittest.TestCase):
    """Itens 1 a 4 da rodada de meia-entrada."""

    @classmethod
    def setUpClass(cls):
        cls.refs = parser.carregar_categorias()

    def jogo(self, *linhas):
        tab = [_linha(rot, preco, self.refs) for rot, preco in linhas]
        parser.resolver_pcd(tab)
        parser.marcar_meia(tab)
        return tab

    def test_1_meia_na_metade_e_false(self):
        tab = self.jogo(("SETOR A - Inteira", "60.00"), ("SETOR A - Meia", "30.00"))
        self.assertIs(tab[1]["meia_fora_da_metade"], False)
        self.assertIsNone(tab[0]["meia_fora_da_metade"])

    def test_1_meia_fora_da_metade_e_true(self):
        tab = self.jogo(("SETOR A - Inteira", "30.00"), ("SETOR A - Meia", "20.00"))
        self.assertIs(tab[1]["meia_fora_da_metade"], True)

    def test_1_tolerancia_de_um_centavo(self):
        tab = self.jogo(("SETOR A - Inteira", "50.01"), ("SETOR A - Meia", "25.00"))
        self.assertIs(tab[1]["meia_fora_da_metade"], False)

    def test_1_sem_inteira_no_setor_e_nula(self):
        tab = self.jogo(("SETOR A - Inteira", "60.00"), ("SETOR B - Meia", "30.00"))
        self.assertIsNone(tab[1]["meia_fora_da_metade"])

    def test_1_compara_com_inteira_do_mesmo_subtipo(self):
        # Meia sem subtipo a R$ 25 é metade da Inteira sem subtipo (R$ 50),
        # não da Inteira do camarote especial (R$ 300).
        tab = self.jogo(("SETOR A - Inteira", "50.00"),
                        ("SETOR A - Camarote dos Ídolos - Inteira", "300.00"),
                        ("SETOR A - Meia", "25.00"))
        self.assertIs(tab[2]["meia_fora_da_metade"], False)

    def test_1_meia_local_nao_compara_com_inteira_de_visitante(self):
        tab = self.jogo(("SUL - Visitante - Inteira", "100.00"), ("SUL - Meia", "60.00"))
        self.assertIsNone(tab[1]["meia_fora_da_metade"])
        self.assertEqual(tab[1]["regime"], "mercado")

    def test_2_meia_fora_sai_de_mercado(self):
        tab = self.jogo(("CAMAROTES 4º ANDAR - Inteira", "60.00"),
                        ("CAMAROTES 4º ANDAR - Especial - Meia", "50.43"))
        r = tab[1]
        self.assertEqual((r["status"], r["regime"]), ("revisao_meia", None))
        self.assertEqual((r["setor"], r["subtipo"], r["categoria"]),
                         ("CAMAROTES 4º ANDAR", "Especial", "Meia"))

    def test_2_e_3_pcd_fora_da_metade_fica_em_mercado(self):
        tab = self.jogo(("GOL SUL - Inteira", "90.00"), ("GOL SUL - P.C.D. - Meia", "30.00"))
        r = tab[1]
        self.assertIs(r["meia_fora_da_metade"], True)
        self.assertEqual((r["status"], r["regime"], r["preco_regulado"]), ("casado", "mercado", True))

    def test_3_preco_regulado(self):
        tab = self.jogo(("SETOR A - Inteira", "60.00"), ("SETOR A - Meia", "30.00"),
                        ("SETOR A - P.C.D. - Inteira", "60.00"), ("SETOR A - Sócio", "20.00"))
        self.assertEqual([r["preco_regulado"] for r in tab], [False, True, True, False])

    def test_4_nenhum_literal_com_meia_ou_inteira_como_sufixo(self):
        for literal in self.refs["literais"]:
            if literal in ("Meia", "Inteira"):
                continue
            ultimo = parser.segmentos(literal)[-1]
            with self.subTest(literal=literal):
                self.assertNotIn(ultimo, ("Meia", "Inteira"))
        self.assertNotIn("Especial - Meia", self.refs["literais"])


class TestBaseFechada(unittest.TestCase):
    """Itens 1, 2 e 4 da última rodada antes da descritiva."""

    @classmethod
    def setUpClass(cls):
        cls.refs = parser.carregar_categorias()

    def sep(self, rotulo, preco):
        r = {"rotulo": rotulo, "PREÇO": Decimal(preco)}
        r.update(parser.separar_setor_categoria(rotulo, self.refs, r["PREÇO"]))
        parser.marcar_meia([r])
        return r

    def test_1_lei_com_preco_zero_vira_gratuidade(self):
        r = self.sep("ARQUIBANCADA MANDANTE - SEÇÃO 2 - Lei nº18.159- Meia entrada, menores de 12 anos",
                     "0.00")
        self.assertEqual((r["categoria"], r["regime"], r["lei_preco_zero"], r["preco_regulado"]),
                         ("Meia legal", "gratuidade", True, False))

    def test_1_lei_com_preco_fica_mercado_regulado(self):
        r = self.sep("ARQUIBANCADA - Lei nº18.159- Meia entrada, menores de 12 anos", "30.00")
        self.assertEqual((r["regime"], r["lei_preco_zero"], r["preco_regulado"]),
                         ("mercado", False, True))

    def test_1_gratuidade_legal_com_preco_zero_nao_muda(self):
        r = self.sep("ARQUIBANCADA - Lei n. 4046/14 - Novorizonte", "0.00")
        self.assertEqual((r["categoria"], r["regime"], r["lei_preco_zero"]),
                         ("Gratuidade legal", "gratuidade", False))

    def test_2_preco_regulado_por_categoria(self):
        esperado = {"Meia": True, "Meia Promocional": True, "PCR": True, "Menor": True,
                    "Acompanhante": True, "Solidário": True, "Meia Social": True,
                    "Meia Solidária": True, "Inteira": False}
        for categoria, regulado in esperado.items():
            with self.subTest(categoria=categoria):
                r = self.sep(f"SETOR A - {categoria}", "10.00")
                self.assertEqual(r["categoria"], categoria)
                self.assertIs(r["preco_regulado"], regulado)

    def test_2_so_inteira_fica_livre_em_mercado(self):
        livres = {l["categoria_boletim"] for l in self.refs["literais"].values()
                  if l["regime"] == "mercado" and l["preco_regulado"] == "nao"}
        self.assertEqual(livres, {"Inteira"})

    def test_4_linha_fecha_exata_sem_preco_derivado(self):
        l = {"VENDIDOS": Decimal("10"), "PREÇO": Decimal("20.00"),
             "ARRECADAÇÃO": Decimal("200.01"), "preco_derivado": False}
        self.assertFalse(lote.linha_fecha(l))
        l["ARRECADAÇÃO"] = Decimal("200.00")
        self.assertTrue(lote.linha_fecha(l))

    def test_4_linha_fecha_com_tolerancia_no_preco_derivado(self):
        l = {"categoria_boletim": "Fiel Torcedor", "VENDIDOS": Decimal("8109"),
             "PREÇO": Decimal("0.00"), "ARRECADAÇÃO": Decimal("281873.00")}
        parser.derivar_preco(l)
        self.assertTrue(lote.linha_fecha(l))
        l["ARRECADAÇÃO"] = Decimal("300000.00")
        self.assertFalse(lote.linha_fecha(l))


class TestPadronizacaoNoCSV(unittest.TestCase):
    """O CSV processado só pode ter clube e estádio que estão nos dicionários."""

    @classmethod
    def setUpClass(cls):
        import csv
        with open(RAIZ / "data" / "03_processed" / "boletins.csv", encoding="utf-8", newline="") as f:
            cls.linhas = list(csv.DictReader(f))
        cls.clubes, cls.estadios = lote.carregar_padronizacao()

    def test_clubes_no_dicionario(self):
        padronizados = set(self.clubes.values())
        for papel in ("mandante", "visitante"):
            with self.subTest(papel=papel):
                self.assertEqual({l[f"{papel}_boletim"] for l in self.linhas} - set(self.clubes), set())
                self.assertEqual({l[papel] for l in self.linhas} - padronizados, set())

    def test_estadios_no_dicionario(self):
        self.assertEqual({l["estadio_boletim"] for l in self.linhas} - set(self.estadios), set())
        padronizados = {e["estadio"] for e in self.estadios.values()}
        self.assertEqual({l["estadio"] for l in self.linhas} - padronizados, set())

    def test_padronizar_lista_nome_desconhecido(self):
        r = [{"mandante_boletim": "Clube X", "visitante_boletim": "Santos",
              "estadio_boletim": "Estádio Y"}]
        sem = lote.padronizar(r, self.clubes, self.estadios)
        self.assertEqual(sem, {"clube": {"Clube X"}, "estadio": {"Estádio Y"}})
        self.assertEqual((r[0]["mandante"], r[0]["visitante"], r[0]["estadio"]), ("", "Santos", ""))


if __name__ == "__main__":
    unittest.main()
