import xml.etree.ElementTree as ET
from decimal import Decimal
import re

# Carregar xml
tree = ET.parse("C:\\Users\\paulo\\Downloads\\nfse_202500000000671.xml")
root = tree.getroot()


# Loop por todos elementos
# for elem in root.findall(".//n:*", ns):
#     print(elem.tag, elem.text)

#NFS - Prefeitura BH
def extrair_dados_pbh(nota_xml):
    ns = {"n":"http://www.abrasf.org.br/nfse.xsd"}
    numero = nota_xml.find(".//n:Numero", ns).text
    valor = Decimal(nota_xml.find(".//n:ValorServicos", ns).text)
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
        print(valor_iss)
    outras_info = nota_xml.find(".//n:OutrasInformacoes", ns).text
    chave = re.search(r"\d{44}", outras_info)
    chave = chave.group(0) if chave else None


extrair_dados_pbh(root)