import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import funcoes_notas
import xml.etree.ElementTree as ET

def selecionar_xmls() -> list[Path]:
    """
    Abre o seletor nativo de arquivos do Windows para múltiplos arquivos XML.
    Retorna uma lista de Paths.
    """
    # Inicializa Tkinter sem mostrar a janela principal
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

# Exemplo de uso
if __name__ == "__main__":
    arquivos = selecionar_xmls()
    if arquivos:
        for a in arquivos:
            tree = ET.parse("C:\\Users\\paulo\\Downloads\\nfse_202500000000661.xml")
            root = tree.getroot()
            nota = funcoes_notas.extrair_dados_pbh(root)
    else:
        print("Nenhum arquivo selecionado.")
