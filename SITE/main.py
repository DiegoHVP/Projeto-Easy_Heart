# IMPORTANDO BIBLIOTECAS
import streamlit as st
import requests
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# URL base da API
BASE_URL = "http://localhost:8000"

# CONFIGURAÇÕES INICIAIS DA TELA
st.set_page_config(page_title="Análise de Batimentos Cardíacos", layout="wide")
st.title("Análise de Batimentos Cardíacos")

# BOTÕES DE ESCOLHA DE VISUALIZAÇÃO
visualizacao = st.radio(
    "Selecione o tipo de visualização:",
    ["Últimos 5 registros", "Busca por data", "Registros anormais"]
)

# FUNÇÃO PARA PLOTAR OS BATIMENTOS
def plot_batimentos(registro):
    # Converte os batimentos para array NumPy
    batimentos = np.array(registro["batimentos"], dtype=np.float32)

    # Reconstrói os batimentos simulando IA
    reconstructed = batimentos * 0.9 + 0.1

    # Calcula erro entre real e reconstruído
    erro = np.abs(batimentos - reconstructed)

    # Cria 2 gráficos
    fig, ax = plt.subplots(2, 1, figsize=(12, 8))

    # Primeiro gráfico: batimentos reais
    ax[0].plot(batimentos, label="Batimentos reais", color="blue")
    ax[0].set_title("Batimentos reais", fontsize=12)
    ax[0].set_xlabel("Amostra")
    ax[0].set_ylabel("Amplitude")
    ax[0].grid(True)
    ax[0].legend()

    # Segundo gráfico: real vs reconstruído
    ax[1].plot(batimentos, label="Batimentos reais", color="blue", linestyle="--")
    ax[1].plot(reconstructed, label="Reconstrução (IA)", color="red")
    ax[1].set_title("Comparação: Original vs Reconstrução", fontsize=12)
    ax[1].set_xlabel("Amostra")
    ax[1].set_ylabel("Amplitude")
    ax[1].grid(True)
    ax[1].legend()

    # Ajusta o layout
    plt.tight_layout()
    return fig, erro

# FUNÇÃO PARA EXIBIR A TABELA DOS DADOS
def exibir_dados(dados):
    if dados:
        df = pd.DataFrame(dados)

        # Garante que a coluna batimentos exista
        if "batimentos" not in df.columns:
            df["batimentos"] = [d["batimentos"] for d in dados]

        # Seleciona colunas específicas
        df_display = df[[
            "id", "user_id", "spo2", "press", "status_local", 
            "diagnostico_ia", "perda", "data", "hora"
        ]]

        # Renomeia colunas para exibição
        df_display.columns = [
            "ID", "Usuário", "SpO2", "Pressão", "Status Local",
            "Diagnóstico IA", "Erro (Perda)", "Data", "Hora"
        ]

        # Mostra métricas no topo
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Registros", len(df))
        with col2:
            st.metric("Registros Anormais", len(df[df_display["Diagnóstico IA"] == "anormal"]))
        with col3:
            st.metric("Erro Médio", f"{df_display['Erro (Perda)'].mean():.4f}")

        # Mostra a tabela colorida
        st.dataframe(
            df_display.style
                .highlight_max(subset=['Erro (Perda)'], color='red')
                .highlight_min(subset=['SpO2'], color='yellow'),
            height=300
        )

        return df_display, dados

# FUNÇÃO PARA MOSTRAR DETALHES DE UM REGISTRO
def mostrar_detalhes_registro(registro, dados_completos):
    # Mostra informações principais em 4 colunas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("SpO2", f"{registro['spo2']}%")
    with col2:
        st.metric("Pressão", registro['press'])
    with col3:
        st.metric("Status Local", registro['status_local'])
    with col4:
        st.metric("Erro (Perda)", f"{registro['perda']:.4f}")

    # Mostra os gráficos
    fig, erro = plot_batimentos(registro)
    st.pyplot(fig)

    # Mostra os erros calculados
    st.subheader("Análise do Erro")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Erro Médio", f"{np.mean(erro):.4f}")
    with col2:
        st.metric("Erro Máximo", f"{np.max(erro):.4f}")

# BLOCO PRINCIPAL DE EXECUÇÃO
try:
    # CASO 1: VISUALIZA OS ÚLTIMOS 5 DADOS
    if visualizacao == "Últimos 5 registros":
        response = requests.get(f"{BASE_URL}/ultimos_5_dados")
        dados = response.json()["ultimos_dados"]

        df_display, dados_completos = exibir_dados(dados)

        if dados_completos:
            registro_selecionado = st.selectbox(
                "Selecione um registro para visualizar os gráficos:",
                options=dados_completos,
                format_func=lambda x: f"ID: {x['id']} - {x['data']} {x['hora']} - Diagnóstico: {x['diagnostico_ia']}"
            )
            if registro_selecionado:
                mostrar_detalhes_registro(registro_selecionado, dados_completos)

    # CASO 2: FILTRA POR DATA
    elif visualizacao == "Busca por data":
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial", value=datetime.now() - timedelta(days=7))
        with col2:
            data_fim = st.date_input("Data final", value=datetime.now())

        if "dados_busca" not in st.session_state:
            st.session_state.dados_busca = None

        if st.button("Buscar", type="primary"):
            response = requests.get(
                f"{BASE_URL}/dados_por_data",
                params={
                    "data_inicio": data_inicio.strftime("%Y-%m-%d"),
                    "data_fim": data_fim.strftime("%Y-%m-%d")
                }
            )
            st.session_state.dados_busca = response.json()["dados"]

        if st.session_state.dados_busca:
            df_display, dados_completos = exibir_dados(st.session_state.dados_busca)

            registro_selecionado = st.selectbox(
                "Selecione um registro para visualizar os gráficos:",
                options=dados_completos,
                format_func=lambda x: f"ID: {x['id']} - {x['data']} {x['hora']} - Diagnóstico: {x['diagnostico_ia']}"
            )
            if registro_selecionado:
                mostrar_detalhes_registro(registro_selecionado, dados_completos)

    # CASO 3: REGISTROS ANORMAIS
    else:
        response = requests.get(f"{BASE_URL}/dados_anormais")
        dados = response.json()["dados"]
        st.warning("⚠️ Exibindo apenas registros classificados como anormais")

        df_display, dados_completos = exibir_dados(dados)

        if dados_completos:
            registro_selecionado = st.selectbox(
                "Selecione um registro para visualizar os gráficos:",
                options=dados_completos,
                format_func=lambda x: f"ID: {x['id']} - {x['data']} {x['hora']} - Diagnóstico: {x['diagnostico_ia']}"
            )
            if registro_selecionado:
                mostrar_detalhes_registro(registro_selecionado, dados_completos)

# TRATAMENTO DE ERROS CASO A API FALHE
except requests.RequestException as e:
    st.error(f"Erro ao acessar a API: {e}")
    st.info("Verifique se a API está rodando em: " + BASE_URL)
