#calcular_simples.py
import psycopg2
import conexao_db
from dotenv import load_dotenv
import os
from datetime import date
from dateutil.relativedelta import relativedelta
import calendar

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

def calcular_rbt12 (conn, cnpj, mes_ref):
    cnpj = conexao_db._normalize_cnpj(cnpj)
    empresa_id = conexao_db.procurar_empresa_id(conn, cnpj)
    data_abertura = conexao_db.pegar_data_abertura(conn, empresa_id).replace(day=1)
    data_inicial = data_abertura - relativedelta(months=11)
    ultimo_dia = calendar.monthrange(mes_ref.year, mes_ref.month)[1]
    data_final = mes_ref.replace(day=ultimo_dia)
    if data_abertura > data_inicial:
        diferenca = relativedelta(mes_ref, data_abertura)
        total_periodo = conexao_db.somar_notas_periodo(conn, empresa_id, data_abertura, data_final)
        total_meses = diferenca.years * 12 + diferenca.months + 1
    else:
        total_periodo = conexao_db.somar_notas_periodo(conn, empresa_id, data_inicial, data_final)
        total_meses = 12
    rbt12 = total_periodo*12/total_meses
    return rbt12

if __name__ == "__main__":
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(calcular_rbt12(conn, "37.851.556/0001-00", date(2025, 9, 1)))
    except Exception as e:
        print(f"Erro na conexão: {e}")
    finally:
        if 'conn' in locals() and conn:
                conn.close()