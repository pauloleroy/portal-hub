from decimal import Decimal
import re
from datetime import datetime
from datetime import date
from scripts.identificacao_socios import definir_socio
import xml.etree.ElementTree as ET

#TO-DO
#Implementar logica para identificar notas canceladas NFC-e e NF-e
#Implementar logica para trocar CFOP de se for emit ou dest para 1 e 2 ou 5 e 6
#Avaliar se vou ler todos CFOPs em uma danfe
#Implementar logica extracao nfs_gov


#NFS - Prefeitura BH
def extrair_dados_pbh(root: ET.Element, namespace: str, xml_texto: str) -> dict:
    ns = {"n": namespace}
    try:
        numero = root.find(".//n:Numero", ns).text
        valor_total = Decimal(root.find(".//n:ValorServicos", ns).text)
        data_emissao = root.find(".//n:DataEmissao", ns).text
        data_competencia = root.find(".//n:Competencia", ns).text
        data_emissao = datetime.strptime(data_emissao, '%Y-%m-%dT%H:%M:%S').date()
        data_competencia = datetime.strptime(data_competencia, '%Y-%m-%dT%H:%M:%S').date()
        mes_ref = date(data_emissao.year, data_emissao.month, 1)
        prestador_nome = root.find(".//n:PrestadorServico//n:RazaoSocial",ns).text
        prestador_doc = root.find(".//n:IdentificacaoPrestador/n:Cnpj", ns).text
        tomador_nome = root.find(".//n:TomadorServico/n:RazaoSocial", ns).text
        tomador_doc = root.find(".//n:IdentificacaoTomador/n:CpfCnpj/n:Cnpj", ns)
        if tomador_doc is not None and tomador_doc.text:
            tomador_doc = tomador_doc.text
        else:
            tomador_doc = root.find(".//n:IdentificacaoTomador/n:CpfCnpj/n:Cpf", ns)
            tomador_doc = tomador_doc.text if tomador_doc is not None and tomador_doc.text else None
        tem_iss_retido = root.find(".//n:IssRetido", ns).text
        if tem_iss_retido == "1":
            valor_iss = Decimal(root.find(".//n:ValorIss", ns).text)
        else:
            valor_iss = 0
        outras_info = root.find(".//n:OutrasInformacoes", ns).text
        chave = re.search(r"\d{44}", outras_info)
        chave = chave.group(0) if chave else None
        discriminacao = root.find(".//n:Discriminacao", ns).text
        socio_id = definir_socio(discriminacao, prestador_doc)
        cancelamento = root.find(".//n:NfseCancelamento", ns)
        if cancelamento is not None:
            e_cancelada = True
        else:
            e_cancelada = False
        return {
            'numero' : numero,
            'tipo' : 'nfse_pbh',
            'valor_total' : valor_total,
            'data_emissao' : data_emissao,
            'data_competencia' : data_competencia,
            'mes_ref' : mes_ref,
            'prestador_nome' : prestador_nome,
            'prestador_doc' : prestador_doc,
            'tomador_nome' : tomador_nome,
            'tomador_doc' : tomador_doc,
            'valor_iss' : valor_iss,
            'chave' : chave,
            'socio_id' : socio_id,
            'cfop' : '5933',
            'e_cancelada' : e_cancelada,
            'xml_text' : xml_texto
        }
    except Exception as e:
        print(f"ERRO ao parsear NFSe PBH: {e}")
        return {}

def extrair_dados_nfce(root: ET.Element, namespace: str, xml_texto: str) -> dict:
    ns = {"n": namespace}
    try:
        numero = root.find(".//n:nNF", ns).text
        valor_total = Decimal(root.find(".//n:vNF", ns).text)
        data_emissao = root.find(".//n:dhEmi", ns).text
        data_competencia = root.find(".//n:dhEmi", ns).text
        data_emissao = datetime.strptime(data_emissao, '%Y-%m-%dT%H:%M:%S%z').date()
        data_competencia = datetime.strptime(data_competencia, '%Y-%m-%dT%H:%M:%S%z').date()
        mes_ref = date(data_emissao.year, data_emissao.month, 1)
        prestador_nome = root.find(".//n:emit/n:xNome",ns).text
        prestador_doc = root.find(".//n:emit/n:CNPJ", ns).text
        tomador_nome = root.find(".//n:dest/n:xNome", ns)
        if tomador_nome is not None and tomador_nome.text:
            tomador_nome = tomador_nome.text
        else:
            tomador_nome = None
        tomador_doc = root.find(".//n:dest/n:CPF", ns)
        if tomador_doc is not None and tomador_doc.text:
            tomador_doc = tomador_doc.text
        else:
            tomador_doc = None
        chave = root.find(".//n:protNFe/n:infProt/n:chNFe", ns).text
        cfop = root.find(".//n:CFOP", ns).text # Ta pegando primeiro CFOP
        e_cancelada = False #ACHAR EXEMPLO CANCELADO PARA IMPLEMENTAR
        return {
            'numero' : numero,
            'tipo' : 'nfce',
            'valor_total' : valor_total,
            'data_emissao' : data_emissao,
            'data_competencia' : data_competencia,
            'mes_ref' : mes_ref,
            'prestador_nome' : prestador_nome,
            'prestador_doc' : prestador_doc,
            'tomador_nome' : tomador_nome,
            'tomador_doc' : tomador_doc,
            'chave' : chave,
            'cfop' : cfop,
            'e_cancelada' : e_cancelada,
            'xml_text' : xml_texto
        }
    except Exception as e:
        print(f"ERRO ao parsear NFCe: {e}")
        return {}

def extrair_dados_nfe(root: ET.Element, namespace: str, xml_texto: str) -> dict:
    ns = {"n": namespace}
    try:
        numero = root.find(".//n:nNF", ns).text
        valor_total = Decimal(root.find(".//n:vNF", ns).text)
        data_emissao = root.find(".//n:dhEmi", ns).text
        data_competencia = root.find(".//n:dhEmi", ns).text
        data_emissao = datetime.strptime(data_emissao, '%Y-%m-%dT%H:%M:%S%z').date()
        data_competencia = datetime.strptime(data_competencia, '%Y-%m-%dT%H:%M:%S%z').date()
        mes_ref = date(data_emissao.year, data_emissao.month, 1)
        prestador_nome = root.find(".//n:emit/n:xNome",ns).text
        prestador_doc = root.find(".//n:emit/n:CNPJ", ns).text
        tomador_nome = root.find(".//n:dest/n:xNome", ns).text
        tomador_doc = root.find(".//n:dest/n:CNPJ", ns)
        if tomador_doc is not None and tomador_doc.text:
            tomador_doc = tomador_doc.text
        else:
            tomador_doc = None
        chave = root.find(".//n:protNFe/n:infProt/n:chNFe", ns).text
        cfop = root.find(".//n:CFOP", ns).text # Ta pegando primeiro CFOP
        e_cancelada = False #ACHAR EXEMPLO CANCELADO PARA IMPLEMENTAR
        return {
            'numero' : numero,
            'tipo' : 'nfe',
            'valor_total' : valor_total,
            'data_emissao' : data_emissao,
            'data_competencia' : data_competencia,
            'mes_ref' : mes_ref,
            'prestador_nome' : prestador_nome,
            'prestador_doc' : prestador_doc,
            'tomador_nome' : tomador_nome,
            'tomador_doc' : tomador_doc,
            'chave' : chave,
            'cfop' : cfop,
            'e_cancelada' : e_cancelada,
            'xml_text' : xml_texto
        }
    except Exception as e:
        print(f"ERRO ao parsear NFCe: {e}")
        return {}
