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
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/1U7Xx9iENygcdO-Hx7gnihzmQxeJyklUqRMelJ9y5_QE/export?format=csv"


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


# ============================================================
# ROTAS FLASK
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status-sheets", methods=["GET"])
def status_sheets():
    """Rota para verificar o status de conexão com as planilhas."""
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

        # Se tentarem usar a parte de plantão/filial que não funciona
        if tipo == "plantao":
            return jsonify({
                "sucesso": True,
                "total": 0,
                "mensagem": "O criador desistiu de fazer, negócio do diabo nn funciona!!"
            })

        url = URL_AGENDAMENTOS
        linhas = ler_csv_online(url)

        if not linhas:
            return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets na Vercel."}), 500

        termo_normalizado = termo.strip().lower()
        tabela_mapa = str.maketrans("áàãâäéèêëíìîïóòõôöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
        termo_normalizado = " ".join(termo_normalizado.translate(tabela_mapa).split())

        resultados = []
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

        return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"sucesso": False, "erro": str(e)}), 500


application = app

if __name__ == "__main__":
    app.run(debug=True)
