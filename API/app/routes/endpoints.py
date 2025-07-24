from fastapi import APIRouter, HTTPException
import sqlite3
import tensorflow as tf
import numpy as np
import json
from datetime import datetime

from models import DadosECG, Detector
from utils import normalizar_dados, calcular_diagnostico
from database import db_path

router = APIRouter()

modelo = Detector()
modelo.build(input_shape=(None, 141))
try:
    modelo.compile(optimizer='adam', loss='mae')
    modelo.load_weights("./PESO.weights.h5")
except Exception as e:
    raise Exception("Falha ao carregar os pesos do modelo")

# RECEBE PARA ANALISAR O ECG
@router.post("/analisar")
def analisar_ecg(dados: DadosECG):
    try:
        dados.validar_batimentos()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    batimentos_norm = normalizar_dados(dados.batimentos)
    batimentos_norm = np.clip(batimentos_norm, 0, 1)
    batimentos_norm = tf.expand_dims(tf.cast(batimentos_norm, tf.float32), axis=0)

    reconstruido = modelo(batimentos_norm)
    mae = tf.keras.losses.MeanAbsoluteError()
    perda = mae(batimentos_norm, reconstruido).numpy()

    diagnostico_ia, nivel_risco = calcular_diagnostico(perda)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = """
                INSERT INTO dados_locais (
                    user_id, bat, spo2, press, status_local, diagnostico_ia, perda, data, hora
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            valores = (
                dados.user_id,
                json.dumps([float(x) for x in batimentos_norm.numpy().flatten()]),
                float(dados.spo2) if dados.spo2 else None,
                float(dados.press) if dados.press else None,
                dados.status_local,
                diagnostico_ia,
                float(perda),
                datetime.now().strftime("%Y-%m-%d"),
                datetime.now().strftime("%H:%M:%S")
            )
            cursor.execute(query, valores)
            conn.commit()
    except sqlite3.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no banco de dados: {err}")

    return {
        "status_local": dados.status_local,
        "diagnostico_ia": diagnostico_ia,
        "nivel_risco": nivel_risco,
        "perda": float(perda)
    }


# RETORNA OS ULTIMOS 5 DADOS
@router.get("/ultimos_5_dados")
def ultimos_dados():
    try:
        # CONECTA
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # CONSULTA OS ULTIMOS 5 REGISTROS
            query = (
                "SELECT id, user_id, bat, spo2, press, status_local, diagnostico_ia, perda, data, hora "
                "FROM dados_locais "
                "ORDER BY id DESC LIMIT 5"
            )
            cursor.execute(query)
            registros = cursor.fetchall()

            # FORMATA OS DADOS
            dados_formatados = [
                {
                    "id": registro[0],
                    "user_id": registro[1],
                    "batimentos": json.loads(registro[2]),
                    "spo2": registro[3],
                    "press": registro[4],
                    "status_local": registro[5],
                    "diagnostico_ia": registro[6],
                    "perda": registro[7],
                    "data": registro[8],
                    "hora": registro[9],
                }
                for registro in registros
            ]

            return {"ultimos_dados": dados_formatados}

    except sqlite3.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar o banco de dados: {err}")


# RETORNA O ULTIMO DADO
@router.get("/ultimo_dado")
def ultimo_dado():
    try:
        # CONECTA
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # CONSULTA O ULTIMO REGISTRO
            query = (
                "SELECT id, user_id, bat, spo2, press, status_local, diagnostico_ia, perda, data, hora "
                "FROM dados_locais "
                "ORDER BY id DESC LIMIT 1"
            )
            cursor.execute(query)
            registro = cursor.fetchone()

            # SE NAO TEM RETORNA 404
            if not registro:
                raise HTTPException(
                    status_code=404, 
                    detail="Nenhum registro encontrado no banco de dados"
                )

            # FORMATA O DADO
            dado_formatado = {
                "id": registro[0],
                "user_id": registro[1],
                "batimentos": json.loads(registro[2]),
                "spo2": registro[3],
                "press": registro[4],
                "status_local": registro[5],
                "diagnostico_ia": registro[6],
                "perda": registro[7],
                "data": registro[8],
                "hora": registro[9],
            }

            return dado_formatado

    except sqlite3.Error as err:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao consultar o banco de dados: {err}"
        )
    

# BUSCA DADOS POR DATA
@router.get("/dados_por_data")
def dados_por_data(data_inicio: str, data_fim: str):
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, user_id, bat, spo2, press, status_local, diagnostico_ia, perda, data, hora
                FROM dados_locais 
                WHERE data BETWEEN ? AND ?
                ORDER BY data DESC, hora DESC
            """
            cursor.execute(query, (data_inicio, data_fim))
            registros = cursor.fetchall()
            
            dados_formatados = [{
                "id": r[0],
                "user_id": r[1],
                "batimentos": json.loads(r[2]),
                "spo2": r[3],
                "press": r[4],
                "status_local": r[5],
                "diagnostico_ia": r[6],
                "perda": r[7],
                "data": r[8],
                "hora": r[9]
            } for r in registros]
            return {"dados": dados_formatados}
    except sqlite3.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar o banco de dados: {err}")


# BUSCA DADOS ANORMAIS
@router.get("/dados_anormais")
def dados_anormais():
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, user_id, bat, spo2, press, status_local, diagnostico_ia, perda, data, hora
                FROM dados_locais 
                WHERE diagnostico_ia = 'anormal' OR perda >= 0.5
                ORDER BY data DESC, hora DESC
            """
            cursor.execute(query)
            registros = cursor.fetchall()
            
            dados_formatados = [{
                "id": r[0],
                "user_id": r[1],
                "batimentos": json.loads(r[2]),
                "spo2": r[3],
                "press": r[4],
                "status_local": r[5],
                "diagnostico_ia": r[6],
                "perda": r[7],
                "data": r[8],
                "hora": r[9]
            } for r in registros]
            
            print(dados_anormais)
            return {"dados": dados_formatados}
    except sqlite3.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar o banco de dados: {err}")

