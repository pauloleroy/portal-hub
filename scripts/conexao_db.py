#conexao_db.py
import psycopg2
import re
from dotenv import load_dotenv
import os
from typing import Dict, Any, List

# Configuração é carregada UMA VEZ ao importar o módulo
load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

def _normalize_cnpj(cnpj: str) -> str | None:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    return digits if digits else None

class DatabaseService:
    
    def __init__(self):
        self.config = DB_CONFIG 

    def _get_connection(self):
        return psycopg2.connect(**self.config)

    def procurar_empresa_id(self, cnpj: str) -> int | None:
        cnpj_norm = _normalize_cnpj(cnpj)
        if not cnpj_norm:
            return None
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:  
                query = "SELECT id FROM empresas WHERE cnpj = %s" 
                cur.execute(query, (cnpj_norm,))
                resultado = cur.fetchone() 
                return resultado[0] if resultado else None
        except Exception as e:
            print(f"❌ Erro ao buscar empresa: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def pegar_empresas(self) -> List[Dict[str, Any]] | None:
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:  
                query = "SELECT id, razao_social, cnpj FROM empresas ORDER BY razao_social ASC" 
                cur.execute(query)
                empresas = [{"id": r[0], "nome": r[1], "cnpj": r[2]} for r in cur.fetchall()]
                return empresas
        except Exception as e:
            print(f"❌ Erro ao buscar empresa: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def somar_notas_periodo(self, empresa_id, data_inicial, data_final):
        conn = None
        try:
            conn = self._get_connection()
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
            print(f"❌ Erro ao buscar dados: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def calcular_iss_periodo(self, empresa_id, data_inicial, data_final):
        conn = None
        try:
            conn = self._get_connection()
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
            print(f"❌ Erro ao buscar dados: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def pegar_data_abertura(self, empresa_id):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = "SELECT data_abertura FROM empresas WHERE id = %s"
                cur.execute(query, (empresa_id,))
                resultado = cur.fetchone()
                return resultado[0]
        except Exception as e:
            print(f"❌ Erro ao buscar dados: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def inserir_aliq(self, dados: Dict[str, Any]):
        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = f"""
                INSERT INTO simples_apuracoes ({colunas_str})
                VALUES ({placeholders});
                """
                cur.execute(query, valores)
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Erro ao buscar dados: {e}")
        finally:
            if conn:
                conn.close()

    def inserir_calc_simples(self, faturamento_mensal, retencoes, valor_estimado_guia, empresa_id, competencia):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = """
                    UPDATE simples_apuracoes
                    SET faturamento_mensal = %s,
                        retencoes = %s,
                        valor_estimado_guia = %s
                    WHERE empresa_id = %s AND competencia = %s;
                    """
                cur.execute(query, (faturamento_mensal, retencoes, valor_estimado_guia, empresa_id, competencia))
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Erro ao buscar dados: {e}")
        finally:
            if conn:
                conn.close()

    def pegar_aliquota_efetiva(self, empresa_id, mes_ref):
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = """
                    SELECT aliquota_efetiva 
                    FROM simples_apuracoes
                    WHERE empresa_id = %s AND competencia = %s;
                    """
                cur.execute(query, (empresa_id, mes_ref))
                resultado = cur.fetchone()
                return resultado[0]
        except Exception as e:
            print(f"❌ Erro ao buscar dados: {e}")
        finally:
            if conn:
                conn.close()

    def cadastrar_empresa_socio(self, tabela, dados):
        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = f"""
                INSERT INTO {tabela} ({colunas_str})
                VALUES ({placeholders});
                """
                cur.execute(query, valores)
                conn.commit()
            return None
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Erro ao buscar dados: {e}")
            return str(e)
        finally:
            if conn:
                conn.close()

    def inserir_nota(self, tabela, dados):
        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))

        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = f"""
                INSERT INTO {tabela} ({colunas_str})
                VALUES ({placeholders})
                ON CONFLICT (chave) DO UPDATE SET
                {', '.join([f"{col}=EXCLUDED.{col}" for col in colunas if col not in ['chave', 'id']])};
                """
                cur.execute(query, valores)
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"❌ Erro ao inserir nota {dados.get('chave')}: {e}")
        finally:
            if conn:
                conn.close()