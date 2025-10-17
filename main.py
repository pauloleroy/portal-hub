import streamlit as st
from scripts.conexao_db import DatabaseService
from scripts import consultar_cnpj
from pathlib import Path
from datetime import datetime
import time
from scripts.repositories.empresas_repo import EmpresaRepository
from scripts.repositories.notas_repo import NotasRepository
from scripts.nota import Nota


st.set_page_config(page_title="Portal HUB")
st.title('Portal HUB')

db_service = DatabaseService()
empresas_repo = EmpresaRepository(db_service)
notas_repo = NotasRepository(db_service)

tab1, tab2, tab3 = st.tabs(["Notas", "Cadastrar Empresa", "Cadastrar Sócio"])


@st.fragment()
def notas():
    arquivos = st.file_uploader(
        "Selecione arquivos XML",
        type="xml",
        accept_multiple_files=True
    )

    if st.button("Processar Notas") and arquivos:
        for arquivo in arquivos:
            nota = Nota(arquivo)
            retorno = nota.enviar_nota_db('37851556000101', empresas_repo, notas_repo)
            print(f'valor retorno: {retorno}')
    

@st.fragment()
def cadastro_empresa():
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
    
    st.subheader('Cadastrar Empresa')
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
            form_values['matriz_id'] = empresas_repo.procurar_empresa_id(cnpj=cnpj_matriz)
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
            retorno_conexao = empresas_repo.cadastrar_empresa_socio(tabela='empresas',dados=form_values)
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

@st.fragment()
def cadastro_socio():
    if 'form_socio' not in st.session_state:
        st.session_state.form_socio = {
            'empresa_id' : None,
            'nome' : None,
            'cpf' : None,
            'identificador_prof' : None,
            'email' : None,
            'telefone' : None,
            'percentual_participacao' : None
        }   
    st.subheader("Cadastrar Sócio")
    form_socio = st.session_state.form_socio
    lista_empresas = empresas_repo.pegar_empresas()
    opcoes = {f"{e['nome']} ({e['cnpj']})": e["id"] for e in lista_empresas}

    if 'selectbox_index' not in st.session_state:
        st.session_state.selectbox_index = None
    escolha = st.selectbox(
        "Selecione a empresa:",
        options=list(opcoes.keys()),
        index=st.session_state.selectbox_index,
        placeholder="Digite para buscar...",
        key='empresas_socios'
    )
    if escolha is not None and escolha in opcoes: 
        form_socio['empresa_id'] = opcoes[escolha]
        st.session_state.selectbox_index = list(opcoes.keys()).index(escolha)

    col_nome, col_cpf = st.columns([3,1])
    form_socio['nome'] = col_nome.text_input('Nome', value=form_socio['nome'], key='nome_socio')
    form_socio['cpf'] = col_cpf.text_input('CPF', value=form_socio['cpf'], key='cpf_socio')
    col_email, col_tefone = st.columns([1,1])
    form_socio['email'] = col_email.text_input('Email', value=form_socio['email'], key='email_socio')
    form_socio['telefone'] = col_tefone.text_input('Telefone', value=form_socio['telefone'], key='telefone_socio')
    col_id, col_percentual = st.columns([1,1])
    form_socio['identificador_prof'] = col_id.text_input('Identificador', value=form_socio['identificador_prof'], placeholder='ex. CRM, CRO, CREA, CPF', key = 'identificador_socio')
    form_socio['percentual_participacao'] = col_percentual.number_input('Percentual de participação', value=form_socio['percentual_participacao'], min_value=0, max_value=100, step=1, key='pct_participacao')
    if st.button('Cadastar Sócio') :
        erros = []
        if not form_socio['empresa_id']:
            erros.append('Empresa é obrigatório')
        if not form_socio['nome']:
            erros.append('Nome é obrigatório')
        if erros:
            for e in erros:
                st.error(e)
        else:
            retorno_conexao = empresas_repo.cadastrar_empresa_socio(tabela='socios',dados=form_socio)
            if retorno_conexao is None:
                st.success("Sócio Cadastrado com Sucesso")

                time.sleep(2)

                st.session_state.form_socio = {
                'empresa_id' : None,
                'nome' : None,
                'cpf' : None,
                'identificador_prof' : None,
                'email' : None,
                'telefone' : None,
                'percentual_participacao' : None
            }
                st.rerun()
            else:
                st.error(retorno_conexao)


with tab1:
    notas()
with tab2:
    cadastro_empresa()
with tab3:
    cadastro_socio()