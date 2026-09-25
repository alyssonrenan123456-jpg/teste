import io
import traceback
import urllib.request
import urllib.error
import time

from flask import Flask, jsonify, render_template, request
import pandas as pd
from rapidfuzz import fuzz, process


app = Flask(__name__)

# ============================================================
# GOOGLE SHEETS
# ============================================================

URL_AGENDAMENTOS = (
    "https://docs.google.com/spreadsheets/d/"
    "1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/"
    "export?format=csv&gid=0"
)

URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWh1vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"
)

# Cache simples para evitar várias chamadas seguidas ao Google Sheets.
CACHE = {
    "agendamento": {"tempo": 0, "dados": None},
    "plantao": {"tempo": 0, "dados": None},
}

CACHE_SEGUNDOS = 30


# ============================================================
# MAPAS
# ============================================================

MAPEAMENTO_SIGLAS_AGENDAMENTO = {
    "bnu": "Brunópolis",
    "cnv": "Campos Novos",
    "ctb": "Curitibanos",
    "fbg": "Fraiburgo",
    "frr": "Frei Rogério",
    "iom": "Iomerê",
    "mca": "Monte Carlo",
    "ppr": "Pinheiro Preto",
    "vda": "Videira",
    "agr": "Agronômica",
    "aur": "Aurora",
    "itu": "Ituporanga",
    "lon": "Lontras",
    "ptl": "Petrolândia",
    "prd": "Pouso Redondo",
    "rsl": "Rio do Sul",
    "cbs": "Campo Belo do Sul",
    "cat": "Capão Alto",
    "cpo": "Correia Pinto",
    "lgs": "Lages",
    "pta": "Ponte Alta",
    "api": "Apiúna",
    "asc": "Ascurra",
    "blu": "Blumenau",
    "idl": "Indaial",
    "rod": "Rodeio",
    "ace": "Água Doce",
    "ctv": "Catanduvas",
    "hdo": "Herval d'Oeste",
    "ibc": "Ibicaré",
    "ipi": "Ipira",
    "jba": "Joaçaba",
    "lzn": "Luzerna",
    "ptb": "Piratuba",
    "svs": "Salto Veloso",
    "tan": "Tangará",
    "tzs": "Treze Tílias",
    "ant": "Anita Garibaldi",
    "cdr": "Caçador",
    "mra": "Macieira",
    "pan": "Ponte Alta do Norte",
    "sct": "São Cristóvão do Sul",
    "arq": "Araquari",
    "bbs": "Balneário Barra do Sul",
    "brq": "Brusque",
    "cmb": "Camboriú",
    "cal": "Campo Alegre",
    "grm": "Guaramirim",
    "jas": "Jaraguá do Sul",
    "jve": "Joinville",
    "las": "Luiz Alves",
    "mas": "Massaranduba",
    "sfs": "São Francisco do Sul",
    "sch": "Schroeder",
    "evv": "Erval Velho",
    "ldp": "Lacerdópolis",
    "rdc": "Rio dos Cedros",
    "bpi": "Balneário Piçarras",
    "bve": "Barra Velha",
    "nav": "Navegantes",
    "pen": "Penha",
    "sji": "São João do Itaperiú",
    "gva": "Garuva",
    "itp": "Itapoá",
}

MAPA_FILIAIS_ORIGINAL = {
    "Brunópolis": "01 - MCA",
    "Campos Novos": "01 - MCA",
    "Curitibanos": "01 - MCA",
    "Fraiburgo": "01 - MCA",
    "Frei Rogério": "01 - MCA",
    "Iomerê": "01 - MCA",
    "Monte Carlo": "01 - MCA",
    "Pinheiro Preto": "01 - MCA",
    "Videira": "01 - MCA",

    "Agronômica": "02 - RSL",
    "Aurora": "02 - RSL",
    "Ituporanga": "02 - RSL",
    "Lontras": "02 - RSL",
    "Petrolândia": "02 - RSL",
    "Pouso Redondo": "02 - RSL",
    "Rio do Sul": "02 - RSL",

    "Campo Belo do Sul": "03 - LGS",
    "Capão Alto": "03 - LGS",
    "Correia Pinto": "03 - LGS",
    "Lages": "03 - LGS",
    "Ponte Alta": "03 - LGS",

    "Apiúna": "04 - BLU",
    "Ascurra": "04 - BLU",
    "Blumenau": "04 - BLU",
    "Indaial": "04 - BLU",
    "Rodeio": "04 - BLU",

    "Água Doce": "06 - JBA",
    "Catanduvas": "06 - JBA",
    "Herval d'Oeste": "06 - JBA",
    "Ibicaré": "06 - JBA",
    "Ipira": "06 - JBA",
    "Joaçaba": "06 - JBA",
    "Luzerna": "06 - JBA",
    "Piratuba": "06 - JBA",
    "Salto Veloso": "06 - JBA",
    "Tangará": "06 - JBA",
    "Treze Tílias": "06 - JBA",

    "Anita Garibaldi": "07 - ANT",

    "Caçador": "08 - CDR",
    "Macieira": "08 - CDR",

    "Ponte Alta do Norte": "09 - SCT",
    "São Cristóvão do Sul": "09 - SCT",

    "Araquari": "10 - JVE",
    "Balneário Barra do Sul": "10 - JVE",
    "Brusque": "10 - JVE",
    "Camboriú": "10 - JVE",
    "Campo Alegre": "10 - JVE",
    "Guaramirim": "10 - JVE",
    "Jaraguá do Sul": "10 - JVE",
    "Joinville": "10 - JVE",
    "Luiz Alves": "10 - JVE",
    "Massaranduba": "10 - JVE",
    "São Francisco do Sul": "10 - JVE",
    "Schroeder": "10 - JVE",

    "Erval Velho": "1002 - EVV",
    "Lacerdópolis": "1002 - EVV",

    "Rio dos Cedros": "1063 - RDC",

    "Balneário Piçarras": "11 - BVE",
    "Barra Velha": "11 - BVE",
    "Navegantes": "11 - BVE",
    "Penha": "11 - BVE",
    "São João do Itaperiú": "11 - BVE",

    "Garuva": "12 - ITP",
    "Itapoá": "12 - ITP",
}

MAPA_FILIAIS = {
    normalizar: filial
    for normalizar, filial in (
        (
            " ".join(
                str(cidade).strip().lower().translate(
                    str.maketrans(
                        "áàãâäéèêëíìîïóòõôöúùûüç",
                        "aaaaaeeeeiiiiooooouuuuc",
                    )
                ).split()
            ),
            filial,
        )
        for cidade, filial in MAPA_FILIAIS_ORIGINAL.items()
    )
}


# ============================================================
# FUNÇÕES DE TEXTO
# ============================================================

def normalizar_texto(texto):
    if texto is None:
        return ""

    texto = str(texto).strip().lower()

    tabela = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüç",
        "aaaaaeeeeiiiiooooouuuuc",
    )

    return " ".join(texto.translate(tabela).split())


def obter_filial_por_cidade(cidade):
    if not cidade:
        return "Não mapeada"

    return MAPA_FILIAIS.get(
        normalizar_texto(cidade),
        "Não mapeada",
    )


# ============================================================
# LEITURA ROBUSTA DO GOOGLE SHEETS
# ============================================================

def ler_csv_online(url, tipo):
    agora = time.time()

    # Usa cache por alguns segundos.
    cache = CACHE.get(tipo)

    if cache and cache["dados"] is not None:
        if agora - cache["tempo"] < CACHE_SEGUNDOS:
            return cache["dados"]

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/130 Safari/537.36"
                )
            },
        )

        with urllib.request.urlopen(req, timeout=20) as resposta:
            status = resposta.status
            conteudo = resposta.read()

        if status != 200:
            raise Exception(
                f"Google Sheets respondeu HTTP {status}"
            )

        if not conteudo:
            raise Exception("Google Sheets retornou conteúdo vazio.")

        # Google pode devolver uma página HTML quando a planilha
        # não está pública. Detectamos isso para não gerar erro
        # misterioso no pandas.
        inicio = conteudo[:300].lower()

        if b"<html" in inicio or b"<!doctype" in inicio:
            raise Exception(
                "O Google Sheets não retornou CSV. "
                "Verifique se a planilha está publicada/compartilhada "
                "para acesso pela URL de exportação."
            )

        # utf-8-sig remove BOM quando existir.
        texto = conteudo.decode("utf-8-sig")

        df = pd.read_csv(
            io.StringIO(texto),
            dtype=str,
            keep_default_na=False,
        )

        # Remove colunas completamente vazias.
        df = df.dropna(axis=1, how="all")

        linhas = [
            [str(col) for col in df.columns.tolist()]
        ]

        for linha in df.values.tolist():
            linhas.append([
                "" if valor is None else str(valor).strip()
                for valor in linha
            ])

        CACHE[tipo] = {
            "tempo": agora,
            "dados": linhas,
        }

        print(
            f"[GOOGLE SHEETS] {tipo}: "
            f"{len(linhas) - 1} linhas carregadas."
        )

        return linhas

    except urllib.error.HTTPError as e:
        print(
            f"[ERRO GOOGLE SHEETS] {tipo} - "
            f"HTTP {e.code}: {e.reason}"
        )
        return None

    except urllib.error.URLError as e:
        print(
            f"[ERRO GOOGLE SHEETS] {tipo} - "
            f"conexão: {e.reason}"
        )
        return None

    except Exception as e:
        print(
            f"[ERRO GOOGLE SHEETS] {tipo} - {repr(e)}"
        )
        traceback.print_exc()
        return None


# ============================================================
# IDENTIFICAÇÃO DE CIDADE / STATUS
# ============================================================

def encontrar_cidade_na_linha(linha):
    """
    Procura a cidade em qualquer coluna da linha.
    Primeiro tenta igualdade exata.
    Depois aceita uma célula que contenha o nome da cidade.
    """

    cidades = list(MAPA_FILIAIS_ORIGINAL.keys())

    valores = [
        normalizar_texto(valor)
        for valor in linha
        if normalizar_texto(valor)
    ]

    # 1 - Igualdade exata
    for valor in valores:
        for cidade in cidades:
            if valor == normalizar_texto(cidade):
                return cidade

    # 2 - Cidade contida na célula
    for valor in valores:
        for cidade in cidades:
            cidade_norm = normalizar_texto(cidade)

            if (
                len(cidade_norm) >= 5
                and cidade_norm in valor
            ):
                return cidade

    return ""


def encontrar_status_na_linha(linha):
    """
    Procura SIM/NÃO em toda a linha.
    """

    for valor in linha:
        valor_normalizado = normalizar_texto(valor)

        if valor_normalizado == "sim":
            return "SIM"

    for valor in linha:
        valor_normalizado = normalizar_texto(valor)

        if valor_normalizado in ("nao", "não"):
            return "NÃO"

    return "-"


def localizar_marcadores_tecnico(linha):
    """
    Identifica os campos de técnico da planilha.
    """

    tecnicos = []

    for i, valor in enumerate(linha):
        texto = str(valor).strip()
        upper = texto.upper()

        if (
            "PRÓPRIOS" in upper
            or "PROPRIOS" in upper
            or "TERCEIRIZADOS" in upper
            or "TERCEIRIZADO" in upper
        ):
            jornada = "-"

            if i + 1 < len(linha):
                proximo = str(linha[i + 1]).strip()

                if proximo:
                    jornada = proximo

            tecnicos.append((texto, jornada))

    return tecnicos


# ============================================================
# EXTRAÇÃO DO PLANTÃO
# ============================================================

def extrair_dados_plantao_linha(linha):
    cidade = encontrar_cidade_na_linha(linha)
    filial = obter_filial_por_cidade(cidade)

    status_planilha = encontrar_status_na_linha(linha)

    tecnicos = localizar_marcadores_tecnico(linha)

    tecnico_sabado = "Nenhum técnico escalado"
    jornada_sabado = "-"

    tecnico_domingo = "Nenhum técnico escalado"
    jornada_domingo = "-"

    if len(tecnicos) >= 1:
        tecnico_sabado, jornada_sabado = tecnicos[0]

    if len(tecnicos) >= 2:
        tecnico_domingo, jornada_domingo = tecnicos[1]

    tem_sabado = len(tecnicos) >= 1
    tem_domingo = len(tecnicos) >= 2

    # Se a planilha diz SIM, usamos os técnicos encontrados.
    # Se não houver técnico explícito, o resultado fica NÃO.
    status_sabado = (
        "Sim"
        if status_planilha == "SIM" and tem_sabado
        else "Não"
    )

    status_domingo = (
        "Sim"
        if status_planilha == "SIM" and tem_domingo
        else "Não"
    )

    return {
        "filial": filial,
        "supervisor": str(linha[0]).strip() if linha else "",
        "cidade": cidade,
        "status": (
            "SIM"
            if status_planilha == "SIM"
            else "NÃO"
        ),
        "sabado": status_sabado,
        "domingo": status_domingo,
        "tecnico_sabado": tecnico_sabado,
        "jornada_sabado": jornada_sabado,
        "tecnico_domingo": tecnico_domingo,
        "jornada_domingo": jornada_domingo,
        "tem_tecnico_real": tem_sabado or tem_domingo,
    }


# ============================================================
# AGENDAMENTOS
# ============================================================

def extrair_agendamentos(linhas):
    cidades_map = {}

    for linha in linhas:
        if not linha:
            continue

        for idx, valor in enumerate(linha):
            nome_col = str(valor).strip()

            if not nome_col:
                continue

            nome_norm = normalizar_texto(nome_col)

            if nome_norm in (
                "cidade",
                "responsavel",
                "responsavel",
                "total conectados",
                "regional",
                ":-:",
                "|",
            ):
                continue

            if idx + 3 >= len(linha):
                continue

            conectados = (
                str(linha[idx + 1]).strip()
                if idx + 1 < len(linha)
                else "-"
            )

            ttth = (
                str(linha[idx + 2]).strip()
                if idx + 2 < len(linha)
                else "-"
            )

            responsavel = (
                str(linha[idx + 3]).strip()
                if idx + 3 < len(linha)
                else "Não informado"
            )

            regional = (
                str(linha[idx + 4]).strip()
                if idx + 4 < len(linha)
                else "-"
            )

            if normalizar_texto(responsavel) == "responsavel":
                continue

            # Só aceita como cidade se ela estiver no mapa.
            cidade_oficial = ""

            for cidade in MAPA_FILIAIS_ORIGINAL:
                if normalizar_texto(cidade) == normalizar_texto(nome_col):
                    cidade_oficial = cidade
                    break

            if not cidade_oficial:
                continue

            cidades_map[cidade_oficial] = {
                "cidade": cidade_oficial,
                "conectados": conectados,
                "ttth": ttth,
                "responsavel": responsavel,
                "regional": regional,
            }

            break

    return cidades_map


# ============================================================
# BUSCA
# ============================================================

def encontrar_cidades_por_termo(termo, cidades_disponiveis):
    termo_norm = normalizar_texto(termo)

    encontradas = []

    # Busca exata/parcial.
    for cidade in cidades_disponiveis:
        cidade_norm = normalizar_texto(cidade)

        if (
            termo_norm == cidade_norm
            or termo_norm in cidade_norm
        ):
            encontradas.append(cidade)

    if encontradas:
        return encontradas

    # Busca por sigla.
    if termo_norm in MAPEAMENTO_SIGLAS_AGENDAMENTO:
        cidade = MAPEAMENTO_SIGLAS_AGENDAMENTO[termo_norm]

        for disponivel in cidades_disponiveis:
            if normalizar_texto(disponivel) == normalizar_texto(cidade):
                return [disponivel]

    # Fuzzy.
    if cidades_disponiveis:
        match = process.extractOne(
            termo_norm,
            cidades_disponiveis,
            scorer=lambda a, b, **kwargs: fuzz.WRatio(
                normalizar_texto(a),
                normalizar_texto(b),
            ),
        )

        if match and match[1] >= 65:
            return [match[0]]

    return []


def encontrar_filiais_por_termo(termo):
    termo_norm = normalizar_texto(termo)

    filiais = sorted(
        set(MAPA_FILIAIS_ORIGINAL.values())
    )

    encontradas = [
        filial
        for filial in filiais
        if termo_norm in normalizar_texto(filial)
    ]

    if encontradas:
        return encontradas

    match = process.extractOne(
        termo_norm,
        filiais,
        scorer=lambda a, b, **kwargs: fuzz.WRatio(
            normalizar_texto(a),
            normalizar_texto(b),
        ),
    )

    if match and match[1] >= 70:
        return [match[0]]

    return []


# ============================================================
# ROTAS
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/buscar", methods=["POST"])
def buscar():
    try:
        dados = request.get_json(silent=True) or {}

        termo = str(
            dados.get("termo", "")
        ).strip()

        tipo = str(
            dados.get("tipo", "agendamento")
        ).strip().lower()

        if not termo:
            return jsonify({
                "sucesso": False,
                "erro": "Informe um termo para consultar.",
            }), 400

        # ----------------------------------------------------
        # AGENDAMENTO
        # ----------------------------------------------------

        if tipo == "agendamento":
            linhas = ler_csv_online(
                URL_AGENDAMENTOS,
                "agendamento",
            )

            if linhas is None:
                return jsonify({
                    "sucesso": False,
                    "erro": (
                        "Não foi possível conectar ao Google Sheets. "
                        "Verifique se a planilha está pública e se "
                        "a URL de exportação está correta."
                    ),
                }), 500

            cidades_map = extrair_agendamentos(linhas)

            cidades_disponiveis = list(
                cidades_map.keys()
            )

            cidades_encontradas = encontrar_cidades_por_termo(
                termo,
                cidades_disponiveis,
            )

            resultados = [
                cidades_map[cidade]
                for cidade in cidades_encontradas
                if cidade in cidades_map
            ]

            return jsonify({
                "sucesso": True,
                "total": len(resultados),
                "dados": resultados,
            })

        # ----------------------------------------------------
        # PLANTÃO / SOBREAVISO
        # ----------------------------------------------------

        if tipo in (
            "plantao",
            "sobreaviso",
            "plantão",
        ):
            linhas = ler_csv_online(
                URL_PLANTAO,
                "plantao",
            )

            if linhas is None:
                return jsonify({
                    "sucesso": False,
                    "erro": (
                        "Não foi possível conectar ao Google Sheets "
                        "do Plantão/Sobreaviso. "
                        "Verifique se a planilha está pública."
                    ),
                }), 500

            dados_planilha = []

            for linha in linhas:
                dados_linha = extrair_dados_plantao_linha(
                    linha
                )

                if dados_linha["cidade"]:
                    dados_planilha.append(
                        dados_linha
                    )

            # Remove duplicados mantendo a última informação.
            dados_por_cidade = {}

            for item in dados_planilha:
                dados_por_cidade[
                    normalizar_texto(item["cidade"])
                ] = item

            dados_planilha = list(
                dados_por_cidade.values()
            )

            cidades_disponiveis = [
                item["cidade"]
                for item in dados_planilha
            ]

            termo_norm = normalizar_texto(termo)

            # "todas as cidades"
            termo_todas = termo_norm.replace(
                " ",
                "_",
            )

            if termo_todas in (
                "todas_as_cidades",
                "todas",
                "todos",
            ):
                resultados = sorted(
                    dados_planilha,
                    key=lambda x: (
                        x["filial"],
                        x["cidade"],
                    ),
                )

                return jsonify({
                    "sucesso": True,
                    "total": len(resultados),
                    "dados": resultados,
                })

            # Primeiro verifica se é filial.
            filiais_encontradas = encontrar_filiais_por_termo(
                termo
            )

            if filiais_encontradas:
                resultados = [
                    item
                    for item in dados_planilha
                    if item["filial"] in filiais_encontradas
                ]

                resultados.sort(
                    key=lambda x: x["cidade"]
                )

                return jsonify({
                    "sucesso": True,
                    "total": len(resultados),
                    "dados": resultados,
                })

            # Depois verifica cidade.
            cidades_encontradas = encontrar_cidades_por_termo(
                termo,
                cidades_disponiveis,
            )

            resultados = [
                item
                for item in dados_planilha
                if item["cidade"] in cidades_encontradas
            ]

            if not resultados:
                # Caso a cidade esteja no mapa mas não tenha
                # aparecido corretamente na planilha.
                cidades_mapa = encontrar_cidades_por_termo(
                    termo,
                    list(MAPA_FILIAIS_ORIGINAL.keys()),
                )

                if cidades_mapa:
                    return jsonify({
                        "sucesso": True,
                        "total": 0,
                        "mensagem": (
                            f"{cidades_mapa[0]} não possui "
                            "registro de sobreaviso na planilha."
                        ),
                        "dados": [],
                    })

                return jsonify({
                    "sucesso": True,
                    "total": 0,
                    "mensagem": (
                        "Cidade ou filial não encontrada."
                    ),
                    "dados": [],
                })

            return jsonify({
                "sucesso": True,
                "total": len(resultados),
                "dados": resultados,
            })

        return jsonify({
            "sucesso": False,
            "erro": f"Tipo de consulta inválido: {tipo}",
        }), 400

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "sucesso": False,
            "erro": f"Erro interno: {str(e)}",
        }), 500


# ============================================================
# ROTA DE TESTE
# ============================================================

@app.route("/api/teste")
def teste():
    resultado = {
        "agendamentos": False,
        "plantao": False,
    }

    dados_agendamento = ler_csv_online(
        URL_AGENDAMENTOS,
        "agendamento",
    )

    dados_plantao = ler_csv_online(
        URL_PLANTAO,
        "plantao",
    )

    resultado["agendamentos"] = (
        dados_agendamento is not None
    )

    resultado["plantao"] = (
        dados_plantao is not None
    )

    return jsonify({
        "sucesso": True,
        "google_sheets": resultado,
    })


# ============================================================
# VERCEL
# ============================================================

application = app


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
