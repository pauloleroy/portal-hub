from typing import List, Dict, Any
from ..conexao_db import DatabaseService, normalize_cnpj 

class EmpresaRepository:
    """Lógica de acesso e manipulação de dados de Empresas e Sócios."""
    
    def __init__(self, db_service: DatabaseService):
        self._db = db_service # Injeção de dependência da classe base

    def procurar_empresa_id(self, cnpj: str) -> int | None:
        """Busca o ID de uma empresa pelo CNPJ normalizado."""
        cnpj_norm = normalize_cnpj(cnpj)
        if not cnpj_norm:
            return None
        
        query = "SELECT id FROM empresas WHERE cnpj = %s" 
        resultado = self._db._execute_query(query, (cnpj_norm,), fetch_one=True)
        
        return resultado[0] if resultado else None

    def pegar_empresas(self) -> List[Dict[str, Any]] | None:
        """Retorna a lista de todas as empresas cadastradas."""
        query = "SELECT id, razao_social, cnpj FROM empresas ORDER BY razao_social ASC" 
        resultados = self._db._execute_query(query, fetch_one=False)
        
        # Verifica se houve erro de execução (retorna string) ou se está vazio (retorna tupla vazia)
        if isinstance(resultados, str) or resultados is None:
            return None
            
        return [{"id": r[0], "nome": r[1], "cnpj": r[2]} for r in resultados]
        
    def pegar_data_abertura(self, empresa_id) -> Any | None:
        """Retorna a data de abertura de uma empresa pelo ID."""
        query = "SELECT data_abertura FROM empresas WHERE id = %s"
        resultado = self._db._execute_query(query, (empresa_id,), fetch_one=True)
        return resultado[0] if resultado else None

    def pegar_anexo(self, empresa_id) -> str | None:
        """Retorna anexo da empresa"""
        query = "SELECT detalhes_tributarios FROM empresas WHERE id = %s"
        resultado = self._db._execute_query(query, (empresa_id,), fetch_one=True)
        return resultado[0] if resultado else None

    def cadastrar_empresa_socio(self, tabela: str, dados: Dict[str, Any]) -> str | None:
        """ Insere novos dados em uma tabela (empresas ou socios)."""

        colunas = list(dados.keys())
        valores = list(dados.values())

        colunas_str = ", ".join(colunas)
        placeholders = ", ".join(["%s"] * len(valores))

        query = f"""
        INSERT INTO {tabela} ({colunas_str})
        VALUES ({placeholders});
        """
        # Executa com commit=True. Retorna erro (str) ou None (sucesso).
        return self._db._execute_query(query, valores, commit=True)