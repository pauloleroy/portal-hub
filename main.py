import streamlit as st
from scripts import conexao_db
from scripts import funcoes_notas
import os
from dotenv import load_dotenv
import psycopg2
from pathlib import Path
import xml.etree.ElementTree as ET


load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    st.write('Hello world 123')

    if st.button('Pegar abertura'):
        data_abertura = conexao_db.pegar_data_abertura(conn, 1)
        st.write('Data abertura:', data_abertura)

    arquivos = st.file_uploader(
        "Selecione arquivos XML",
        type="xml",
        accept_multiple_files=True
    )

    if st.button("Processar Notas") and arquivos:
        for arquivo in arquivos:
            conteudo = arquivo.read()
            funcoes_notas.inserir_notas(conn, conteudo)
    
    empresas = conexao_db.pegar_empresas(conn)
    opcoes = {f"{e['nome']} ({e['cnpj']})": e["id"] for e in empresas}
    escolha = st.selectbox("Selecione a empresa:", options=list(opcoes.keys()), index=None, placeholder="Digite para buscar...")
    empresa_id = opcoes[escolha]
    st.session_state["empresa_id"] = empresa_id        
except Exception as e:
    print(f"Erro na conexão: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()

