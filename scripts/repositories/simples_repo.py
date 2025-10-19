from typing import Dict, Any, List
from decimal import Decimal
from ..conexao_db import DatabaseService

class SimplesRepository:
    """Lógica de acesso e manipulação de dados de Empresas e Sócios."""

    def __init__(self, db_service : DatabaseService):
        self._db = db_service 
    
    def pegar_aliquota_efetiva(self, empresa_id: int, mes_ref: str) -> Decimal | str | None:
        """Busca a alíquota efetiva para uma competência específica. Retorna Decimal, None (se não encontrar) ou str (em caso de erro)."""
        query = """
            SELECT aliquota_efetiva 
            FROM simples_apuracoes
            WHERE empresa_id = %s AND competencia = %s;
            """
        resultado = self._db._execute_query(query, (empresa_id, mes_ref), fetch_one=True)
        
        # Se for string, é um ERRO do DB. Repassamos o erro.
        if isinstance(resultado, str):
            return resultado
            
        # Se a consulta foi bem-sucedida, mas não retornou linhas (resultado é None ou tupla vazia), retorna None
        return resultado[0] if resultado else None

    def inserir_aliq(self, dados: Dict[str, Any], update: bool = False) -> str | None:
        """Insere uma nova apuração de alíquota no Simples Nacional. Retorna str em caso de erro ou None em caso de sucesso."""
        CHAVES_CONFLITO = ['empresa_id', 'competencia', 'id']

        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))
        
        query = f"""
        INSERT INTO simples_apuracoes ({colunas_str})
        VALUES ({placeholders})
        """

        if update:
            # Cria a string de atualização para ON CONFLICT
            colunas_para_update = [col for col in colunas if col not in CHAVES_CONFLITO]
            update_set_clause = ', '.join([f"{col}=EXCLUDED.{col}" for col in colunas_para_update])
            query += f' ON CONFLICT (empresa_id, competencia) DO UPDATE SET {update_set_clause};'
        else:
            query += ';'
        # _execute_query retorna str (Erro) ou None (Sucesso)
        return self._db._execute_query(query, valores, commit=True)

    def inserir_calc_simples(self, faturamento_mensal: Decimal, retencoes: Decimal, valor_estimado_guia: Decimal, empresa_id: int, competencia: str) -> str | None:
        """Atualiza os valores de cálculo do Simples em uma apuração existente. Retorna str em caso de erro ou None em caso de sucesso."""
        query = """
        UPDATE simples_apuracoes
        SET faturamento_mensal = %s,
            retencoes = %s,
            valor_estimado_guia = %s
        WHERE empresa_id = %s AND competencia = %s;
        """
        params = (faturamento_mensal, retencoes, valor_estimado_guia, empresa_id, competencia)
        return self._db._execute_query(query, params, commit=True)