# -*- coding: utf-8 -*-
"""

Original file is located at
    https://www.kaggle.com/code/vijeetnigam26/anomaly-detection-ecg-autoencoders
"""

import tensorflow as tf
from tensorflow.keras import layers, losses
from tensorflow.keras.models import Model
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Carregar e preparar os dados
df = pd.read_csv('http://storage.googleapis.com/download.tensorflow.org/data/ecg.csv', header=None)
data = df.iloc[:, :-1].values
labels = df.iloc[:, -1].values

# Verificar a distribuição das classes
print(f"Normal: {np.sum(labels == 0)}, Anormal: {np.sum(labels == 1)}")

# Dividir os dados
train_data, test_data, train_labels, test_labels = train_test_split(data, labels, test_size=0.2, random_state=21)

# Normalizar os dados
min_val = tf.reduce_min(train_data)
max_val = tf.reduce_max(train_data)
train_data = (train_data - min_val) / (max_val - min_val)
test_data = (test_data - min_val) / (max_val - min_val)

train_data = tf.cast(train_data, dtype=tf.float32)
test_data = tf.cast(test_data, dtype=tf.float32)
train_labels = train_labels.astype(bool)

# Separar dados normais
n_train_data = train_data[train_labels]

# Definição do modelo com mais complexidade
class Autoencoder(Model):
    def __init__(self):
        super(Autoencoder, self).__init__()
        self.encoder = tf.keras.Sequential([
            layers.Dense(64, activation='relu'),
            layers.Dense(32, activation='relu'),
            layers.Dense(16, activation='relu')
        ])
        self.decoder = tf.keras.Sequential([
            layers.Dense(32, activation='relu'),
            layers.Dense(64, activation='relu'),
            layers.Dense(140, activation='sigmoid')
        ])

    def call(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

# Compilar e treinar o modelo
autoencoder = Autoencoder()
autoencoder.compile(optimizer='adam', loss='mae')
history = autoencoder.fit(
    n_train_data, n_train_data,
    epochs=200, batch_size=256, validation_split=0.2
)

# Salvar os pesos
autoencoder.save_weights('./PESO.weights.h5')

# Cálculo do threshold
reconstructed = autoencoder(n_train_data)
train_loss = losses.mae(reconstructed, n_train_data)
threshold = np.percentile(train_loss, 95)
print(f"Threshold: {threshold}")

# Avaliar o desempenho
reconstructed_test = autoencoder(test_data)
test_loss = losses.mae(reconstructed_test, test_data)

# Previsões
predictions = test_loss.numpy() < threshold

# Relatório de classificação
print(classification_report(test_labels, predictions, target_names=["Normal", "Anormal"]))

# Visualizar reconstrução de amostras
def plot_reconstruction(data, reconstructed_data, index):
    plt.plot(data[index], label="Entrada")
    plt.plot(reconstructed_data[index], label="Reconstrução")
    plt.fill_between(
        np.arange(len(data[index])),
        data[index], reconstructed_data[index],
        color="lightcoral", alpha=0.5
    )
    plt.legend()
    plt.show()

# Exemplo de reconstrução
plot_reconstruction(test_data, reconstructed_test, 0)
plot_reconstruction(test_data, reconstructed_test, 1)

# Cálculo da acurácia global
accuracy = np.mean(predictions == test_labels)
print(f"Acurácia Global: {accuracy * 100:.2f}%")