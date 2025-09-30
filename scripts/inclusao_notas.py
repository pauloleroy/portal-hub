#inclusao_notas.py
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import funcoes_notas
import xml.etree.ElementTree as ET
import conexao_db
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}


def selecionar_xmls() -> list[Path]:
    """
    Abre o seletor nativo de arquivos do Windows para múltiplos arquivos XML.
    Retorna uma lista de Paths.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # garante que a janela fique em frente

    # Abre o diálogo para múltiplos arquivos XML
    arquivos = filedialog.askopenfilenames(
        title="Selecione arquivos XML",
        filetypes=[("Arquivos XML", "*.xml")],
    )

    # Converte cada caminho em Path
    return [Path(a) for a in arquivos]

if __name__ == "__main__":
    arquivos = selecionar_xmls()
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        if arquivos:
            for a in arquivos:
                tree = ET.parse(a)
                root = tree.getroot()
                nota = funcoes_notas.extrair_dados_pbh(root)

                # Buscar empresa_id dinamicamente
                cnpj_prestador = nota.get('prestador_doc')
                if cnpj_prestador:
                    empresa_id = conexao_db.procurar_empresa_id(conn, cnpj_prestador)
                    if empresa_id:
                        nota['empresa_id'] = empresa_id
                        conexao_db.inserir_dict(conn, "notas", nota)
                        print(f"✅ Nota {nota.get('chave')} inserida para empresa ID {empresa_id}")
                    else:
                        print(f"❌ Empresa com CNPJ {cnpj_prestador} não cadastrada. Nota {nota.get('chave')} ignorada.")
                else:
                    print(f"❌ CNPJ do prestador não encontrado na nota {nota.get('chave')}.")
        else:
            print("Nenhum arquivo selecionado.")
    except Exception as e:
        print(f"Erro na conexão: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()