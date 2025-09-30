#conexao_db.py
import psycopg2
import re


def _normalize_cnpj(cnpj: str) -> str | None:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    return digits if digits else None

# conexao_db.py
def procurar_empresa_id(conn, cnpj):
    try:
        with conn.cursor() as cur:  # Corrigido: conn.cursor() em vez de conn.cursor
            query = "SELECT id FROM empresas WHERE cnpj = %s"  # Use parâmetros, não f-string
            cur.execute(query, (cnpj,))
            resultado = cur.fetchone()  # Obtenha o resultado
            return resultado[0] if resultado else None
    except Exception as e:
        print(f"Erro ao buscar empresa: {e}")
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


