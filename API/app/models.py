from typing import Optional
from pydantic import BaseModel
import tensorflow as tf

# Modelo Pydantic
class DadosECG(BaseModel):
    user_id: int
    batimentos: list
    spo2: Optional[float] = None
    press: Optional[float] = None
    status_local: str

    def validar_batimentos(self):
        if not self.batimentos:
            raise ValueError("A lista de batimentos não pode estar vazia.")
        if len(self.batimentos) != 141:
            raise ValueError("A lista de batimentos deve conter exatamente 141 valores.")

# Modelo de IA
class Detector(tf.keras.Model):
    def __init__(self):
        super(Detector, self).__init__()
        self.encoder = tf.keras.Sequential([
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(8, activation='relu')
        ])
        self.decoder = tf.keras.Sequential([
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(141, activation='sigmoid')
        ])

    def call(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
