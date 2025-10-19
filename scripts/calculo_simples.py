import psycopg2
from dotenv import load_dotenv
import os
from datetime import date
from dateutil.relativedelta import relativedelta
import calendar
from .tabela_simples import TABELAS_SIMPLES_ANEXOS
from decimal import Decimal
import json
from typing import Optional
from .repositories.empresas_repo import EmpresaRepository 
from .repositories.notas_repo import NotasRepository
from .repositories.simples_repo import SimplesRepository 

class CalculoSimples:
    def __init__(self, mes_ref : date, anexo : str, empresa_id: int, empresa_repo: EmpresaRepository, notas_repo: NotasRepository, simples_repo: SimplesRepository):
        self.empresa_repo = empresa_repo 
        self.notas_repo = notas_repo
        self.simples_repo = simples_repo

        self.mes_ref = mes_ref.replace(day=1)
        ultimo_dia = calendar.monthrange(mes_ref.year, mes_ref.month)[1]
        self.mes_ref_final = mes_ref.replace(day=ultimo_dia)
        self.anexo = anexo
        self.empresa_id = empresa_id
        self.rbt12 = self._calcular_rbt_12()
        self.faixa = self._definir_faixa_simples()
        self.retencoes = self._calcular_retencoes()
        self.faturamento_mensal = self._calcular_faturamento_mensal()

    
    def _calcular_rbt_12(self) -> Decimal:
        data_abertura = self.empresa_repo.pegar_data_abertura(self.empresa_id).replace(day=1)
        if data_abertura > self.mes_ref:
            raise ValueError('Mês de referência anterior à data de abertura da empresa.')
        if data_abertura == self.mes_ref:
            return Decimal(0.00)
        data_inicial_12m = self.mes_ref - relativedelta(months=12)
        mes_anterior_ref = self.mes_ref - relativedelta(months=1)
        ultimo_dia = calendar.monthrange(mes_anterior_ref.year, mes_anterior_ref.month)[1]
        data_final = mes_anterior_ref.replace(day=ultimo_dia)
        data_inicio_real = max(data_abertura, data_inicial_12m)
        if data_abertura > data_inicial_12m:
            total_meses = (mes_anterior_ref.year - data_abertura.year) * 12 + (mes_anterior_ref.month - data_abertura.month) + 1
            total_periodo = self.notas_repo.somar_notas_periodo(self.empresa_id, data_inicio_real, data_final)
        else:
            total_periodo = self.notas_repo.somar_notas_periodo(self.empresa_id, data_inicio_real, data_final)
            total_meses = 12
        rbt12 = total_periodo*12/total_meses
        return rbt12

    def _definir_faixa_simples (self) -> dict:
        aliq_anexo = TABELAS_SIMPLES_ANEXOS[self.anexo]
        for faixa in aliq_anexo:
            if self.rbt12 <= faixa["faixa_max"]:
                return faixa
        raise ValueError(f'RBT12 (R$ {self.rbt12:.2f}) excedeu o limite máximo do Simples Nacional para o Anexo {self.anexo}.')
    
    def _calcular_aliq(self) -> Decimal:
        if self.rbt12 == Decimal(0):
            aliquota_efetiva = Decimal(self.faixa["aliquota"])
            return aliquota_efetiva.quantize(Decimal('0.00000000'))
        aliquota_efetiva = (self.rbt12 * Decimal(str(self.faixa["aliquota"])) - Decimal(str(self.faixa["deducao"])))/ self.rbt12
        return aliquota_efetiva.quantize(Decimal('0.00000000'))

    def _calcular_cada_imposto(self, aliquota_efetiva : Decimal) -> dict:
        impostos = {
            chave : (Decimal(str(aliq)) * aliquota_efetiva).quantize(Decimal('0.00000000'))
            for chave, aliq in self.faixa['impostos'].items()
        }
        return impostos
    
    def _calcular_faturamento_mensal(self) -> Decimal:
        faturamento_mensal = self.notas_repo.somar_notas_periodo(self.empresa_id, self.mes_ref, self.mes_ref_final)
        return faturamento_mensal.quantize(Decimal('0.00'))

    def _calcular_retencoes(self) -> Decimal:
        total_retencoes = self.notas_repo.calcular_iss_periodo(self.empresa_id, self.mes_ref, self.mes_ref_final)
        return total_retencoes.quantize(Decimal('0.00'))

    def pegar_aliq(self) -> Decimal | str:
        aliquota_db = self.simples_repo.pegar_aliquota_efetiva(self.empresa_id, self.mes_ref.strftime('%Y-%m-%d'))
        if isinstance(aliquota_db, str):
        # É uma string de erro do DB
            return f"ERRO DB ao buscar alíquota: {aliquota_db}"
        
        if aliquota_db is None:
            # Alíquota não encontrada - Regra de negócio: Apuração deve ser rodada primeiro.
            return f"ERRO: Alíquota Efetiva para {self.mes_ref.strftime('%Y-%m')} não encontrada. Rode a apuração (enviar_aliq) primeiro."
        
        return Decimal(aliquota_db) if not isinstance(aliquota_db, Decimal) else aliquota_db

    def pegar_guia(self):
        valor_guia_estimado = self.simples_repo.pegar_guia(self.empresa_id, self.mes_ref.strftime('%Y-%m-%d'))
        if isinstance(valor_guia_estimado, str):
            return f"ERRO DB ao buscar Valor Guia: {valor_guia_estimado}"
        
        if valor_guia_estimado is None:
            return f"ERRO: Valor Guia Estimado para {self.mes_ref.strftime('%Y-%m')} não encontrada. Rode a apuração (calcular_guia) primeiro."

        return Decimal(valor_guia_estimado) if not isinstance(valor_guia_estimado, Decimal) else valor_guia_estimado
    
    def enviar_aliq(self) -> str | None:
        aliquota_efetiva = self._calcular_aliq()
        impostos = self._calcular_cada_imposto(aliquota_efetiva)
        dados_impostos = json.dumps(impostos, default=lambda x: str(x))
        dados = {
            'empresa_id' : self.empresa_id,
            'competencia' : self.mes_ref,
            'rbt12' : self.rbt12,
            'anexo' : self.anexo,
            'aliquota_efetiva' : aliquota_efetiva,
            'impostos' : dados_impostos
        }
        retorno = self.simples_repo.inserir_aliq(dados)
        return retorno
    
    def calcular_guia(self) -> str | None:
        resultado_aliq = self.pegar_aliq()
        if isinstance(resultado_aliq, str):
            return resultado_aliq
        aliquota_efetiva = resultado_aliq
        valor_imposto = self.faturamento_mensal * aliquota_efetiva
        valor_retencao = self.retencoes or Decimal('0')
        valor_guia =valor_imposto - valor_retencao
        retorno = self.simples_repo.inserir_calc_simples(self.faturamento_mensal, valor_retencao, valor_guia, self.empresa_id, self.mes_ref)
        return retorno