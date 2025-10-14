#calcular_simples.py
import psycopg2
import conexao_db
from dotenv import load_dotenv
import os
from datetime import date
from dateutil.relativedelta import relativedelta
import calendar
from tabela_simples import TABELAS_SIMPLES_ANEXOS
from decimal import Decimal
import json

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

def calcular_rbt12 (conn, empresa_id, mes_ref):
    data_abertura = conexao_db.pegar_data_abertura(conn, empresa_id).replace(day=1)
    data_inicial = mes_ref - relativedelta(months=12)
    mes_anterior_ref = mes_ref - relativedelta(months=1)
    ultimo_dia = calendar.monthrange(mes_anterior_ref.year, mes_anterior_ref.month)[1]
    data_final = mes_anterior_ref.replace(day=ultimo_dia)
    if data_abertura > data_inicial:
        diferenca = relativedelta(mes_anterior_ref, data_abertura)
        total_periodo = conexao_db.somar_notas_periodo(conn, empresa_id, data_abertura, data_final)
        total_meses = diferenca.years * 12 + diferenca.months + 1
    else:
        total_periodo = conexao_db.somar_notas_periodo(conn, empresa_id, data_inicial, data_final)
        total_meses = 12
    rbt12 = total_periodo*12/total_meses
    return rbt12

def calcular_iss_retido(conn, empresa_id, mes_ref):
    data_inicial = mes_ref.replace(day=1)
    ultimo_dia = calendar.monthrange(mes_ref.year, mes_ref.month)[1]
    data_final = mes_ref.replace(day=ultimo_dia)
    total_iss = conexao_db.calcular_iss_periodo(conn, empresa_id, data_inicial, data_final)
    return total_iss

def definir_faixa_simples (anexo, rbt12):
    aliq_anexo = TABELAS_SIMPLES_ANEXOS[anexo]
    for faixa in aliq_anexo:
        if rbt12 <= faixa["faixa_max"]:
            return faixa
    return None

def calcular_aliq (faixa, rbt12):
    aliquota_efetiva = (rbt12 * Decimal(str(faixa["aliquota"])) - Decimal(str(faixa["deducao"])))/ rbt12
    impostos = {
        chave : Decimal(str(aliq)) * aliquota_efetiva
        for chave, aliq in faixa['impostos'].items()
    }
    return impostos, aliquota_efetiva

def enviar_aliq(conn, empresa_id, competencia, rbt12, anexo, aliquota_efetiva, impostos):
    impostos = json.dumps(impostos, default=lambda x: str(x))
    dados = {
        'empresa_id' : empresa_id,
        'competencia' : competencia,
        'rbt12' : rbt12,
        'anexo' : anexo,
        'aliquota_efetiva' : aliquota_efetiva,
        'impostos' : impostos
    }
    conexao_db.inserir_aliq(conn, dados)


CNPJ = "37.851.556/0001-00"
MES_REF = date(2025, 8, 1)
ANEXO = 'Anexo III'

if __name__ == "__main__":
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        empresa_id = conexao_db.procurar_empresa_id(conn ,CNPJ)
        rbt12 = calcular_rbt12(conn, empresa_id, MES_REF)
        faixa = definir_faixa_simples(ANEXO, rbt12)
        impostos, aliquota_efetiva = calcular_aliq(faixa, rbt12)
        print(calcular_iss_retido(conn, empresa_id, date(2025, 8, 1)))
        enviar_aliq(conn, empresa_id, MES_REF, rbt12, ANEXO, aliquota_efetiva, impostos)
    except Exception as e:
        print(f"Erro na conexão: {e}")
    finally:
        if 'conn' in locals() and conn:
                conn.close()
    