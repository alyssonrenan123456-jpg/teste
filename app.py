import io
import traceback
from flask import Flask, jsonify, render_template, request
import pandas as pd
from rapidfuzz import fuzz, process

app = Flask(__name__)

# ============================================================
# URLs DE EXPORTAÇÃO CSV (Google Sheets)
# ============================================================
URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"


def ler_csv_online(url):
    """Lê o CSV diretamente usando pandas, ideal e seguro para a Vercel."""
    try:
        df = pd.read_csv(url, dtype=str)
        df = df.fillna("")  # Substitui valores vazios por string vazia
        return [df.columns.tolist()] + df.values.tolist()
    except Exception as e:
        print(f"[ERRO AO LER PLANILHA COM PANDAS] {e}")
        return None


# ============================================================
# FUNÇÃO DE NORMALIZAÇÃO
# ============================================================

def normalizar_texto(texto):
    if texto is None:
        return ""
    texto = str(texto).strip().lower()
    tabela = str.maketrans("áàãâäéèêëíìîïóòõôöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return " ".join(texto.translate(tabela).split())


# ============================================================
# SIGLAS E MAPAS DE FILIAIS
# ============================================================

MAPEAMENTO_SIGLAS_AGENDAMENTO = {
    "bnu": "Brunópolis", "cnv": "Campos Novos", "ctb": "Curitibanos", "fbg": "Fraiburgo",
    "frr": "Frei Rogério", "iom": "Iomerê", "mca": "Monte Carlo", "ppr": "Pinheiro Preto",
    "vda": "Videira", "agr": "Agronômica", "aur": "Aurora", "itu": "Ituporanga",
    "lon": "Lontras", "ptl": "Petrolândia", "prd": "Pouso Redondo", "rsl": "Rio do Sul",
    "cbs": "Campo Belo do Sul", "cat": "Capão Alto", "cpo": "Correia Pinto", "lgs": "Lages",
    "pta": "Ponte Alta", "api": "Apiúna", "asc": "Ascurra", "blu": "Blumenau",
    "idl": "Indaial", "rod": "Rodeio", "ace": "Água Doce", "ctv": "Catanduvas",
    "hdo": "Herval d'Oeste", "ibc": "Ibicaré", "ipi": "Ipira", "jba": "Joaçaba",
    "lzn": "Luzerna", "ptb": "Piratuba", "svs": "Salto Veloso", "tan": "Tangará",
    "tzs": "Treze Tílias", "ant": "Anita Garibaldi", "cdr": "Caçador", "mra": "Macieira",
    "pan": "Ponte Alta do Norte", "sct": "São Cristóvão do Sul", "arq": "Araquari",
    "bbs": "Balneário Barra do Sul", "brq": "Brusque", "cmb": "Camboriú", "cal": "Campo Alegre",
    "grm": "Guaramirim", "jas": "Jaraguá do Sul", "jve": "Joinville", "las": "Luiz Alves",
    "mas": "Massaranduba", "sfs": "São Francisco do Sul", "sch": "Schroeder", "evv": "Erval Velho",
    "ldp": "Lacerdópolis", "rdc": "Rio dos Cedros", "bpi": "Balneário Piçarras", "bve": "Barra Velha",
    "nav": "Navegantes", "pen": "Penha", "sji": "São João do Itaperiú", "gva": "Garuva", "itp": "Itapoá"
}

MAPA_FILIAIS_ORIGINAL = {
    "Brunópolis": "01 - MCA", "Campos Novos": "01 - MCA", "Curitibanos": "01 - MCA",
    "Fraiburgo": "01 - MCA", "Frei Rogério": "01 - MCA", "Iomerê": "01 - MCA",
    "Monte Carlo": "01 - MCA", "Pinheiro Preto": "01 - MCA", "Videira": "01 - MCA",
    "Agronômica": "02 - RSL", "Aurora": "02 - RSL", "Ituporanga": "02 - RSL",
    "Lontras": "02 - RSL", "Petrolândia": "02 - RSL", "Pouso Redondo": "02 - RSL",
    "Rio do Sul": "02 - RSL", "Campo Belo do Sul": "03 - LGS", "Capão Alto": "03 - LGS",
    "Correia Pinto": "03 - LGS", "Lages": "03 - LGS", "Ponte Alta": "03 - LGS",
    "Apiúna": "04 - BLU", "Ascurra": "04 - BLU", "Blumenau": "04 - BLU",
    "Indaial": "04 - BLU", "Rodeio": "04 - BLU", "Água Doce": "06 - JBA",
    "Catanduvas": "06 - JBA", "Herval d'Oeste": "06 - JBA", "Ibicaré": "06 - JBA",
    "Ipira": "06 - JBA", "Joaçaba": "06 - JBA", "Luzerna": "06 - JBA",
    "Piratuba": "06 - JBA", "Salto Veloso": "06 - JBA", "Tangará": "06 - JBA",
    "Treze Tílias": "06 - JBA", "Anita Garibaldi": "07 - ANT", "Caçador": "08 - CDR",
    "Macieira": "08 - CDR", "Ponte Alta do Norte": "09 - SCT", "São Cristóvão do Sul": "09 - SCT",
    "Araquari": "10 - JVE", "Balneário Barra do Sul": "10 - JVE", "Brusque": "10 - JVE",
    "Camboriú": "10 - JVE", "Campo Alegre": "10 - JVE", "Guaramirim": "10 - JVE",
    "Jaraguá do Sul": "10 - JVE", "Joinville": "10 - JVE", "Luiz Alves": "10 - JVE",
    "Massaranduba": "10 - JVE", "São Francisco do Sul": "10 - JVE", "Schroeder": "10 - JVE",
    "Erval Velho": "1002 - EVV", "Lacerdópolis": "1002 - EVV", "Rio dos Cedros": "1063 - RDC",
    "Balneário Piçarras": "11 - BVE", "Barra Velha": "11 - BVE", "Navegantes": "11 - BVE",
    "Penha": "11 - BVE", "São João do Itaperiú": "11 - BVE", "Garuva": "12 - ITP", "Itapoá": "12 - ITP",
    
    "01 - MCA": "01 - MCA", "02 - RSL": "02 - RSL", "03 - LGS": "03 - LGS",
    "04 - BLU": "04 - BLU", "06 - JBA": "06 - JBA", "07 - ANT": "07 - ANT",
    "08 - CDR": "08 - CDR", "09 - SCT": "09 - SCT", "10 - JVE": "10 - JVE",
    "1002 - EVV": "1002 - EVV", "1063 - RDC": "1063 - RDC", "11 - BVE": "11 - BVE",
    "12 - ITP": "12 - ITP",
    "VDA": "01 - MCA", "MCA": "01 - MCA", "FBG": "01 - MCA", "RSL": "02 - RSL", 
    "LGS": "03 - LGS", "BLU": "04 - BLU", "JBA": "06 - JBA", "ANT": "07 - ANT", 
    "CDR": "08 - CDR", "SCT": "09 - SCT", "JVE": "10 - JVE", "EVV": "1002 - EVV", 
    "RDC": "1063 - RDC", "BVE": "11 - BVE", "ITP": "12 - ITP", "BPI": "11 - BVE", 
    "BBS": "10 - JVE", "ARQ": "10 - JVE", "ASC": "04 - BLU", "IDL": "04 - BLU", 
    "HDO": "06 - JBA", "IBC": "06 - JBA", "PTB": "06 - JBA", "TAN": "06 - JBA"
}

MAPA_FILIAIS = {normalizar_texto(k): v for k, v in MAPA_FILIAIS_ORIGINAL.items()}


# ============================================================
# FUNÇÕES DE AUXÍLIO
# ============================================================

def obter_filial_por_cidade(cidade):
    if not cidade:
        return "Não mapeada"
    return MAPA_FILIAIS.get(normalizar_texto(cidade), "Não mapeada")


def encontrar_cidade_na_linha(linha):
    cidades = [k for k in MAPA_FILIAIS_ORIGINAL.keys() if " - " not in k and len(k) > 3]
    for valor in linha:
        valor_normalizado = normalizar_texto(valor)
        if not valor_normalizado:
            continue
        for cidade in cidades:
            if valor_normalizado == normalizar_texto(cidade):
                return cidade
    return ""


def extrair_dados_plantao_linha(linha):
    supervisor = str(linha[0]).strip() if len(linha) > 0 else ""
    cidade = encontrar_cidade_na_linha(linha)
    filial = obter_filial_por_cidade(cidade)

    tec_sabado, jornada_sabado = "Nenhum técnico escalado", "-"
    tec_domingo, jornada_domingo = "Nenhum técnico escalado", "-"
    tecnicos_encontrados = []

    for i, valor in enumerate(linha):
        valor = str(valor).strip()
        valor_upper = valor.upper()
        if "PRÓPRIOS" in valor_upper or "TERCEIRIZADOS" in valor_upper:
            jornada = "-"
            if i + 1 < len(linha):
                proximo = str(linha[i + 1]).strip()
                if ":" in proximo or "H" in proximo.upper() or "AS" in proximo.upper() or "-" in proximo:
                    jornada = proximo
            tecnicos_encontrados.append((valor, jornada))

    if len(tecnicos_encontrados) >= 1:
        tec_sabado, jornada_sabado = tecnicos_encontrados[0]
    if len(tecnicos_encontrados) >= 2:
        tec_domingo, jornada_domingo = tecnicos_encontrados[1]

    tem_tec_sabado = tec_sabado not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_sabado != ""
    tem_tec_domingo = tec_domingo not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_domingo != ""
    
    tem_sobreaviso_real = tem_tec_sabado or tem_tec_domingo

    return {
        "filial": filial, "supervisor": supervisor, "cidade": cidade,
        "status": "SIM" if tem_sobreaviso_real else "NÃO",
        "tecnico_sabado": tec_sabado, "jornada_sabado": jornada_sabado,
        "tecnico_domingo": tec_domingo, "jornada_domingo": jornada_domingo,
        "tem_tecnico_real": tem_sobreaviso_real,
    }


def extrair_dados_matriz_geral(linha):
    """Extrai os dados para a Matriz Geral exibindo 'Sim' ou 'Não' para sábado e domingo."""
    cidade = encontrar_cidade_na_linha(linha)
    if not cidade:
        return None
    filial = obter_filial_por_cidade(cidade)

    tecnicos_encontrados = []
    for i, valor in enumerate(linha):
        valor_str = str(valor).strip()
        valor_upper = valor_str.upper()
        if "PRÓPRIOS" in valor_upper or "TERCEIRIZADOS" in valor_upper:
            tecnicos_encontrados.append((i, valor_str))

    tec_sabado = "Não"
    tec_domingo = "Não"

    if len(tecnicos_encontrados) >= 1:
        # Valida se o técnico de sábado realmente existe e não é vazio/opção inválida
        t_val = tecnicos_encontrados[0][1]
        if t_val not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and t_val != "":
            tec_sabado = "Sim"

    if len(tecnicos_encontrados) >= 2:
        # Valida se o técnico de domingo realmente existe e não é vazio/opção inválida
        t_val = tecnicos_encontrados[1][1]
        if t_val not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and t_val != "":
            tec_domingo = "Sim"

    return {
        "filial": filial, 
        "cidade": cidade,
        "tecnico_sabado": tec_sabado,
        "tecnico_domingo": tec_domingo,
    }


# ============================================================
# ROTAS FLASK
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status-sheets", methods=["GET"])
def status_sheets():
    res_agendamentos = ler_csv_online(URL_AGENDAMENTOS)
    res_plantao = ler_csv_online(URL_PLANTAO)
    return jsonify({
        "sucesso": True,
        "google_sheets": {
            "agendamentos": res_agendamentos is not None,
            "plantao": res_plantao is not None
        }
    })


@app.route("/api/buscar", methods=["POST"])
def buscar():
    try:
        dados = request.json or {}
        termo = str(dados.get("termo", "")).strip()
        tipo = dados.get("tipo", "agendamento")

        if not termo:
            return jsonify({"sucesso": False, "erro": "Informe um termo para consultar."}), 400

        url = URL_AGENDAMENTOS if tipo == "agendamento" else URL_PLANTAO
        linhas = ler_csv_online(url)

        if not linhas:
            return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets na Vercel."}), 500

        termo_normalizado = normalizar_texto(termo)
        tabela_mapa = str.maketrans("áàãâäéèêëíìîïóòõôöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
        resultados = []

        if tipo == "agendamento":
            cidades_map = {}
            for linha in linhas:
                for idx, col_val in enumerate(linha):
                    nome_col = str(col_val).strip()
                    if not nome_col or nome_col.upper() in ["CIDADE", ":-:", "RESPONSÁVEL", "TOTAL CONECTADOS", "|"]:
                        continue
                    if idx + 3 >= len(linha):
                        continue

                    conectados = str(linha[idx + 1]).strip() if idx + 1 < len(linha) else "-"
                    ttth = str(linha[idx + 2]).strip() if idx + 2 < len(linha) else "-"
                    responsavel = str(linha[idx + 3]).strip() if idx + 3 < len(linha) else "Não informado"
                    regional = str(linha[idx + 4]).strip() if idx + 4 < len(linha) else "-"

                    if responsavel.upper() in ["RESPONŚAVEL", "RESPONSÁVEL"]:
                        continue

                    cidades_map[nome_col] = {
                        "cidade": nome_col, "conectados": conectados,
                        "ttth": ttth, "responsavel": responsavel, "regional": regional
                    }
                    break

            cidades_disponiveis = list(cidades_map.keys())
            cidades_alvo = []

            if termo_normalizado in MAPEAMENTO_SIGLAS_AGENDAMENTO:
                cidades_alvo.append(MAPEAMENTO_SIGLAS_AGENDAMENTO[termo_normalizado])
            else:
                for cidade in cidades_disponiveis:
                    cidade_limpa = " ".join(cidade.strip().lower().translate(tabela_mapa).split())
                    if termo_normalizado in cidade_limpa:
                        cidades_alvo.append(cidade)

            cidades_encontradas = [
                cidade for cidade in cidades_disponiveis
                if any(" ".join(alvo.strip().lower().translate(tabela_mapa).split()) == " ".join(cidade.strip().lower().translate(tabela_mapa).split()) for alvo in cidades_alvo)
            ]

            if not cidades_encontradas and cidades_disponiveis:
                match = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio)
                if match and match[1] >= 75:
                    cidades_encontradas = [match[0]]

            if not cidades_encontradas:
                return jsonify({"sucesso": True, "total": 0, "mensagem": "Cidade ou sigla não encontrada no Agendamento", "dados": []})

            for cidade in cidades_encontradas:
                if cidade in cidades_map:
                    resultados.append(cidades_map[cidade])
        else:
            if termo_normalizado == "todas_as_cidades":
                for linha in linhas:
                    dados_linha = extrair_dados_matriz_geral(linha)
                    if dados_linha:
                        resultados.append(dados_linha)
                return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

            cidades_disponiveis = [k for k in MAPA_FILIAIS_ORIGINAL.keys() if " - " not in k and len(k) > 3]
            filiais_disponiveis = list(set(MAPA_FILIAIS_ORIGINAL.values()))
            cidades_encontradas, filiais_encontradas = [], []

            for cidade in cidades_disponiveis:
                if termo_normalizado in normalizar_texto(cidade):
                    cidades_encontradas.append(cidade)

            for filial in filiais_disponiveis:
                if termo_normalizado in normalizar_texto(filial):
                    filiais_encontradas.append(filial)

            if not cidades_encontradas and not filiais_encontradas:
                match_cidade = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio)
                match_filial = process.extractOne(termo, filiais_disponiveis, scorer=fuzz.WRatio)
                score_cidade = match_cidade[1] if match_cidade else 0
                score_filial = match_filial[1] if match_filial else 0

                if score_cidade >= 75 and score_cidade >= score_filial:
                    cidades_encontradas = [match_cidade[0]]
                elif score_filial >= 75:
                    filiais_encontradas = [match_filial[0]]

            if not cidades_encontradas and not filiais_encontradas:
                return jsonify({"sucesso": True, "total": 0, "mensagem": "Essa cidade não possui sobreaviso no momento", "dados": []})

            for linha in linhas:
                dados_linha = extrair_dados_plantao_linha(linha)
                cidade = dados_linha["cidade"]
                filial = dados_linha["filial"]

                if not cidade:
                    continue

                if cidades_encontradas:
                    if cidade in cidades_encontradas:
                        resultados.append(dados_linha)
                elif filiais_encontradas:
                    if filial in filiais_encontradas and dados_linha["tem_tecnico_real"]:
                        resultados.append(dados_linha)

            if len(resultados) == 0:
                return jsonify({"sucesso": True, "total": 0, "mensagem": "Essa cidade não possui sobreaviso no momento", "dados": []})

        return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": str(e)}), 500


# VARIÁVEIS EXIGIDAS PELA VERCEL (OBRIGATÓRIO)
application = app

if __name__ == "__main__":
    app.run(debug=True)
