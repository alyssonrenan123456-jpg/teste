import io
import csv
import traceback
from flask import Flask, jsonify, render_template, request
from rapidfuzz import fuzz, process
import requests

app = Flask(__name__)

# ============================================================
# URLs DE EXPORTAÇÃO CSV
# ============================================================
URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWh1vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"


def ler_csv_online(url):
    """Baixa o CSV usando requests e trata possíveis erros."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"[DEBUG] Status HTTP para {url}: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[ERRO] Falha ao baixar planilha. Status HTTP: {response.status_code}")
            return None
            
        conteudo = response.text
        
        if "<html" in conteudo.lower() or "<head" in conteudo.lower():
            print("[ERRO] A URL retornou HTML. A planilha pode não estar acessível publicamente.")
            return None
            
        return list(csv.reader(io.StringIO(conteudo)))
    except Exception as e:
        print(f"[EXCEÇÃO NO DOWNLOAD DO CSV] {e}")
        return None


# ============================================================
# SIGLAS E MAPAS
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
}

MAPA_FILIAIS = {k.strip().lower(): v for k, v in MAPA_FILIAIS_ORIGINAL.items()}


# ============================================================
# FUNÇÕES DE AUXÍLIO
# ============================================================

def normalizar_texto(texto):
    if texto is None:
        return ""
    texto = str(texto).strip().lower()
    tabela = str.maketrans("áàãâäéèêëíìîïóòõôöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return " ".join(texto.translate(tabela).split())


def obter_filial_por_cidade(cidade):
    if not cidade:
        return "Não mapeada"
    return MAPA_FILIAIS.get(normalizar_texto(cidade), "Não mapeada")


def encontrar_cidade_na_linha(linha):
    cidades = list(MAPA_FILIAIS_ORIGINAL.keys())
    for valor in linha:
        valor_normalizado = normalizar_texto(valor)
        if not valor_normalizado:
            continue
        for cidade in cidades:
            if valor_normalizado == normalizar_texto(cidade):
                return cidade
    return ""


def encontrar_status_na_linha(linha):
    for valor in linha:
        valor_normalizado = normalizar_texto(valor)
        if valor_normalizado == "sim":
            return "SIM"
        if valor_normalizado in ("nao", "não"):
            return "NÃO"
    return "-"


def extrair_dados_plantao_linha(linha):
    supervisor = linha[0].strip() if len(linha) > 0 else ""
    cidade = encontrar_cidade_na_linha(linha)
    filial = obter_filial_por_cidade(cidade)
    status_bruto = encontrar_status_na_linha(linha)

    tec_sabado, jornada_sabado = "Nenhum técnico escalado", "-"
    tec_domingo, jornada_domingo = "Nenhum técnico escalado", "-"
    tecnicos_encontrados = []

    for i, valor in enumerate(linha):
        valor = valor.strip()
        valor_upper = valor.upper()
        if "PRÓPRIOS" in valor_upper or "TERCEIRIZADOS" in valor_upper:
            jornada = "-"
            if i + 1 < len(linha):
                proximo = linha[i + 1].strip()
                if ":" in proximo or "H" in proximo.upper() or "AS" in proximo.upper() or "-" in proximo:
                    jornada = proximo
            tecnicos_encontrados.append((valor, jornada))

    if len(tecnicos_encontrados) >= 1:
        tec_sabado, jornada_sabado = tecnicos_encontrados[0]
    if len(tecnicos_encontrados) >= 2:
        tec_domingo, jornada_domingo = tecnicos_encontrados[1]

    tem_tec_sabado = tec_sabado not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_sabado != ""
    tem_tec_domingo = tec_domingo not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_domingo != ""
    tem_sobreaviso_real = status_bruto == "SIM" and (tem_tec_sabado or tem_tec_domingo)

    return {
        "filial": filial, "supervisor": supervisor, "cidade": cidade,
        "status": "SIM" if tem_sobreaviso_real else "NÃO",
        "tecnico_sabado": tec_sabado, "jornada_sabado": jornada_sabado,
        "tecnico_domingo": tec_domingo, "jornada_domingo": jornada_domingo,
        "tem_tecnico_real": tem_sobreaviso_real,
    }


def extrair_dados_matriz_geral(linha):
    cidade = encontrar_cidade_na_linha(linha)
    if not cidade:
        return None
    filial = obter_filial_por_cidade(cidade)
    status = encontrar_status_na_linha(linha)

    tecnicos_encontrados = []
    for valor in linha:
        valor_upper = valor.strip().upper()
        if "PRÓPRIOS" in valor_upper or "TERCEIRIZADOS" in valor_upper:
            tecnicos_encontrados.append(valor.strip())

    tem_sabado = len(tecnicos_encontrados) >= 1
    tem_domingo = len(tecnicos_encontrados) >= 2

    return {
        "filial": filial, "cidade": cidade,
        "tecnico_sabado": "Sim" if status == "SIM" and tem_sabado else "Não",
        "tecnico_domingo": "Sim" if status == "SIM" and tem_domingo else "Não",
    }


# ============================================================
# ROTAS FLASK
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


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
            return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets. Verifique o link."}), 500

        termo_normalizado = normalizar_texto(termo)
        resultados = []

        if tipo == "agendamento":
            cidades_map = {}
            for linha in linhas:
                for idx, col_val in enumerate(linha):
                    nome_col = col_val.strip()
                    if not nome_col or nome_col.upper() in ["CIDADE", ":-:", "RESPONSÁVEL", "TOTAL CONECTADOS", "|"]:
                        continue
                    if idx + 3 >= len(linha):
                        continue

                    conectados = linha[idx + 1].strip() if idx + 1 < len(linha) else "-"
                    ttth = linha[idx + 2].strip() if idx + 2 < len(linha) else "-"
                    responsavel = linha[idx + 3].strip() if idx + 3 < len(linha) else "Não informado"
                    regional = linha[idx + 4].strip() if idx + 4 < len(linha) else "-"

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
                    if termo_normalizado in normalizar_texto(cidade):
                        cidades_alvo.append(cidade)

            cidades_encontradas = [
                cidade for cidade in cidades_disponiveis
                if any(normalizar_texto(alvo) == normalizar_texto(cidade) for alvo in cidades_alvo)
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
            cidades_disponiveis = list(MAPA_FILIAIS_ORIGINAL.keys())
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

                if score_cidade >= 60 and score_cidade >= score_filial:
                    cidades_encontradas = [match_cidade[0]]
                elif score_filial >= 60:
                    filiais_encontradas = [match_filial[0]]

            if termo_normalizado == "todas_as_cidades":
                for linha in linhas:
                    dados_linha = extrair_dados_matriz_geral(linha)
                    if dados_linha:
                        resultados.append(dados_linha)
                return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

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
        print("================ ERRO CRTICO NA ROTA /API/BUSCAR ================")
        traceback.print_exc()
        print("=================================================================")
        return jsonify({"sucesso": False, "erro": str(e)}), 500


application = app

if __name__ == "__main__":
    app.run(debug=True)
