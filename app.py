from flask import Flask, render_template, request, jsonify
import csv
import urllib.request
import io
from rapidfuzz import process, fuzz

app = Flask(__name__)

# URL da planilha de Agendamentos
URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"

# URL definitiva da planilha de Plantão
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"

# Dicionário de siglas exclusivo para o Agendamento
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
    "itp": "Itapoá"
}

def ler_csv_online(url):
    """Baixa e lê os dados atualizados em tempo real do Google Sheets"""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            conteudo = response.read().decode('utf-8')
            return list(csv.reader(io.StringIO(conteudo)))
    except Exception as e:
        print(f"Erro ao ler CSV do Google Sheets: {e}")
        return None

def extrair_dados_plantao_linha(linha):
    """Extrai com segurança os dados de uma linha da planilha de plantão"""
    coluna_filial = linha[0].strip() if len(linha) > 0 else ""
    coluna_cidade = linha[1].strip() if len(linha) > 1 else ""
    status = linha[3].strip() if len(linha) > 3 else "-"

    tec_sabado = "Nenhum técnico escalado"
    jornada_sabado = "-"
    tec_domingo = "Nenhum técnico escalado"
    jornada_domingo = "-"

    tecnicos_encontrados = []
    for i in range(4, len(linha)):
        val = linha[i].strip()
        val_upper = val.upper()
        if "PRÓPRIOS" in val_upper or "TERCEIRIZADOS" in val_upper:
            jornada = "-"
            if i + 1 < len(linha) and (":" in linha[i+1] or "h" in linha[i+1].lower() or "as" in linha[i+1].lower() or "-" in linha[i+1]):
                jornada = linha[i+1].strip()
            tecnicos_encontrados.append((val, jornada))

    if len(tecnicos_encontrados) > 0:
        tec_sabado, jornada_sabado = tecnicos_encontrados[0]
    if len(tecnicos_encontrados) > 1:
        tec_domingo, jornada_domingo = tecnicos_encontrados[1]

    return {
        "filial": coluna_filial,
        "cidade": coluna_cidade,
        "status": status,
        "tecnico_sabado": tec_sabado,
        "jornada_sabado": jornada_sabado,
        "tecnico_domingo": tec_domingo,
        "jornada_domingo": jornada_domingo
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/buscar', methods=['POST'])
def buscar():
    dados = request.json or {}
    termo = dados.get('termo', '').strip()
    tipo = dados.get('tipo', 'agendamento')

    if not termo:
        return jsonify({"sucesso": False, "erro": "Informe um termo para consultar."}), 400

    url = URL_AGENDAMENTOS if tipo == 'agendamento' else URL_PLANTAO
    linhas = ler_csv_online(url)

    if not linhas:
        return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets."}), 500

    termo_lower = termo.lower()
    resultados = []

    # ==========================================
    # 1. ABA AGENDAMENTO
    # ==========================================
    if tipo == 'agendamento':
        cidades_map = {}
        for linha in linhas:
            for idx, col_val in enumerate(linha):
                nome_col = col_val.strip()
                if nome_col and nome_col.upper() not in ["CIDADE", ":-:", "RESPONSÁVEL", "TOTAL CONECTADOS", "|"]:
                    cidade_nome = nome_col
                    if idx + 3 < len(linha):
                        conectados = linha[idx + 1].strip() if idx + 1 < len(linha) else "-"
                        ttth = linha[idx + 2].strip() if idx + 2 < len(linha) else "-"
                        responsavel = linha[idx + 3].strip() if idx + 3 < len(linha) else "Não informado"
                        regional = linha[idx + 4].strip() if idx + 4 < len(linha) else "-"
                        
                        if responsavel.upper() not in ["RESPONŚAVEL", "RESPONSÁVEL"]:
                            cidades_map[cidade_nome] = {
                                "cidade": cidade_nome,
                                "conectados": conectados,
                                "ttth": ttth,
                                "responsavel": responsavel,
                                "regional": regional
                            }
                    break

        cidades_alvo = []
        if termo_lower in MAPEAMENTO_SIGLAS_AGENDAMENTO:
            cidades_alvo.append(MAPEAMENTO_SIGLAS_AGENDAMENTO[termo_lower])
        else:
            for cidade_oficial in cidades_map.keys():
                if termo_lower in cidade_oficial.lower():
                    cidades_alvo.append(cidade_oficial)

        cidades_disponiveis = list(cidades_map.keys())
        cidades_encontradas = [c for c in cidades_disponiveis if any(alvo.lower() == c.lower() for alvo in cidades_alvo)]

        if not cidades_encontradas and cidades_disponiveis:
            match = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio)
            if match and match[1] >= 75:
                cidades_encontradas = [match[0]]

        if not cidades_encontradas:
            return jsonify({"sucesso": True, "total": 0, "mensagem": "Cidade ou sigla não encontrada no Agendamento", "dados": []})

        for c in cidades_encontradas:
            if c in cidades_map:
                resultados.append(cidades_map[c])

    # ==========================================
    # 2. ABA PLANTÃO
    # ==========================================
    else:
        filiais_disponiveis = []
        cidades_disponiveis = []
        
        for linha in linhas:
            if len(linha) > 1:
                f = linha[0].strip()
                c = linha[1].strip()
                if f and f.upper() not in ["FILIAL", ":-:", "", "SEGUNDA-FEIRA", "TÉCNICO RESPONSÁVEL"]:
                    filiais_disponiveis.append(f)
                if c and c.upper() not in ["CIDADE", ":-:", "", "SEGUNDA-FEIRA", "TÉCNICO RESPONSÁVEL"]:
                    cidades_disponiveis.append(c)

        filiais_disponiveis = list(set(filiais_disponiveis))
        cidades_disponiveis = list(set(cidades_disponiveis))

        # 3. Resumo total (modal) traz absolutamente todas as cidades
        if termo_lower == 'todas_as_cidades':
            for linha in linhas:
                if len(linha) > 1:
                    f = linha[0].strip()
                    c = linha[1].strip()
                    if f and f.upper() not in ["FILIAL", ":-:", "", "SEGUNDA-FEIRA", "TÉCNICO RESPONSÁVEL"]:
                        resultados.append(extrair_dados_plantao_linha(linha))
            return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

        filiais_encontradas = [f for f in filiais_disponiveis if termo_lower in f.lower()]
        cidades_encontradas = [c for c in cidades_disponiveis if termo_lower in c.lower()]

        e_busca_filial = False
        e_busca_cidade = False

        if filiais_encontradas:
            e_busca_filial = True
        elif cidades_encontradas:
            e_busca_cidade = True
        else:
            match_filial = process.extractOne(termo, filiais_disponiveis, scorer=fuzz.WRatio) if filiais_disponiveis else None
            match_cidade = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio) if cidades_disponiveis else None

            score_filial = match_filial[1] if match_filial else 0
            score_cidade = match_cidade[1] if match_cidade else 0

            if score_filial >= 45 and (score_filial >= score_cidade or len(termo) <= 4):
                filiais_encontradas = [match_filial[0]]
                e_busca_filial = True
            elif score_cidade >= 60:
                cidades_encontradas = [match_cidade[0]]
                e_busca_cidade = True

        if not e_busca_filial and not e_busca_cidade:
            return jsonify({"sucesso": True, "total": 0, "mensagem": "Essa filial não possui sobreaviso no momento", "dados": []})

        for linha in linhas:
            if len(linha) > 1:
                coluna_filial = linha[0].strip()
                coluna_cidade = linha[1].strip()
                
                if coluna_filial.upper() in ["FILIAL", ":-:", "", "SEGUNDA-FEIRA", "TÉCNICO RESPONSÁVEL"]:
                    continue

                dados_linha = extrair_dados_plantao_linha(linha)
                tem_sobreaviso = dados_linha["status"].strip().upper() == "SIM"

                if e_busca_filial:
                    # 1. Regra para Filial: só adiciona se a filial bater E tiver sobreaviso (SIM)
                    if coluna_filial in filiais_encontradas and tem_sobreaviso:
                        resultados.append(dados_linha)
                elif e_busca_cidade:
                    # 2. Regra para Cidade Específica: exibe mesmo que não tenha sobreaviso
                    if coluna_cidade in cidades_encontradas:
                        resultados.append(dados_linha)

        if len(resultados) == 0:
            return jsonify({"sucesso": True, "total": 0, "mensagem": "Essa filial não possui sobreaviso no momento", "dados": []})

    return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

application = app

if __name__ == '__main__':
    app.run(debug=True)
