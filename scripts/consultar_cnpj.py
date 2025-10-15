import requests
from datetime import datetime

API_URL = "https://brasilapi.com.br/api/cnpj/v1/"

def consultar_dados_cnpj(cnpj):
    dados= []
    response = requests.get(API_URL + cnpj)
    if response.status_code == 200:
        data = response.json()
        razao_social = data["razao_social"]
        data_abertura = datetime.strptime(data["data_inicio_atividade"],"%Y-%m-%d")
        optante_simples = data["opcao_pelo_simples"]
        situacao_cadastral = data["descricao_situacao_cadastral"]
        identificador_matriz_filial = data["identificador_matriz_filial"]
        dados.append({
            "razao_social" : razao_social,
            "cnpj": cnpj,
            "data_abertura" : data_abertura,
            "situacao_cadastral": situacao_cadastral,
            "optante_simples": optante_simples,
            "matriz_filial" : identificador_matriz_filial
        })
        return dados
    else:
        print(f"Erro: Requisição retornou status {response.status_code}")
        return None