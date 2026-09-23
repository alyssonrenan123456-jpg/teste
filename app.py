from flask import Flask, render_template, request, jsonify
import csv
import urllib.request
import io

app = Flask(__name__)

# URLs de exportação direta CSV configuradas com os seus IDs e GIDs das planilhas
URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"

def ler_csv_online(url):
    """Baixa o conteúdo atualizado da planilha diretamente do Google Sheets"""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            conteudo = response.read().decode('utf-8')
            return list(csv.reader(io.StringIO(conteudo)))
    except Exception as e:
        print(f"Erro ao acessar planilha: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/buscar', methods=['POST'])
def buscar():
    dados = request.json or {}
    termo = dados.get('termo', '').strip().lower()
    tipo = dados.get('tipo', 'agendamento') # 'agendamento' ou 'plantao'

    if not termo:
        return jsonify({"sucesso": False, "erro": "Informe uma cidade para consultar."}), 400

    url = URL_AGENDAMENTOS if tipo == 'agendamento' else URL_PLANTAO
    linhas = ler_csv_online(url)

    if not linhas:
        return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets. Verifique a permissão do link."}), 500

    resultados = []

    # Procura pela cidade no arquivo
    for linha in linhas[1:]:
        if len(linha) > 1:
            # Na planilha de agendamento a cidade fica na coluna 0 ou 1, na de sobreaviso fica na coluna 1
            coluna_cidade = linha[0].strip() if tipo == 'agendamento' else (linha[1].strip() if len(linha) > 1 else "")
            
            if termo in coluna_cidade.lower():
                if tipo == 'agendamento':
                    resultados.append({
                        "cidade": linha[0].strip(),
                        "conectados": linha[1].strip() if len(linha) > 1 else "-",
                        "ttth": linha[2].strip() if len(linha) > 2 else "-",
                        "responsavel": linha[3].strip() if len(linha) > 3 else "Não informado",
                        "regional": linha[4].strip() if len(linha) > 4 else "-"
                    })
                else:
                    # Estrutura para plantão / sobreaviso
                    resultados.append({
                        "filial": linha[0].strip() if len(linha) > 0 else "-",
                        "cidade": linha[1].strip() if len(linha) > 1 else "-",
                        "status": linha[3].strip() if len(linha) > 3 else "-",
                        "tecnico_sabado": linha[14].strip() if len(linha) > 14 else "NENHUMA OPÇÃO",
                        "jornada_sabado": linha[15].strip() if len(linha) > 15 else "-",
                        "tecnico_domingo": linha[16].strip() if len(linha) > 16 else "NENHUMA OPÇÃO",
                        "jornada_domingo": linha[17].strip() if len(linha) > 17 else "-"
                    })

    return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

if __name__ == '__main__':
    app.run(debug=True)