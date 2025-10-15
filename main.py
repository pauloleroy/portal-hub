import streamlit as st
from scripts import conexao_db
from scripts import funcoes_notas
from scripts import consultar_cnpj
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
import time

st.set_page_config(page_title="Portal HUB")
st.title('Portal HUB')


@st.fragment()
def notas():

    if st.button('Pegar abertura'):
        data_abertura = conexao_db.pegar_data_abertura(empresa_id=1)
        st.write('Data abertura:', data_abertura)

    arquivos = st.file_uploader(
        "Selecione arquivos XML",
        type="xml",
        accept_multiple_files=True
    )

    if st.button("Processar Notas") and arquivos:
        for arquivo in arquivos:
            conteudo = arquivo.read()
            funcoes_notas.inserir_notas(conteudo=conteudo)
    
    empresas = conexao_db.pegar_empresas()
    opcoes = {f"{e['nome']} ({e['cnpj']})": e["id"] for e in empresas}

    escolha = st.selectbox(
        "Selecione a empresa:",
        options=list(opcoes.keys()),
        index=None,
        placeholder="Digite para buscar..."
    )

    if st.button("Procurar empresa"):
        if escolha:
            empresa_id = opcoes[escolha]
            st.session_state["empresa_id"] = empresa_id
            st.success(f"Empresa selecionada: {escolha}")
        else:
            st.warning("Selecione uma empresa antes de clicar no botão")    

@st.fragment()
def cadastros():
    if 'form_values' not in st.session_state:
        st.session_state.form_values = {
            'cnpj': None,
            'razao_social': None,
            'data_abertura' : None,
            'regime_tributario': None,
            'detalhes_tributarios': None,
            'email': None,
            'telefone': None,
            'situacao_cadastral': None,
            'is_matriz': True,
            'matriz_id': None
        }
    form_values = st.session_state.form_values
    opcoes_regime = ['simples', 'lucro_presumido', 'lucro_real']
    opcoes_matriz = [True, False]
    
    st.header('Cadastrar Empresa')
    form_values['cnpj'] = st.text_input('CNPJ', value=form_values['cnpj'])
    if st.button('Buscar CNPJ'):
        dados = consultar_cnpj.consultar_dados_cnpj(form_values['cnpj'])
        if dados:
            # Atualiza os valores no session_state
            form_values['razao_social'] = dados[0]['razao_social']
            form_values['situacao_cadastral'] = dados[0]['situacao_cadastral']
            form_values['data_abertura'] = dados[0]['data_abertura']
            if dados[0]['matriz_filial'] == 1:
                form_values['is_matriz'] = True
            else:
                form_values['is_matriz'] = False
        else:
            st.error('CNPJ inválido')
    form_values['razao_social'] = st.text_input('Razão Social', value=form_values['razao_social'])
    form_values['email'] = st.text_input('Email', value=form_values['email'])
    form_values['telefone'] = st.text_input('Telefone', value=form_values['telefone'])
    col_sit, col_data = st.columns([1,1])
    form_values['situacao_cadastral'] = col_sit.text_input('Situação cadastral', value=form_values['situacao_cadastral'])
    form_values['data_abertura'] = col_data.date_input('Data de abertura', value=form_values['data_abertura'], max_value=datetime.now(), min_value=datetime(1980, 1, 1))
    # Radio de regime tributário
    col_regime, col_det = st.columns([1,1])
    form_values['regime_tributario'] = col_regime.radio(
        'Regime Tributário', 
        opcoes_regime,
        index=opcoes_regime.index(form_values['regime_tributario']) if form_values['regime_tributario'] else 0
    )

    # Selectbox dinâmico de acordo com o regime
    if form_values['regime_tributario'] == 'simples':
        form_values['detalhes_tributarios'] = col_det.selectbox(
            'Anexo',
            options=['Anexo I', 'Anexo II', 'Anexo III', 'Anexo IV', 'Anexo V'],
            index=0
        )
    elif form_values['regime_tributario'] == 'lucro_presumido':
        form_values['detalhes_tributarios'] = col_det.selectbox(
            'Percentual Lucro Presumido',
            options=['8%', '32%'],
            index=0
        )
    else:  # lucro_real
        form_values['detalhes_tributarios'] = None
    
    form_values['is_matriz'] = st.radio('É matriz', opcoes_matriz, index=opcoes_matriz.index(form_values['is_matriz']))    

    if not form_values['is_matriz']:
        cnpj_matriz = st.text_input('CNPJ Matriz')
        if st.button('Procurar Matriz'):
            form_values['matriz_id'] = conexao_db.procurar_empresa_id(cnpj=cnpj_matriz)
        if form_values['matriz_id'] is not None:
            st.write("ID da Matriz:", form_values['matriz_id'])
        else:
            st.write("ID da Matriz: NÃO ENCONTRADO")

    if st.button("Cadastrar Empresa"):
        erros = []
        if not form_values['cnpj']:
            erros.append("CNPJ é obrigatório")
        if not form_values['razao_social']:
            erros.append("Razão Social é obrigatória")
        if not form_values['regime_tributario']:
            erros.append("Regime Tributário é obrigatório")
        
        if not form_values['is_matriz'] and not form_values['matriz_id']:
            erros.append("Filiais devem ter uma matriz válida") 

        if form_values['regime_tributario'] == 'simples' or form_values['regime_tributario'] == 'lucro_presumido':
            if not form_values['detalhes_tributarios']:
                erros.append("Anexo Simples ou Percuntual Lucro Presumido é obrigatório")

        if erros:
            for e in erros:
                st.error(e)
        else:
            retorno_conexao = conexao_db.cadastrar_empresa(dados=form_values)
            if retorno_conexao is None:
                st.success("Empresas Cadastrada com Sucesso")
                
                # Aguarda 2 segundos antes de limpar
                time.sleep(2)

                st.session_state.form_values = {
                'cnpj': None,
                'razao_social': None,
                'data_abertura': None,
                'regime_tributario': None,
                'detalhes_tributarios': None,
                'email': None,
                'telefone': None,
                'situacao_cadastral': None,
                'is_matriz': True,
                'matriz_id': None
            }
                st.rerun()
            else:
                st.error(retorno_conexao)
notas()
st.divider()
cadastros()