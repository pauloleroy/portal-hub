import streamlit as st
from scripts.conexao_db import DatabaseService
from scripts import consultar_cnpj
from pathlib import Path
from datetime import datetime
import time
from scripts.repositories.empresas_repo import EmpresaRepository
from scripts.repositories.notas_repo import NotasRepository
from scripts.repositories.simples_repo import SimplesRepository
from scripts.nota import Nota
from scripts.calculo_simples import CalculoSimples
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import calendar

st.set_page_config(page_title="Portal HUB")
st.title('Portal HUB')

db_service = DatabaseService()
empresas_repo = EmpresaRepository(db_service)
notas_repo = NotasRepository(db_service)
simples_repo = SimplesRepository(db_service)

tab1, tab2, tab3, tab4 = st.tabs(["Notas", "Apuração Simples","Cadastrar Empresa", "Cadastrar Sócio"])

def gerar_opcoes_competencia(meses_para_tras=18):
    """Gera uma lista de strings 'MM/AAAA' para as competências."""
    hoje = date.today().replace(day=1)
    opcoes = []
    # Cria a lista a partir do mês atual até meses_para_tras
    for i in range(meses_para_tras + 1):
        competencia = hoje - relativedelta(months=i)
        opcoes.append(competencia.strftime("%m/%Y"))
    return opcoes

#CONTEUDO DA PAGINA
@st.fragment()
def notas():
    lista_empresas_resultado = empresas_repo.pegar_empresas()
    if isinstance(lista_empresas_resultado, str):
        st.error(f"Erro ao carregar empresas do banco de dados: {lista_empresas_resultado}")
        return
    lista_empresas = lista_empresas_resultado or []
    opcoes = {f"{e['nome']} ({e['cnpj']})": e['cnpj'] for e in lista_empresas}
    if 'selectbox_index' not in st.session_state:
        st.session_state.selectbox_index = None
    cnpj = None
    st.subheader('Importar Notas')
    with st.form("notas_form", clear_on_submit=True):
        escolha = st.selectbox(
            "Selecione a empresa:",
            options=list(opcoes.keys()),
            index=st.session_state.selectbox_index,
            placeholder="Digite para buscar...",
            key='empresas_notas_form_sb'
        )
        if escolha is not None and escolha in opcoes: 
            cnpj = opcoes[escolha]
            try:
                st.session_state.selectbox_index = list(opcoes.keys()).index(escolha)
            except ValueError:
                st.session_state.selectbox_index = 0

        arquivos = st.file_uploader(
            "Selecione arquivos XML",
            type="xml",
            accept_multiple_files=True,
            key='arquivos_xml'
        )

        submitted = st.form_submit_button("Processar Notas")
    if submitted:
        erros = []
        if not cnpj:
            st.error('Por favor, selecione uma empresa.') 
            return

        if not arquivos:
            st.error('Por favor, selecione pelo menos um arquivo XML.')
            return

        with st.spinner('Processando notas...'):
            try:
                for arquivo in arquivos:
                    nota = Nota(arquivo)
                    retorno = nota.enviar_nota_db(cnpj , empresas_repo, notas_repo)
                    if retorno is not None: erros.append(retorno)
            except Exception as e:
                erros.append(f"Erro inesperado ao processar arquivo: {str(e)}")
        if erros:
            st.warning(f"Processamento concluído com {len(erros)} falhas. Veja os detalhes abaixo:")
            for e in erros:
                st.error(e)
            if len(arquivos) > len(erros):
                st.success(f"{len(arquivos) - len(erros)} nota(s) processada(s) com sucesso")
        else:
            st.success(f'Todas as {len(arquivos)} notas foram processadas com sucesso!') 
    

@st.fragment()
def apuracao_simples():
    # Criando seassion stade para radio de subtituir aliq na DB
    if 'recalcular_aliq' not in st.session_state:
        st.session_state.recalcular_aliq = False

    # Pegando empresas matriz da db
    lista_empresas_resultado = empresas_repo.pegar_empresas_matriz()

    # Verifica de se teve êxito na consulta de lista de empresas matriz db 
    if isinstance(lista_empresas_resultado, str):
        st.error(f"Erro ao carregar empresas do banco de dados: {lista_empresas_resultado}")
        return
    
    # Caso não haja nenhuma empresa cadastrada gerar lista vazia
    lista_empresas = lista_empresas_resultado or []
    # Setando valores para popular o select box chave NOME (CNPJ) valor ID
    opcoes = {f"{e['nome']} ({e['cnpj']})": e['id'] for e in lista_empresas}

    # Criando session_state do selectbox de empresas
    if 'selectbox_index' not in st.session_state:
        st.session_state.selectbox_index = None
    empresa_id = None

    st.subheader('Dados Simples')

    col_empresa, col_data = st.columns([3,1])
    # selectbox  de Empresas
    escolha = col_empresa.selectbox(
        "Selecione a empresa:",
        options=list(opcoes.keys()),
        index=st.session_state.selectbox_index,
        placeholder="Digite para buscar...",
        key='empresas_simples'
    )
    # Validação de seleção do selectbox
    if escolha is not None and escolha in opcoes: 
        empresa_id = opcoes[escolha]
        try:
            st.session_state.selectbox_index = list(opcoes.keys()).index(escolha)
        except ValueError:
            st.session_state.selectbox_index = 0

    # Gerando valores para popular selectbox mes referencia
    opcoes_competencia = gerar_opcoes_competencia(meses_para_tras=18)
    
    # select box mes referencia
    competencia_escolhida_str = col_data.selectbox(
        "Mês de Referência:",
        options=opcoes_competencia,
        index=1, # Default para o mês anterior (mais comum)
        key='mes_referencia_simples'
    )
    # tratando valores da seleção mes referencia para data 1º dia do mes
    mes, ano = map(int, competencia_escolhida_str.split('/'))
    mes_ref_date = date(ano, mes, 1)

    # Validação se alguma empreesa foi selecionada
    if empresa_id is None:
        return
    # Gerando dados de 1º e ult dia do mes para chamar funcoes que pedem periodo
    data_inicial = mes_ref_date
    ultimo_dia = calendar.monthrange(mes_ref_date.year, mes_ref_date.month)[1]
    data_final = mes_ref_date.replace(day=ultimo_dia)

    # Pegando da db anexo da empresa selecionada
    anexo = empresas_repo.pegar_anexo(empresa_id)
    
    # Validador para verificar se sitacao_fiscal na db está cadastrada corretamente ou não seja do simples
    VALIDADOR_ANEXO = ['Anexo I', 'Anexo II', 'Anexo III', 'Anexo IV', 'Anexo V']
    if anexo not in VALIDADOR_ANEXO:
        st.warning(f'Empresa não se enquadra no simples. Ou detalhe_trib: {anexo} cadastrado no formato errado')
        return
    
    col_btn, col_rad, col_empt1, col_btn2 = st.columns(4, gap=None, vertical_alignment='center')

    # Botão para apuração de aliq
    if col_btn.button('Apurar Alíquota'):
        # Criação da classe CalculoSimples para envio de dados e validação de retorno do commit na DB
        cal_simples = CalculoSimples(mes_ref_date, anexo, empresa_id, empresas_repo, notas_repo, simples_repo)
        retorno_enviar_aliq = cal_simples.enviar_aliq(st.session_state.recalcular_aliq)
        if isinstance(retorno_enviar_aliq, str):
            st.error(retorno_enviar_aliq)
        else:
            st.success('Alíquota Apurada')
    
    # Dict de opcoes do radio se é para substituir dados aliq
    opcoes_radio = { 'Não' : False, 'Sim' : True}
    escolha_radio = col_rad.radio('Substituir Aliq', list(opcoes_radio.keys()) , index=0, horizontal=True, key='radio_apuracao')
    st.session_state.recalcular_aliq = opcoes_radio[escolha_radio]
    
    # Botão para calcular valor estimado simples
    if col_btn2.button('Calcular Guia'):
        cal_simples = CalculoSimples(mes_ref_date, anexo, empresa_id, empresas_repo, notas_repo, simples_repo)
        retorno_calcular_guia = cal_simples.calcular_guia()
        if isinstance(retorno_calcular_guia, str):
            st.error(retorno_calcular_guia)
        else:
            st.success('Guia Calculada')

    # Gerando variaveis de Nome para gerar titulo dos cards
    nome_empresa = [chave for chave, valor in opcoes.items() if valor==empresa_id]

    # Pega dados do simples para um empresa e mes ref
    dados_mes = simples_repo.pegar_dados_mes(empresa_id, mes_ref_date)

    

    # Devem ser depois da consulta pois eles devem carregar para renderizar se tiver um e nao o outro
    # Valida retorno da db consulda de dados mes
    if isinstance(dados_mes, str):
        st.error(f"Erro no banco de dados ao buscar apuração: {dados_mes}")
        return
    # Valida retorno se nao hover apuracao para o mes
    if not dados_mes:
        st.warning(f"Nenhum dado de apuração encontrado para {competencia_escolhida_str}. Execute o cálculo primeiro.")
        return
    # Titulo cards
    st.text(f"{nome_empresa[0]} - {mes_ref_date.strftime('%m/%Y')} - {dados_mes['anexo']}")

    # Pegar se empresas tem filiais
    lista_filiais = empresas_repo.pegar_filias(empresa_id)

    # Pega dados de aliq e iss para verificar se existem
    aliq = dados_mes['aliquota_efetiva']
    iss = dados_mes['impostos']['ISS']

    # Valida se há valores para o mes e gera cards
    if isinstance(aliq, Decimal) and isinstance(iss, Decimal):
        
        # Conversao de valores para X,XXXXXXX
        aliq_percentual = (aliq * 100).quantize(Decimal('0.000001'))
        iss_percentual = (iss * 100).quantize(Decimal('0.000001'))
        
    else:
        st.error("Erro na tipagem dos dados. Alíquotas não são Decimais.")

    # Pega soma de notas com e sem retencao de iss se anexo III, IV ou V
    st.write(anexo)
    if anexo == "Anexo III" or anexo == "Anexo IV" or anexo == "Anexo V":
        com_sem_retencao = notas_repo.somar_receitas_por_retencao(empresa_id, data_inicial, data_final, incluir_grupo=True)
        # Valida retorno da consulta das notas com e sem retencao
        if isinstance(com_sem_retencao, str):
            st.erro("Erro no banco de dados ao buscar notas na rotina com_sem_retencao")
            return
    if anexo == "Anexo I" or "Anexo II":
        matriz_filial = {}
        matriz = empresas_repo.pegar_empresa_por_id(empresa_id)
        matriz_filial[matriz['cnpj']] = empresa_id
        for filial in lista_filiais:
            matriz_filial[filial['cnpj']] = filial['id']
    col_aliq, col_iss = st.columns(2)
    col_rbt, col_guia = st.columns(2)
    col_fat, col_ret = st.columns(2) 
    col_cret, col_sret = st.columns(2)
    
    col_aliq.metric('Alíquota Efetiva', f'{aliq_percentual} %')
    col_iss.metric('ISS do Simples', f'{iss_percentual} %')
    col_fat.metric("Faturamento Liq Mensal",f"R$ {dados_mes['faturamento_mensal']:,.2f}")
    col_ret.metric("Retenção ISS",f"R$ {dados_mes['retencoes']:,.2f}")
    col_rbt.metric("RBT12",f"R$ {dados_mes['rbt12']:,.2f}")
    col_guia.metric('Guia DAS Estimada', f"R$ {dados_mes['valor_estimado_guia']:,.2f}")
    if anexo == "Anexo III" or anexo == "Anexo IV" or anexo == "Anexo V":
        col_cret.metric("Faturamento Com Retencao",f"R$ {com_sem_retencao['receita_com_retencao']:,.2f}")
        col_sret.metric("Faturamento Com Retencao",f"R$ {com_sem_retencao['receita_sem_retencao']:,.2f}")
    if anexo == "Anexo I" or anexo == "Anexo II":
        for cnpj, matriz_filial_id in matriz_filial.items():
            fat_matriz_filial = notas_repo.somar_faturamento_liquido(matriz_filial_id, data_inicial, data_final)
            st.metric(f"Fat Liq ({cnpj})",f"R$ {fat_matriz_filial:,.2f}")

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
    st.divider()
with tab2:
    apuracao_simples()
with tab3:
    cadastro_empresa()
with tab4:
    cadastro_socio()