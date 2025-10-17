from typing import Dict, Any, List
from decimal import Decimal
from ..conexao_db import DatabaseService

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

    def inserir_aliq(self, dados: Dict[str, Any]) -> str | None:
        """Insere uma nova apuração de alíquota no Simples Nacional. Retorna str em caso de erro ou None em caso de sucesso."""
        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))
        
        query = f"""
        INSERT INTO simples_apuracoes ({colunas_str})
        VALUES ({placeholders});
        """
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

    def inserir_nota(self, dados: Dict[str, Any]) -> str | None:
        """Insere ou atualiza uma nota fiscal usando ON CONFLICT (chave). Retorna str em caso de erro ou None em caso de sucesso."""
        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))

        # Cria a string de atualização para ON CONFLICT
        update_set_clause = ', '.join([f"{col}=EXCLUDED.{col}" for col in colunas if col not in ['chave', 'id']])

        query = f"""
        INSERT INTO notas ({colunas_str})
        VALUES ({placeholders})
        ON CONFLICT (chave) DO UPDATE SET
        {update_set_clause};
        """
        return self._db._execute_query(query, valores, commit=True)