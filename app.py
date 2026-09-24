from flask import Flask, render_template, request, jsonify
import csv
import urllib.request
import json
import io
from rapidfuzz import process, fuzz

@@ -13,40 +12,90 @@
# URL definitiva da planilha de Plantão
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"

# URL do Quadro de Avisos (Google Apps Script)
URL_AVISOS = "https://script.google.com/macros/s/AKfycbxuHFEn-ss5KHYHLIoDSXaRuf7Mwa0Dy8Mm20wrnBfy1ZCG2JHBeJ31g_yC-H38qnMQkA/exec"

# Dicionário de siglas exclusivo para o Agendamento
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
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
with urllib.request.urlopen(req, timeout=10) as response:
conteudo = response.read().decode('utf-8')
return list(csv.reader(io.StringIO(conteudo)))
except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        print(f"Erro ao ler CSV do Google Sheets: {e}")
return None

def extrair_dados_plantao_linha(linha):
    """Extrai com segurança os dados de uma linha da planilha de plantão"""
coluna_filial = linha[0].strip() if len(linha) > 0 else ""
coluna_cidade = linha[1].strip() if len(linha) > 1 else ""
status_bruto = linha[3].strip() if len(linha) > 3 else "-"
@@ -71,34 +120,29 @@ def extrair_dados_plantao_linha(linha):
if len(tecnicos_encontrados) > 1:
tec_domingo, jornada_domingo = tecnicos_encontrados[1]

    # Validação rigorosa: Tem técnico real escalado?
tem_tec_sabado = tec_sabado not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_sabado != ""
tem_tec_domingo = tec_domingo not in ["Nenhum técnico escalado", "NENHUMA OPÇÃO", "-"] and tec_domingo != ""
    
    # O sobreaviso só é SIM de verdade se a planilha diz SIM e TEM técnico escalado em pelo menos um dos dias
tem_sobreaviso_real = (status_bruto.upper() == "SIM") and (tem_tec_sabado or tem_tec_domingo)
status_final = "SIM" if tem_sobreaviso_real else "NÃO"

return {
        "filial": coluna_filial, "cidade": coluna_cidade, "status": status_final,
        "tecnico_sabado": tec_sabado, "jornada_sabado": jornada_sabado,
        "tecnico_domingo": tec_domingo, "jornada_domingo": jornada_domingo,
        "filial": coluna_filial,
        "cidade": coluna_cidade,
        "status": status_final,
        "tecnico_sabado": tec_sabado,
        "jornada_sabado": jornada_sabado,
        "tecnico_domingo": tec_domingo,
        "jornada_domingo": jornada_domingo,
"tem_tecnico_real": tem_sobreaviso_real
}

@app.route('/')
def index():
return render_template('index.html')

@app.route('/api/avisos', methods=['GET'])
def buscar_avisos():
    """Busca os dados do quadro de avisos (problemas massivos)"""
    try:
        req = urllib.request.Request(URL_AVISOS, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            dados = json.loads(response.read().decode('utf-8'))
            return jsonify({"sucesso": True, "avisos": dados})
    except Exception as e:
        print(f"Erro ao buscar avisos: {e}")
        return jsonify({"sucesso": False, "avisos": []})

@app.route('/api/buscar', methods=['POST'])
def buscar():
dados = request.json or {}
@@ -117,6 +161,9 @@ def buscar():
termo_lower = termo.lower()
resultados = []

    # ==========================================
    # 1. ABA AGENDAMENTO
    # ==========================================
if tipo == 'agendamento':
cidades_map = {}
for linha in linhas:
@@ -132,8 +179,11 @@ def buscar():

if responsavel.upper() not in ["RESPONŚAVEL", "RESPONSÁVEL"]:
cidades_map[cidade_nome] = {
                                "cidade": cidade_nome, "conectados": conectados,
                                "ttth": ttth, "responsavel": responsavel, "regional": regional
                                "cidade": cidade_nome,
                                "conectados": conectados,
                                "ttth": ttth,
                                "responsavel": responsavel,
                                "regional": regional
}
break

@@ -160,6 +210,9 @@ def buscar():
if c in cidades_map:
resultados.append(cidades_map[c])

    # ==========================================
    # 2. ABA PLANTÃO
    # ==========================================
else:
filiais_disponiveis = []
cidades_disponiveis = []
@@ -176,6 +229,7 @@ def buscar():
filiais_disponiveis = list(set(filiais_disponiveis))
cidades_disponiveis = list(set(cidades_disponiveis))

        # Resumo total (modal) traz absolutamente todas as cidades
if termo_lower == 'todas_as_cidades':
for linha in linhas:
if len(linha) > 1:
@@ -223,9 +277,11 @@ def buscar():
dados_linha = extrair_dados_plantao_linha(linha)

if e_busca_filial:
                    # 1. Regra para Filial: só exibe se pertencer à filial E tiver sobreaviso REAL (com técnico escalado)
if coluna_filial in filiais_encontradas and dados_linha["tem_tecnico_real"]:
resultados.append(dados_linha)
elif e_busca_cidade:
                    # 2. Regra para Cidade Específica: exibe mesmo que não tenha sobreaviso
if coluna_cidade in cidades_encontradas:
resultados.append(dados_linha)
