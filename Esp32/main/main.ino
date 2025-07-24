#include <WiFi.h>
#include <HTTPClient.h>

// Definições de pinos e constantes
#define SENSOR_PIN 34
#define LED_LEITURA_PIN 14
#define LED_ANORMAL_PIN 13
#define ARRAY_SIZE 141
#define DELAY_BETWEEN_READINGS 20
#define READINGS_PER_MINUTE 600
#define VERIFICAR_STATUS_INTERVALO 5000

// Configurações de rede
const char* WIFI_SSID = "Rede";
const char* WIFI_PASSWORD = "123456780";
const char* API_URL = "http://192.168.0.6:8000/analisar";
const char* STATUS_URL = "http://192.168.0.6:8000/ultimo_dado";

// Variáveis globais
int batimentos[ARRAY_SIZE];
int contador = 0;
unsigned long ultimaVerificacaoStatus = 0;

// Estrutura para armazenar status dos batimentos
struct StatusBatimentos {
    float media;
    const char* status;
};

// Protótipos das funções
void setupWiFi();
StatusBatimentos analisarBatimentosLocal();
void enviarDados(const StatusBatimentos& status);
void ultimoStatusIA();
void atualizarLEDs(bool lendo, bool anormal);

void setup() {
    pinMode(SENSOR_PIN, INPUT);
    pinMode(LED_LEITURA_PIN, OUTPUT);
    pinMode(LED_ANORMAL_PIN, OUTPUT);
    digitalWrite(LED_LEITURA_PIN, LOW);
    digitalWrite(LED_ANORMAL_PIN, LOW);

    Serial.begin(9600);
    setupWiFi();

}

void loop() {    
    // Pega os batimentos
    batimentos[contador] = analogRead(SENSOR_PIN);
    contador++;
    
    // Se temos 141 amostras enviamos
    if (contador == ARRAY_SIZE) {
        StatusBatimentos status = analisarBatimentosLocal();
        // Passo o status local
        enviarDados(status);
        contador = 0;
    }

    // Se passou 5 segundos verifica o status da ia no ultimo envio
    if (millis() - ultimaVerificacaoStatus >= VERIFICAR_STATUS_INTERVALO) {
        ultimoStatusIA();
        ultimaVerificacaoStatus = millis();
    }

    delay(DELAY_BETWEEN_READINGS);
}


void atualizarLEDs(bool lendo, bool anormal) {
    digitalWrite(LED_LEITURA_PIN, lendo ? HIGH : LOW);
    digitalWrite(LED_ANORMAL_PIN, anormal ? HIGH : LOW);
}

void setupWiFi() {
    Serial.println("Iniciando conexão WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.println("Conectando ao WiFi...");
    }

    Serial.println("Conexão WiFi estabelecida!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
}



StatusBatimentos analisarBatimentosLocal() {

    // média
    long soma = 0;
    for (int i = 0; i < ARRAY_SIZE; i++) {
        soma += batimentos[i];
    }
    float media = (float)soma / ARRAY_SIZE;
    
    // Conversão correta para BPM
    // BPM = (média / 1023) * 60 * 1000
    // onde 1023 é o valor máximo do ADC (10 bits)
    // 60 é para converter de segundos para minutos
    // 1000 é para converter de milissegundos para segundos
    // DELAY_BETWEEN_READINGS é o intervalo entre leituras em milisseg
    float bpm = (media / 1023.0) * 60.0 * 1000.0 / DELAY_BETWEEN_READINGS;

    StatusBatimentos status;
    status.media = media;

    if (bpm < 60) {
        status.status = "Bat. Baixo";
    } else if (bpm > 100) {
        status.status = "Bat. alto";
    } else {
        status.status = "Estável";
    }

    Serial.print("BPM calculado: ");
    Serial.println(bpm);

    return status;
}

void enviarDados(const StatusBatimentos& status) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.print("WiFi desconectado!");
        return;
    }

    HTTPClient http;
    http.begin(API_URL);
    http.addHeader("Content-Type", "application/json");

    //por enquanto vamos faze apenas para 1 usuário
    String jsonData = "{\"user_id\": 1, \"batimentos\": [";
    // Constrói o JSON com os batimentos
    for (int i = 0; i < ARRAY_SIZE; i++) {
        jsonData += String(batimentos[i]);
        // Adiciona vírgula entre os batimentos, mas não no final
        if (i < ARRAY_SIZE - 1) jsonData += ",";
    }
    // Fecha o array de batimentos e adiciona os outros campos
    // "spo2" e "press" são placeholders, pois não estamos usando esses dados ainda
    jsonData += "], \"spo2\": 0, \"press\": 0, \"status_local\": \"" + String(status.status) + "\"}";



    int httpResponseCode = http.POST(jsonData);
    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("Resposta da API: " + response);
    } else {
        Serial.println("Erro ao enviar dados: " + String(httpResponseCode));
    }

    http.end();
}

void ultimoStatusIA() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.print("WiFi desconectado durante verificação de status!");
        return;
    }

    HTTPClient http;
    http.begin(STATUS_URL);
    int httpResponseCode = http.GET();

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("Último status: " + response);

        // Se o diagnósticoIA não for normal ou
        // o status local não for estável,
        // mantém LED de status anormal ligado
        bool statusAnormal = 
            (response.indexOf("\"diagnostico_ia\":\"normal\"") == -1) || 
            (response.indexOf("\"status_local\":\"Estável\"") == -1);

        // atualiza os LEDs
        // Se Lendo, Status Anormal
        atualizarLEDs(true, statusAnormal);

        // Se esta normal, exbir mensagem
        if (statusAnormal) {
            Serial.println("Status anormal detectado, mantendo LED de anormalidade ligado.");
        } else {
            Serial.println("Status normal, desligando LED de anormalidade.");
        }
    } else {
        Serial.println("Erro ao verificar último status: " + String(httpResponseCode));
    }

    http.end();
}