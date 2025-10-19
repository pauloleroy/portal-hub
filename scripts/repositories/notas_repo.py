from typing import Dict, Any, List, Tuple, Union
from decimal import Decimal
from ..conexao_db import DatabaseService
from datetime import date

class NotasRepository:
    """Lógica de acesso, cálculo e manipulação de Notas Fiscais e Apurações (Simples)."""
    
    def __init__(self, db_service: DatabaseService):
        self._db = db_service
    
    def _get_where_clause_group(self, empresa_id: int) -> str:
        """Retorna a cláusula WHERE IN (ID do grupo) para PostgreSQL, interpolando o ID."""
        # A interpolação direta (f-string) é usada aqui porque o número de %s muda no método principal
        return f"""
        empresa_id IN (
            WITH MatrizID AS (
                SELECT COALESCE(matriz_id, id) AS id_matriz FROM empresas WHERE id = {empresa_id}
            )
            SELECT id FROM empresas
            WHERE id = (SELECT id_matriz FROM MatrizID)
               OR matriz_id = (SELECT id_matriz FROM MatrizID)
        )
        """
    
    def _seperar_saida_deducao(self, dados: List) -> dict:
        # Convertemos o resultado (lista de tuplas) para lista de dicionários
        total_por_cfop = [{"cfop": r[0], "total": r[1]} for r in dados]
        
        # Lógica de negócio (CFOPs) que deve estar no Repositório
        cfops_saida = {"5102", "5933", "6933", "6102"}
        cfops_devolucao = {"2202", "1202"}

        soma = {
                'Saida' : Decimal(0.00),
                'Devolução' : Decimal (0.00),
                'Outros' : Decimal (0.00)
            }
        
        for item in total_por_cfop:
            cfop = item["cfop"]
            # Garantimos que 'valor' seja Decimal
            valor = item["total"]
            if not isinstance(valor, Decimal):
                valor = Decimal(str(valor))
            
            if cfop in cfops_saida:
                soma["Saida"] += valor
            elif cfop in cfops_devolucao:
                soma["Devolução"] += valor
            else:
                soma["Outros"] += valor

        return soma

    def somar_faturamento_liquido(self, empresa_id: int, data_inicial: str, data_final: str, incluir_grupo: bool = False) -> Decimal | str:
        """
        Soma o faturamento líquido (Saída - Devolução) no período,
        podendo incluir a Matriz e Filiais se 'incluir_grupo' for True.
        """
        
        if incluir_grupo:
            where_empresa = self._get_where_clause_group(empresa_id)
            args = (data_inicial, data_final,) # Sem %s para o ID
        else:
            where_empresa = "empresa_id = %s"
            args = (empresa_id, data_inicial, data_final,) # Com %s para o ID
            
        query = f"""
        SELECT 
            cfop,
            COALESCE(SUM(valor_total), 0) AS total
        FROM notas
        WHERE {where_empresa}
        AND data_emissao BETWEEN %s AND %s
        AND e_cancelada = FALSE
        GROUP BY cfop
        ORDER BY cfop NULLS LAST
        """
        # A query agora é montada via f-string, mas os placeholders de data são seguros (%s)
        resultados = self._db._execute_query(query, args, fetch_one=False)
        
        if isinstance(resultados, str): return resultados
        if not resultados: return Decimal('0.00').quantize(Decimal('0.01'))

        por_cfop = self._seperar_saida_deducao(resultados)
        total = por_cfop['Saida'] - por_cfop['Devolução']
        
        return total.quantize(Decimal('0.01'))
    
    def calcular_iss_periodo(self, empresa_id: int, data_inicial: str, data_final: str, incluir_grupo: bool = False) -> Decimal | str:
        """
        Calcula a soma do valor de ISS das notas, podendo incluir a Matriz e Filiais.
        """
        if incluir_grupo:
            where_empresa = self._get_where_clause_group(empresa_id)
            args = (data_inicial, data_final,)
        else:
            where_empresa = "empresa_id = %s"
            args = (empresa_id, data_inicial, data_final,)
            
        query = f"""
            SELECT COALESCE(SUM(valor_iss), 0)
            FROM notas
            WHERE {where_empresa}
            AND data_emissao BETWEEN %s AND %s
            AND e_cancelada = FALSE;
            """
            
        resultado = self._db._execute_query(query, args, fetch_one=True)
        
        if isinstance(resultado, str): return resultado

        # O COALESCE no SQL já garante que o valor seja 0 se não houver notas
        valor_raw = resultado[0] if resultado and resultado[0] is not None else Decimal('0')
        
        if not isinstance(valor_raw, Decimal):
            valor = Decimal(str(valor_raw))
        else:
            valor = valor_raw
            
        return valor.quantize(Decimal('0.01'))
    
    def somar_receitas_por_retencao(self, empresa_id: int, data_inicial: date, data_final: date, incluir_grupo: bool = False) -> Union[Dict[str, Decimal], str]:
        """
        Soma o valor total das notas fiscais, separando receita com e sem retenção,
        podendo incluir a Matriz e Filiais se 'incluir_grupo' for True.
        """
        
        # 1. Definição do WHERE e Argumentos
        data_inicial_str = data_inicial.strftime('%Y-%m-%d')
        data_final_str = data_final.strftime('%Y-%m-%d')
        
        if incluir_grupo:
            where_empresa = self._get_where_clause_group(empresa_id)
            args = (data_inicial_str, data_final_str,)
        else:
            where_empresa = "empresa_id = %s"
            args = (empresa_id, data_inicial_str, data_final_str,)
        
        # 2. Constrói a Query
        query = f"""
            SELECT
                SUM(CASE WHEN valor_iss IS NOT NULL AND valor_iss > 0 THEN valor_total ELSE 0 END) AS receita_com_retencao,
                SUM(CASE WHEN valor_iss IS NULL OR valor_iss = 0 THEN valor_total ELSE 0 END) AS receita_sem_retencao
            FROM notas
            WHERE {where_empresa}
            AND data_emissao BETWEEN %s AND %s
            AND e_cancelada = FALSE
            AND (tipo = 'nfse_pbh' OR tipo = 'nfse_gov'); -- Garante que apenas NFSe sejam consideradas
            """
            
        # 3. Execução e Tratamento
        resultado: Union[Tuple, str, None] = self._db._execute_query(query, args, fetch_one=True)
        
        if isinstance(resultado, str): return resultado
    
        receita_com = resultado[0] if resultado and resultado[0] is not None else Decimal('0.00')
        receita_sem = resultado[1] if resultado and resultado[1] is not None else Decimal('0.00')

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