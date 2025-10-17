#funcoes_notas.py
import xml.etree.ElementTree as ET
from .notas_parsers import extrair_dados_pbh, extrair_dados_nfce, extrair_dados_nfe
from .repositories.empresas_repo import EmpresaRepository 
from .repositories.notas_repo import NotasRepository 


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
        elif self.tipo == 'nfe':
            return extrair_dados_nfe(self.root, self.namespace, self.xml_texto)
        else:
            return {}
        
    def _checar_cnpj(self, cnpj : str):
        return cnpj == self.dados.get('prestador_doc') or cnpj == self.dados.get('tomador_doc')
    
    def enviar_nota_db(self, 
                      cnpj: str, 
                      empresa_repo: EmpresaRepository, 
                      notas_repo: NotasRepository) -> str | None:
        
        if not self._checar_cnpj(cnpj):
            return f"Nota {self.dados.get('numero')} não pertence ao CNPJ {cnpj}."
        
        empresa_id_resultado = empresa_repo.procurar_empresa_id(cnpj=cnpj)
        
        if isinstance(empresa_id_resultado, str):
            # Houve um ERRO de banco de dados na consulta (ex: erro de conexão/sintaxe)
            print(f"❌ Erro ao buscar empresa: {empresa_id_resultado}")
            return f"Falha no BD ao buscar CNPJ: {empresa_id_resultado}"
        
        empresa_id = empresa_id_resultado
        
        if not empresa_id:
            print(f"❌ Empresa com CNPJ {cnpj} não cadastrada. Nota {self.dados.get('chave')} ignorada.")
            return f"Empresa {cnpj} não cadastrada. Não é possível inserir a nota."

        dados_para_db = self.dados.copy() 
        dados_para_db['empresa_id'] = empresa_id
        
        retorno_insercao = notas_repo.inserir_nota(dados=dados_para_db) 
        
        if isinstance(retorno_insercao, str):
            # Houve um ERRO de BD durante o INSERT/UPDATE
            print(f"❌ Erro ao inserir nota: {retorno_insercao}")
            return f"Falha ao inserir nota no BD: {retorno_insercao}"
            
        print(f"✅ Nota {self.dados.get('chave')} inserida/atualizada para empresa ID {empresa_id}")
        return None 