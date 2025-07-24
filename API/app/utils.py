import numpy as np

def normalizar_dados(dados):
    dados = np.array(dados)
    min_val = dados.min()
    max_val = dados.max()
    return (dados - min_val) / (max_val - min_val)

def calcular_diagnostico(perda):
    if perda < 0.3:  
        return "normal", "baixo"
    elif perda < 0.4:
        return "suspeito", "médio"
    else:
        return "anormal", "alto"
