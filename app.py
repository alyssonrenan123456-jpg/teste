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
        # Mapeamento dinâmico de cidades ignorando linhas de título ou em branco
        cidades_map = {}
        
        for linha in linhas:
            if len(linha) >= 4:
                col_0 = linha[0].strip()
                # Verifica se não é o cabeçalho "CIDADE" ou linha vazia
                if col_0 and col_0.upper() != "CIDADE":
                    cidades_map[col_0] = {
                        "cidade": col_0,
                        "conectados": linha[1].strip() if len(linha) > 1 else "-",
                        "ttth": linha[2].strip() if len(linha) > 2 else "-",
                        "responsavel": linha[3].strip() if len(linha) > 3 else "Não informado",
                        "regional": linha[4].strip() if len(linha) > 4 else "-"
                    }

        cidades_disponiveis = list(cidades_map.keys())
        
        # 1. Busca exata ou parcial (sub-string)
        cidades_encontradas = [c for c in cidades_disponiveis if termo_lower in c.lower()]
        
        # 2. Se não encontrou por sub-string, usa busca inteligente (fuzzy) para erros de digitação
        if not cidades_encontradas and cidades_disponiveis:
            match = process.extractOne(termo, cidades_disponiveis, scorer=fuzz.WRatio)
            if match and match[1] >= 60: # Aceita erros leves de digitação
                cidades_encontradas = [match[0]]

        if not cidades_encontradas:
            return jsonify({"sucesso": True, "total": 0, "mensagem": "Cidade não encontrada", "dados": []})

        for c in cidades_encontradas:
            resultados.append(cidades_map[c])

    else:
        # LÓGICA DE PLANTÃO MANTIDA INTACTA
        filiais_disponiveis = list(set([linha[0].strip() for linha in linhas if len(linha) > 0 and linha[0].strip() and linha[0].strip().upper() != "FILIAL"]))
        cidades_disponiveis = list(set([linha[1].strip() for linha in linhas if len(linha) > 1 and linha[1].strip() and linha[1].strip().upper() != "CIDADE"]))

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
