#conexao_db.py
import psycopg2
import re


def _normalize_cnpj(cnpj: str) -> str | None:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    return digits if digits else None


def procurar_empresa_id(conn, cnpj):
    try:
        with conn.cursor() as cur:  
            query = "SELECT id FROM empresas WHERE cnpj = %s" 
            cur.execute(query, (cnpj,))
            resultado = cur.fetchone() 
            return resultado[0] if resultado else None
    except Exception as e:
        print(f"Erro ao buscar empresa: {e}")
        return None

def somar_notas_periodo (conn, empresa_id, data_inicial, data_final):
    try:
        with conn.cursor() as cur:
            query = """
                        SELECT 
                            cfop,
                            COALESCE(SUM(valor_total), 0) AS total
                        FROM notas
                        WHERE empresa_id = %s
                        AND data_emissao BETWEEN %s AND %s
                        AND e_cancelada = FALSE
                        GROUP BY cfop
                        ORDER BY cfop NULLS LAST
                    """
            cur.execute(query, (empresa_id, data_inicial, data_final,))
            resultados = cur.fetchall()
            total_por_cfop = [{"cfop": cfop, "total": total} for cfop, total in resultados]
            cfops_entrada = {"5102", "5933", "6933", "6102"}
            cfops_saida = {"6202", "5202"}
            total = 0
            for item in total_por_cfop:
                cfop = item["cfop"]
                valor = item["total"]
                if cfop in cfops_entrada:
                    total += valor
                elif cfop in cfops_saida:
                    total -= valor
            return total
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return None

def calcular_iss_periodo(conn, empresa_id, data_inicial, data_final):
    try:
        with conn.cursor() as cur:
            query = """
                    SELECT SUM(valor_iss)
                    FROM notas
                    WHERE empresa_id = %s
                    AND data_emissao BETWEEN %s AND %s
                    AND e_cancelada = FALSE;
                """
            cur.execute(query, (empresa_id, data_inicial, data_final,))
            resultado = cur.fetchone()
            return resultado [0]
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return None

def pegar_data_abertura(conn, empresa_id):
    try:
        with conn.cursor() as cur:
            query = "SELECT data_abertura FROM empresas WHERE id = %s"
            cur.execute(query, (empresa_id,))
            resultado = cur.fetchone()
            return resultado[0]
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return None

def inserir_dict (conn, tabela, dados):
    colunas = list(dados.keys())
    valores = list(dados.values())

    colunas_str = ", ".join(colunas)
    placeholders = ", ".join(["%s"] * len(valores))

    try:
        with conn.cursor() as cur:
            query = f"""
            INSERT INTO {tabela} ({colunas_str})
            VALUES ({placeholders})
            ON CONFLICT (chave) DO UPDATE SET
            {', '.join([f"{col}=EXCLUDED.{col}" for col in colunas if col != 'chave'])};
            """
            cur.execute(query, valores)
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao inserir nota {dados.get('chave')}: {e}")


