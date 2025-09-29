import xml.etree.ElementTree as ET
from decimal import Decimal
import re
from datetime import datetime
from identificacao_socios import definir_socio


#NFS - Prefeitura BH
def extrair_dados_pbh(nota_xml):
    ns = {"n":"http://www.abrasf.org.br/nfse.xsd"}
    numero = nota_xml.find(".//n:Numero", ns).text
    valor_total = Decimal(nota_xml.find(".//n:ValorServicos", ns).text)
    data_emissao = nota_xml.find(".//n:DataEmissao", ns).text
    data_competencia = nota_xml.find(".//n:Competencia", ns).text
    data_emissao = datetime.strptime(data_emissao, '%Y-%m-%dT%H:%M:%S').date()
    data_competencia = datetime.strptime(data_competencia, '%Y-%m-%dT%H:%M:%S').date()
    prestador_nome = nota_xml.find(".//n:PrestadorServico//n:RazaoSocial",ns).text
    prestador_doc = nota_xml.find(".//n:IdentificacaoPrestador/n:Cnpj", ns).text
    tomador_nome = nota_xml.find(".//n:TomadorServico/n:RazaoSocial", ns).text
    tomador_doc = nota_xml.find(".//n:IdentificacaoTomador/n:CpfCnpj/n:Cnpj", ns)
    if tomador_doc is not None and tomador_doc.text:
        tomador_doc = tomador_doc.text
    else:
        tomador_doc = nota_xml.find(".//n:IdentificacaoTomador/n:CpfCnpj/n:Cpf", ns)
        tomador_doc = tomador_doc.text if tomador_doc is not None and tomador_doc.text else None
    tem_iss_retido = nota_xml.find(".//n:IssRetido", ns).text
    if tem_iss_retido == "1":
        valor_iss = Decimal(nota_xml.find(".//n:ValorIss", ns).text)
    else:
        valor_iss = 0
    outras_info = nota_xml.find(".//n:OutrasInformacoes", ns).text
    chave = re.search(r"\d{44}", outras_info)
    chave = chave.group(0) if chave else None
    discrinacao = nota_xml.find(".//n:Discriminacao", ns).text
    socio = definir_socio(discrinacao, prestador_doc)
    cancelamento = nota_xml.find(".//n:NfseCancelamento", ns)
    if cancelamento is not None:
        e_cancelada = True
    else:
        e_cancelada = False
    arquivo_completo = ET.tostring(nota_xml, encoding="utf-8").decode("utf-8")
    return {
        'numero' : numero,
        'tipo' : 'nfse_pbh',
        'valor_total' : valor_total,
        'data_emissao' : data_emissao,
        'data_competencia' : data_competencia,
        'prestador_nome' : prestador_nome,
        'prestador_doc' : prestador_doc,
        'tomador_nome' : tomador_nome,
        'tomador_doc' : tomador_doc,
        'valor_iss' : valor_iss,
        'chave' : chave,
        'socio' : socio,
        'retencoes' : {},
        'e_cancelada' : e_cancelada,
        'arquivo_completo' : arquivo_completo
    }
