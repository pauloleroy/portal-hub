import psycopg2
import re
from dotenv import load_dotenv
import os
from typing import Dict, Any, List

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

def normalize_cnpj(cnpj: str) -> str | None:
    """Função helper para remover caracteres não numéricos do CNPJ."""
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", cnpj)
    return digits if len(digits) == 14 else None

class DatabaseService:
    """
    Classe base para gerenciar a conexão com o banco de dados.
    """
    
    def __init__(self):
        self.config = DB_CONFIG 

    def _get_connection(self):
        """Retorna uma nova conexão psycopg2."""
        return psycopg2.connect(**self.config)

    def _execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, commit: bool = False) -> Any | str | None:
        """
        Método de utilidade para executar qualquer query.
        Centraliza o tratamento de conexão, cursor e erros.

        :param query: A string SQL.
        :param params: Parâmetros para a query (para segurança contra SQL injection).
        :param fetch_one: Se True, retorna a primeira linha (para SELECTs).
        :param commit: Se True, executa conn.commit() (para INSERT, UPDATE, DELETE).
        :return: Resultados da query, string de erro, ou None.
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(query, params)
                
                if commit:
                    conn.commit()
                    return None # Retorna None em sucesso de escrita
                
                # Operações de leitura (SELECT)
                if fetch_one:
                    return cur.fetchone()
                else:
                    return cur.fetchall()
                    
        except Exception as e:
            if conn and commit:
                conn.rollback() # Reverte transação em caso de erro de escrita
            print(f"❌ Erro de BD: {e}") 
            
            return str(e)
            
        finally:
            if conn:
                conn.close()