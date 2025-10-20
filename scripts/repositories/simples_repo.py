from typing import Dict, Any, List, Union, Tuple
from decimal import Decimal
from ..conexao_db import DatabaseService
import json

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
    
    def pegar_dados_mes(self, empresa_id: int, mes_ref: str) -> Union[Dict[str, Any], str, None]:
        query = """
            SELECT aliquota_efetiva, anexo,  rbt12, retencoes, faturamento_mensal, valor_estimado_guia, impostos, id, valor_guia_oficial
            FROM simples_apuracoes
            WHERE empresa_id = %s AND competencia = %s;
            """
        resultado: Union[Tuple, str, None] = self._db._execute_query(query, (empresa_id, mes_ref), fetch_one=True)
        
        # Se for string, é um ERRO do DB. Repassamos o erro.
        if isinstance(resultado, str):
            return resultado
        
        if not resultado:
            return None
        
        impostos_brutos = resultado[6]
        # Se o campo JSONB for NULL ou vazio (o que é improvável se foi inserido corretamente), tratamos aqui.
        if not impostos_brutos:
            impostos_convertidos = {}
        elif isinstance(impostos_brutos, str):
            # Fallback: Se por acaso o driver não converter e vier como string, rodamos o json.loads
            impostos_convertidos = json.loads(impostos_brutos)
        else:
            # CASO NORMAL: O driver (psycopg2) já converteu o JSONB para dict Python
            impostos_convertidos = impostos_brutos

        impostos_finais = {
            chave: Decimal(valor)
            for chave, valor in impostos_convertidos.items()
        }

        return {
            'aliquota_efetiva': resultado[0], 
            'anexo': resultado[1],
            'rbt12': resultado[2],
            'retencoes': resultado[3] or Decimal('0'),
            'faturamento_mensal': resultado[4] or Decimal('0'),
            'valor_estimado_guia': resultado[5] or Decimal('0'),
            'impostos': impostos_finais,
            'id' : resultado[7],
            'valor_guia_oficial' : resultado[8] or Decimal('0')
        }
    
    def pegar_guia(self, empresa_id: int, mes_ref: str) -> Decimal | str |None:
        """Busca valor da guia apurado"""
        query = """
            SELECT valor_estimado_guia 
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
    
    def inserir_valor_guia(self, simples_id: int, valor_guia_oficial: Decimal) -> Union[None, str]:
            """
            Insere o valor oficial da guia na tabela e calcula a diferença.
            Retorna: None (sucesso) ou str (erro do DB).
            """
            
            # Query simplificada: Apenas UPDATE e cálculo.
            query = """
            UPDATE simples_apuracoes
            SET 
                valor_guia_oficial = %s,
                diferenca = %s - valor_estimado_guia 
            WHERE id = %s;
            """
            
            # Os argumentos continuam os mesmos
            args = (valor_guia_oficial, valor_guia_oficial, simples_id)
            
            # Executa a query
            # 💡 fetch_one=False (ou omita, pois não há RETURNING)
            # 💡 commit=True para garantir que o UPDATE seja salvo no DB
            retorno: Union[str, None] = self._db._execute_query(
                query, 
                args, 
                fetch_one=False, # Não precisamos de retorno de dados
                commit=True      # ESSENCIAL: Garante que o UPDATE seja permanente
            )
            
            if isinstance(retorno, str):
                # Retorna string de erro do DB
                return retorno
                
            # Sucesso: Se não houve erro (string), retornamos None
            return None