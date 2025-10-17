#funcoes_notas.py
import xml.etree.ElementTree as ET
from decimal import Decimal
import re
from datetime import datetime
from scripts.identificacao_socios import definir_socio
from datetime import date
from scripts import conexao_db
from .notas_parsers import extrair_dados_pbh, extrair_dados_nfce

#MIGRAR FUNCAO PARA CLASSE - TA AQUI COMO EXEMPLO SO
def tratar_notas(conteudo):
    root = ET.fromstring(conteudo)
    nota = extrair_dados_pbh(root)
    # Buscar empresa_id dinamicamente
    cnpj_prestador = nota.get('prestador_doc')
    if cnpj_prestador:
        empresa_id = conexao_db.procurar_empresa_id(cnpj=cnpj_prestador)
        if empresa_id:
            nota['empresa_id'] = empresa_id
            conexao_db.inserir_nota(tabela="notas", dados=nota)
            print(f"✅ Nota {nota.get('chave')} inserida para empresa ID {empresa_id}")
        else:
            print(f"❌ Empresa com CNPJ {cnpj_prestador} não cadastrada. Nota {nota.get('chave')} ignorada.")
    else:
        print(f"❌ CNPJ do prestador não encontrado na nota {nota.get('chave')}.")

class Nota:
    def __init__(self, caminho: str):
        self.caminho = caminho
        self.root = self._extrair_root()
        
        self.xml_texto = None 
        self.namespace = None 
        self.tipo = None
        self.dados = {}  

        if self.root is not None:
            self.xml_texto = self._extrair_texto()
            self.namespace = self._definir_namespace()
            self.tipo = self._definir_tipo()
            self.dados = self._extrair_dados()
    
    def _extrair_root(self):
        try:
            tree = ET.parse(self.caminho)
            root = tree.getroot()
            return root
        except FileNotFoundError:
            print(f"Erro: O arquivo não foi encontrado em '{self.caminho}'")
            return None
        except ET.ParseError:
            print(f"Erro: Falha ao parsear o XML do arquivo '{self.caminho}'.")
            return None

    def _extrair_texto(self):
        if self.root is None:
            return None    
        xml_texto = ET.tostring(self.root, encoding="utf-8").decode("utf-8")
        return xml_texto
    
    def _definir_namespace(self):
        if self.root is None:
            return None
        try:
           namespace = self.root.tag.split('}')[0].strip('{')
           return namespace
        except ET.ParseError:
            print("Erro: O arquivo XML é inválido ou não pôde ser lido.")
            return None
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
            return None
    
    def _definir_tipo(self):
        if self.namespace is None or self.root is None:
            return None
        
        tipo_nota = None
        ns = {"n": self.namespace}
        if self.namespace == "http://www.portalfiscal.inf.br/nfe":
            tag_mod = self.root.find(".//n:mod", ns)
            if tag_mod is not None:
                modelo = tag_mod.text.strip()
                if modelo == '55':
                    tipo_nota = 'nfe'
                elif modelo == '65':
                    tipo_nota = 'nfce'
                else:
                    print('NF-e/NFC-e modelo não encontrado')
        elif self.namespace == "http://www.abrasf.org.br/nfse.xsd":
            tipo_nota = 'nfse_pbh'
        elif self.namespace == "http://www.sped.fazenda.gov.br/nfse":
            tipo_nota = 'nfse_gov'
        else:
            print(f'NameSpace: {self.namespace} não encontrado')
        return tipo_nota
    
    def _extrair_dados(self) -> dict:
        if self.tipo is None:
            return {}
        
        if self.tipo == 'nfse_pbh':
            return extrair_dados_pbh(self.root, self.namespace, self.xml_texto)
        elif self.tipo == 'nfce':
            return extrair_dados_nfce(self.root, self.namespace, self.xml_texto)
        else:
            return {}