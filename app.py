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

# Novas URLs baseadas nos GIDs das abas de Sábado e Domingo do Gustavo
URL_PLANTAO_SABADO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1364670416"
URL_PLANTAO_DOMINGO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=935861385"


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


def processar_dados_plantao():
    """Lê as abas de Sábado e Domingo e cruza os dados por cidade."""
    linhas_sabado = ler_csv_online(URL_PLANTAO_SABADO)
    linhas_domingo = ler_csv_online(URL_PLANTAO_DOMINGO)

    dados_consolidados = {}

    # Função auxiliar para popular o dicionário com base nas linhas de uma aba
    def parsear_linhas(linhas):
        if not linhas or len(linhas) < 2:
            return {}
        
        cabecalho = [str(c).strip().upper() for c in linhas[0]]
        
        # Identifica os índices das colunas com base nos novos nomes da planilha
        idx_cidade = -1
        idx_tec = -1
        idx_jornada = -1

        for i, col in enumerate(cabecalho):
            if "CIDADE" in col:
                idx_cidade = i
            elif "TÉCNICO" in col or "TECNICO" in col:
                idx_tec = i
            elif "JORNADA" in col:
                idx_jornada = i

        # Fallback padrão caso os títulos exatos mudem levemente
        if idx_cidade == -1: idx_cidade = 2
        if idx_tec == -1: idx_tec = 3
        if idx_jornada == -1: idx_jornada = 4

        mapa_aba = {}
        for linha in linhas[1:]:
            if len(linha) <= max(idx_cidade, idx_tec):
                continue
            
            cidade = str(linha[idx_cidade]).strip()
            if not cidade or cidade.upper() == "NAN":
                continue
                
            tecnico = str(linha[idx_tec]).strip() if len(linha) > idx_tec else "Nenhum técnico escalado"
            jornada = str(linha[idx_jornada]).strip() if len(linha) > idx_jornada else "-"
            
            if not tecnico or tecnico.upper() == "NAN":
                tecnico = "Nenhum técnico escalado"
            if not jornada or jornada.upper() == "NAN":
                jornada = "-"

            mapa_aba[cidade] = {"tecnico": tecnico, "jornada": jornada}
            
        return mapa_aba

    sabado_dict = parsear_linhas(linhas_sabado)
    domingo_dict = parsear_linhas(linhas_domingo)

    # Unifica todas as cidades conhecidas do mapa de filiais
    todas_cidades = [k for k in MAPA_FILIAIS_ORIGINAL.keys() if " - " not in k and len(k) > 3]

    for cidade in todas_cidades:
        filial = obter_filial_por_cidade(cidade)
        
        # Dados de sábado
        info_sab = sabado_dict.get(cidade, {"tecnico": "Nenhum técnico escalado", "jornada": "-"})
        tec_sab = info_sab["tecnico"]
        jor_sab = info_sab["jornada"]

        # Dados de domingo
        info_dom = domingo_dict.get(cidade, {"tecnico": "Nenhum técnico escalado", "jornada": "-"})
        tec_dom = info_dom["tecnico"]
        jor_dom = info_dom["jornada"]

        tem_sab = tec_sab not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_sab != ""
        tem_dom = tec_dom not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_dom != ""
        
        tem_sobreaviso_real = tem_sab or tec_dom # corrigido para checar ambos

        # Formato Sim/Não para a matriz
        sim_nao_sab = "Sim" if tem_sab else "Não"
        sim_nao_dom = "Sim" if tem_dom else "Não"

        dados_consolidados[cidade] = {
            "filial": filial,
            "cidade": cidade,
            "status": "SIM" if tem_sobreaviso_real else "NÃO",
            "tecnico_sabado": tec_sab,
            "jornada_sabado": jor_sab,
            "tecnico_domingo": tec_dom,
            "jornada_domingo": jor_dom,
            "tem_tecnico_real": tem_sobreaviso_real,
            "resumo_sabado": sim_nao_sab,
            "resumo_domingo": sim_nao_dom
        }

    return dados_consolidados


# ============================================================
# ROTAS FLASK
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status-sheets", methods=["GET"])
def status_sheets():
    res_agendamentos = ler_csv_online(URL_AGENDAMENTOS)
    res_sabado = ler_csv_online(URL_PLANTAO_SABADO)
    res_domingo = ler_csv_online(URL_PLANTAO_DOMINGO)
    return jsonify({
        "sucesso": True,
        "google_sheets": {
            "agendamentos": res_agendamentos is not None,
            "plantao": (res_sabado is not None and res_domingo is not None)
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

        if tipo == "agendamento":
            linhas = ler_csv_online(URL_AGENDAMENTOS)
            if not linhas:
                return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets de Agendamentos."}), 500

            termo_normalizado = normalizar_texto(termo)
            tabela_mapa = str.maketrans("áàãâäéèêëíìîïóòõôöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
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

            resultados = [cidades_map[cidade] for cidade in cidades_encontradas if cidade in cidades_map]
            return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

        else:
            # Busca Plantão / Sobreaviso nas abas separadas por dia
            dados_plantao = processar_dados_plantao()

            if termo_normalizado == "todas_as_cidades":
                resultados = list(dados_plantao.values())
                # Formata para o resumo geral da matriz
                resultados_formatados = [{
                    "filial": item["filial"],
                    "cidade": item["cidade"],
                    "tecnico_sabado": item["resumo_sabado"],
                    "tecnico_domingo": item["resumo_domingo"]
                } for item in resultados]
                return jsonify({"sucesso": True, "total": len(resultados_formatados), "dados": resultados_formatados})

            cidades_disponiveis = list(dados_plantao.keys())
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

            resultados = []
            for cidade, info in dados_plantao.items():
                if cidades_encontradas and cidade in cidades_encontradas:
                    resultados.append(info)
                elif filiais_encontradas and info["filial"] in filiais_encontradas and info["tem_tecnico_real"]:
                    resultados.append(info)

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
