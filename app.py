from flask import Flask, render_template, request, jsonify
import csv
import urllib.request
import io
from rapidfuzz import process, fuzz

app = Flask(__name__)

URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"

def ler_csv_online(url):
    """Baixa o arquivo CSV em tempo real do Google Drive"""
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
        # Mapeia todas as cidades disponíveis para a busca por similaridade
        cidades_disponiveis = [linha[0].strip() for linha in linhas[1:] if len(linha) > 0 and linha[0].strip()]
        
        # Tenta busca exata / parcial primeiro
        cidades_encontradas = [c for c in cidades_disponiveis if termo_lower in c.lower()]
        
        # Se não achou exato, usa busca fuzzy para tratar erros de digitação
        if not cidades_encontradas and cidades_disponiveis:
            match = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio)
            if match and match[1] >= 65: # Limiar de similaridade (65%)
                cidades_encontradas = [match[0]]

        if not cidades_encontradas:
            return jsonify({"sucesso": True, "total": 0, "mensagem": "Cidade não encontrada", "dados": []})

        for linha in linhas[1:]:
            if len(linha) > 0 and linha[0].strip() in cidades_encontradas:
                resultados.append({
                    "cidade": linha[0].strip(),
                    "conectados": linha[1].strip() if len(linha) > 1 else "-",
                    "ttth": linha[2].strip() if len(linha) > 2 else "-",
                    "responsavel": linha[3].strip() if len(linha) > 3 else "Não informado",
                    "regional": linha[4].strip() if len(linha) > 4 else "-"
                })

    else:
        # PLANTAO: Identifica se a busca é por Filial ou Cidade
        filiais_disponiveis = list(set([linha[0].strip() for linha in linhas[1:] if len(linha) > 0 and linha[0].strip()]))
        cidades_disponiveis = list(set([linha[1].strip() for linha in linhas[1:] if len(linha) > 1 and linha[1].strip()]))

        # Verifica correspondências exatas/parciais primeiro
        filiais_encontradas = [f for f in filiais_disponiveis if termo_lower in f.lower()]
        cidades_encontradas = [c for c in cidades_disponiveis if termo_lower in c.lower()]

        e_busca_filial = False
        e_busca_cidade = False

        if filiais_encontradas:
            e_busca_filial = True
        elif cidades_encontradas:
            e_busca_cidade = True
        else:
            # Tenta busca fuzzy (tolerância a erro de digitação)
            match_filial = process.extractOne(termo, filiais_disponiveis, scorer=fuzz.WRatio) if filiais_disponiveis else None
            match_cidade = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio) if cidades_disponiveis else None

            score_filial = match_filial[1] if match_filial else 0
            score_cidade = match_cidade[1] if match_cidade else 0

            if score_filial >= 70 and score_filial >= score_cidade:
                filiais_encontradas = [match_filial[0]]
                e_busca_filial = True
            elif score_cidade >= 65:
                cidades_encontradas = [match_cidade[0]]
                e_busca_cidade = True

        if not e_busca_filial and not e_busca_cidade:
            # Identifica se a intenção parecia ser uma filial (Ex: possui números ou código curto)
            is_like_filial = any(char.isdigit() for char in termo) or len(termo) <= 3
            msg = "Filial não encontrada" if is_like_filial else "Cidade não encontrada"
            return jsonify({"sucesso": True, "total": 0, "mensagem": msg, "dados": []})

        for linha in linhas[1:]:
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

                # REGRA 1: Se for busca por FILIAL -> mostra APENAS cidades que tem técnico de plantão
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

                # REGRA 2: Se for busca por CIDADE -> MOSTRA SEMPRE (mesmo se não tiver ninguém de plantão)
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

if __name__ == '__main__':
    app.run(debug=True)
