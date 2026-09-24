from flask import Flask, render_template, request, jsonify
import csv
import urllib.request
import io
from rapidfuzz import process, fuzz

app = Flask(__name__)

# URLs de exportação direta em CSV das duas planilhas do Google Sheets
URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/1yOw71rZ_ex3hOCTCGSEHGMfoqlB2RrG6zbBDCkPKQyA/edit?hl=pt-br&gid=0#gid=0"

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/buscar', methods=['POST'])
def buscar():
    dados = request.json or {}
    termo = dados.get('termo', '').strip()
    tipo = dados.get('tipo', 'agendamento') # 'agendamento' ou 'plantao'

    if not termo:
        return jsonify({"sucesso": False, "erro": "Informe um termo para consultar."}), 400

    url = URL_AGENDAMENTOS if tipo == 'agendamento' else URL_PLANTAO
    linhas = ler_csv_online(url)

    if not linhas:
        return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets."}), 500

    termo_lower = termo.lower()
    resultados = []

    if tipo == 'agendamento':
        cidades_map = {}
        for linha in linhas:
            # Varre as colunas tratando o deslocamento característico da planilha de agendamento
            for idx, col_val in enumerate(linha):
                nome_col = col_val.strip()
                # Localiza onde está o nome da cidade válido (descartando cabeçalho 'CIDADE', traços ou vazios)
                if nome_col and nome_col.upper() not in ["CIDADE", ":-:", "RESPONSÁVEL", "TOTAL CONECTADOS", "|"]:
                    # Garante que a linha possui colunas suficientes
                    cidade_nome = nome_col
                    # Se a cidade foi encontrada na coluna idx, extrai as colunas seguintes
                    if idx + 3 < len(linha):
                        conectados = linha[idx + 1].strip() if idx + 1 < len(linha) else "-"
                        ttth = linha[idx + 2].strip() if idx + 2 < len(linha) else "-"
                        responsavel = linha[idx + 3].strip() if idx + 3 < len(linha) else "Não informado"
                        regional = linha[idx + 4].strip() if idx + 4 < len(linha) else "-"
                        
                        # Evita salvar entradas inválidas
                        if responsavel.upper() != "RESPONŚAVEL" and responsavel.upper() != "RESPONSÁVEL":
                            cidades_map[cidade_nome] = {
                                "cidade": cidade_nome,
                                "conectados": conectados,
                                "ttth": ttth,
                                "responsavel": responsavel,
                                "regional": regional
                            }
                    break

        cidades_disponiveis = list(cidades_map.keys())
        
        # 1. Busca por palavra contida
        cidades_encontradas = [c for c in cidades_disponiveis if termo_lower in c.lower()]
        
        # 2. Se não encontrou de primeira, usa tolerância a erro de digitação
        if not cidades_encontradas and cidades_disponiveis:
            match = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio)
            if match and match[1] >= 60:
                cidades_encontradas = [match[0]]

        if not cidades_encontradas:
            return jsonify({"sucesso": True, "total": 0, "mensagem": "Cidade não encontrada", "dados": []})

        for c in cidades_encontradas:
            resultados.append(cidades_map[c])

    else:
        # LÓGICA DE PLANTÃO (INALTERADA E FUNCIONAL)
        filiais_disponiveis = list(set([linha[0].strip() for linha in linhas if len(linha) > 0 and linha[0].strip() and linha[0].strip().upper() not in ["FILIAL", ":-:"]]))
        cidades_disponiveis = list(set([linha[1].strip() for linha in linhas if len(linha) > 1 and linha[1].strip() and linha[1].strip().upper() not in ["CIDADE", ":-:"]]))

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

            if score_filial >= 70 and score_filial >= score_cidade:
                filiais_encontradas = [match_filial[0]]
                e_busca_filial = True
            elif score_cidade >= 60:
                cidades_encontradas = [match_cidade[0]]
                e_busca_cidade = True

        if not e_busca_filial and not e_busca_cidade:
            is_like_filial = any(char.isdigit() for char in termo) or len(termo) <= 3
            msg = "Filial não encontrada" if is_like_filial else "Cidade não encontrada"
            return jsonify({"sucesso": True, "total": 0, "mensagem": msg, "dados": []})

        for linha in linhas:
            if len(linha) > 1:
                coluna_filial = linha[0].strip()
                coluna_cidade = linha[1].strip()
                
                tec_sabado = linha[14].strip() if len(linha) > 14 else ""
                tec_domingo = linha[16].strip() if len(linha) > 16 else ""

                tem_tecnico = (
                    tec_sabado and tec_sabado.upper() != "NENHUMA OPÇÃO"
                ) or (
                    tec_domingo and tec_domingo.upper() != "NENHUMA OPÇÃO"
                )

                if e_busca_filial and coluna_filial in filiais_encontradas:
                    if tem_tecnico:
                        resultados.append({
                            "filial": coluna_filial,
                            "cidade": coluna_cidade,
                            "status": linha[3].strip() if len(linha) > 3 else "-",
                            "tecnico_sabado": tec_sabado if tec_sabado else "NENHUMA OPÇÃO",
                            "jornada_sabado": linha[15].strip() if len(linha) > 15 else "-",
                            "tecnico_domingo": tec_domingo if tec_domingo else "NENHUMA OPÇÃO",
                            "jornada_domingo": linha[17].strip() if len(linha) > 17 else "-"
                        })

                elif e_busca_cidade and coluna_cidade in cidades_encontradas:
                    resultados.append({
                        "filial": coluna_filial,
                        "cidade": coluna_cidade,
                        "status": linha[3].strip() if len(linha) > 3 else "-",
                        "tecnico_sabado": tec_sabado if (tec_sabado and tec_sabado.upper() != "NENHUMA OPÇÃO") else "Nenhum técnico escalado",
                        "jornada_sabado": linha[15].strip() if len(linha) > 15 and tec_sabado.upper() != "NENHUMA OPÇÃO" else "-",
                        "tecnico_domingo": tec_domingo if (tec_domingo and tec_domingo.upper() != "NENHUMA OPÇÃO") else "Nenhum técnico escalado",
                        "jornada_domingo": linha[17].strip() if len(linha) > 17 and tec_domingo.upper() != "NENHUMA OPÇÃO" else "-"
                    })

    return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

# Exposição obrigatória para o manipulador serverless da Vercel
application = app

if __name__ == '__main__':
    app.run(debug=True)
