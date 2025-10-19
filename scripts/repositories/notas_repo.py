from typing import Dict, Any, List, Tuple, Union
from decimal import Decimal
from ..conexao_db import DatabaseService
from datetime import date

class NotasRepository:
    """Lógica de acesso, cálculo e manipulação de Notas Fiscais e Apurações (Simples)."""
    
    def __init__(self, db_service: DatabaseService):
        self._db = db_service

    def somar_notas_periodo(self, empresa_id: int, data_inicial: str, data_final: str) -> Decimal | str:
        """Soma as notas no período, distinguindo entrada (+) e saída (-). Retorna Decimal com 2 casas de precisão ou str em caso de erro."""
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
        resultados = self._db._execute_query(query, (empresa_id, data_inicial, data_final,), fetch_one=False)
        
        if isinstance(resultados, str):
            return resultados
        
        # Se o resultado for uma lista vazia (sem notas no período)
        if not resultados:
            return Decimal('0.00').quantize(Decimal('0.01'))

        # Convertemos o resultado (tupla de tuplas) para lista de dicionários
        total_por_cfop = [{"cfop": r[0], "total": r[1]} for r in resultados]
        
        # Lógica de negócio (CFOPs) que deve estar no Repositório
        cfops_entrada = {"5102", "5933", "6933", "6102"}
        cfops_saida = {"6202", "5202"}
        
        total = Decimal('0.00') # Inicialização como Decimal para máxima precisão
        for item in total_por_cfop:
            cfop = item["cfop"]
            # Garantimos que 'valor' seja Decimal
            valor = item["total"]
            if not isinstance(valor, Decimal):
                valor = Decimal(str(valor))
                
            if cfop in cfops_entrada:
                total += valor
            elif cfop in cfops_saida:
                total -= valor
                
        # Arredondamento final com duas casas decimais
        return total.quantize(Decimal('0.01'))

    def calcular_iss_periodo(self, empresa_id: int, data_inicial: str, data_final: str) -> Decimal | str:
        """Calcula a soma do valor de ISS das notas não canceladas no período. Retorna Decimal com 2 casas de precisão ou str em caso de erro."""
        query = """
             SELECT SUM(valor_iss)
             FROM notas
             WHERE empresa_id = %s
             AND data_emissao BETWEEN %s AND %s
             AND e_cancelada = FALSE;
             """
        resultado = self._db._execute_query(query, (empresa_id, data_inicial, data_final,), fetch_one=True)
        
        # Se for string, é um ERRO do DB. Repassamos o erro.
        if isinstance(resultado, str):
            return resultado

        # Garante que o valor nulo seja Decimal('0')
        valor_raw = resultado[0] if resultado and resultado[0] is not None else Decimal('0')
        
        # Se não for Decimal (caso raro de driver), converte
        if not isinstance(valor_raw, Decimal):
            valor = Decimal(str(valor_raw))
        else:
            valor = valor_raw
            
        # Arredondamento final
        return valor.quantize(Decimal('0.01'))
    def somar_receitas_por_retencao(self, empresa_id: int, data_inicial: date, data_final: date) -> Union[Dict[str, Decimal], str]:
        """
        Soma o valor total das notas fiscais da empresa no período, 
        separando a receita que teve retenção de ISS daquela que não teve.
        """
        query = """
            SELECT
                SUM(CASE
                    -- Receita COM Retenção: valor_iss é maior que zero
                    WHEN valor_iss IS NOT NULL AND valor_iss > 0 THEN valor_total
                    ELSE 0
                END) AS receita_com_retencao,
                SUM(CASE
                    -- Receita SEM Retenção: valor_iss é nulo ou igual a zero
                    WHEN valor_iss IS NULL OR valor_iss = 0 THEN valor_total
                    ELSE 0
                END) AS receita_sem_retencao
            FROM notas
            WHERE empresa_id = %s
            AND data_emissao BETWEEN %s AND %s;
            """
        
        # Converte as datas para o formato esperado pelo banco de dados
        data_inicial_str = data_inicial.strftime('%Y-%m-%d')
        data_final_str = data_final.strftime('%Y-%m-%d')
        
        # O resultado será (Decimal, Decimal) ou str (erro) ou None
        resultado: Union[Tuple, str, None] = self._db._execute_query(
            query, 
            (empresa_id, data_inicial_str, data_final_str), 
            fetch_one=True
        )
        
        if isinstance(resultado, str):
            return resultado # Erro DB
    
        # Se o SUM retornou NULL (sem notas no período), usamos Decimal('0.00')
        if not resultado:
            receita_com = Decimal('0.00')
            receita_sem = Decimal('0.00')
        else:
            # Garante que, mesmo que o SUM retorne NULL (None no Python), usemos 0
            receita_com = resultado[0] if resultado[0] is not None else Decimal('0.00')
            receita_sem = resultado[1] if resultado[1] is not None else Decimal('0.00')

        return {
            'receita_com_retencao': receita_com,
            'receita_sem_retencao': receita_sem
    }

    def inserir_nota(self, dados: Dict[str, Any], update: bool = False) -> str | None:
        """Insere ou atualiza uma nota fiscal. Retorna str em caso de erro ou None em caso de sucesso."""
        CHAVES_CONFLITO = ['chave', 'id']
        
        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))

        query = f"""
        INSERT INTO notas ({colunas_str})
        VALUES ({placeholders})
        """

        if update:
            colunas_para_update = [col for col in colunas if col not in CHAVES_CONFLITO]
            update_set_clause = ', '.join([f"{col}=EXCLUDED.{col}" for col in colunas_para_update])
            query += f' ON CONFLICT (chave) DO UPDATE SET {update_set_clause};'
        else:
            query += ';'

        return self._db._execute_query(query, valores, commit=True)