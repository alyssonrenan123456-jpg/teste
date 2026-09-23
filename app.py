from flask import Flask, render_template, request, jsonify
import csv
import urllib.request
import io

app = Flask(__name__)

# URLs das planilhas exportadas em formato CSV público do Google Sheets
URL_AGENDAMENTOS = "https://docs.google.com/spreadsheets/d/1ROT8e_gaTmVDr1v-qZngmtTQYeU56uQFVfu65fu0LWs/export?format=csv&gid=0"
URL_PLANTAO = "https://docs.google.com/spreadsheets/d/13Ywxw4AWhx11vzwMWNelPULsEIU32yFoKbLaXmG6BwU/export?format=csv&gid=1389576198"

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
    termo = dados.get('termo', '').strip().lower()
    tipo = dados.get('tipo', 'agendamento') # 'agendamento' ou 'plantao'

    if not termo:
        return jsonify({"sucesso": False, "erro": "Informe um termo para consultar."}), 400

    url = URL_AGENDAMENTOS if tipo == 'agendamento' else URL_PLANTAO
    linhas = ler_csv_online(url)

    if not linhas:
        return jsonify({"sucesso": False, "erro": "Não foi possível conectar ao Google Sheets."}), 500

    resultados = []

    for linha in linhas[1:]:
        if len(linha) > 1:
            if tipo == 'agendamento':
                coluna_cidade = linha[0].strip()
                if termo in coluna_cidade.lower():
                    resultados.append({
                        "cidade": linha[0].strip(),
                        "conectados": linha[1].strip() if len(linha) > 1 else "-",
                        "ttth": linha[2].strip() if len(linha) > 2 else "-",
                        "responsavel": linha[3].strip() if len(linha) > 3 else "Não informado",
                        "regional": linha[4].strip() if len(linha) > 4 else "-"
                    })
            else:
                coluna_filial = linha[0].strip()
                coluna_cidade = linha[1].strip() if len(linha) > 1 else ""
                
                # Coleta técnicos de sábado e domingo
                tec_sabado = linha[14].strip() if len(linha) > 14 else ""
                tec_domingo = linha[16].strip() if len(linha) > 16 else ""

                # Verifica se há técnico escalado (diferente de NENHUMA OPÇÃO, VAZIO ou ' - ')
                tem_tecnico = (
                    tec_sabado and tec_sabado.upper() != "NENHUMA OPÇÃO"
                ) or (
                    tec_domingo and tec_domingo.upper() != "NENHUMA OPÇÃO"
                )

                # Busca tanto por Filial quanto por Cidade
                if termo in coluna_filial.lower() or termo in coluna_cidade.lower():
                    # Exibe somente as cidades que possuem técnico de plantão escalado
                    if tem_tecnico:
                        resultados.append({
                            "filial": coluna_filial,
                            "cidade": coluna_cidade,
                            "status": linha[3].strip() if len(linha) > 3 else "-",
                            "tecnico_sabado": tec_sabado if tec_sabado else "Nenhum",
                            "jornada_sabado": linha[15].strip() if len(linha) > 15 else "-",
                            "tecnico_domingo": tec_domingo if tec_domingo else "Nenhum",
                            "jornada_domingo": linha[17].strip() if len(linha) > 17 else "-"
                        })

    return jsonify({"sucesso": True, "total": len(resultados), "dados": resultados})

if __name__ == '__main__':
    app.run(debug=True)
