#if 0
Configuracao Arduino IDE:
- Board: ESP32S3 Dev Module
- USB CDC On Boot: Enabled
- USB Mode: Hardware CDC and JTAG
- Upload Mode: UART0 / Hardware CDC
- Flash Size: 16MB (128Mb)
- PSRAM: OPI PSRAM
- Upload Speed: 921600

Entradas analogicas:
- GPIO4: SCT013 corrente (ADC1_CH3)
- GPIO5: ZMPT101B tensao (ADC1_CH4)

Veja tambem: CONFIGURACAO_ARDUINO_IDE.md
#endif

#define ADC_CORRENTE_PIN 4
#define ADC_TENSAO_PIN 5

#define TAXA_AMOSTRAGEM_PADRAO 2000
#define TEMPO_CAPTURA_PADRAO 5
#define SPS_MIN 100
#define SPS_MAX 20000
#define TEMPO_MIN 1
#define TEMPO_MAX 60
#define NUM_AMOSTRAS_MAX 120000
#define STREAM_PACOTE_AMOSTRAS 100

uint32_t taxa_amostragem = TAXA_AMOSTRAGEM_PADRAO;
uint32_t tempo_captura = TEMPO_CAPTURA_PADRAO;
uint32_t num_amostras = TAXA_AMOSTRAGEM_PADRAO * TEMPO_CAPTURA_PADRAO;
uint32_t intervalo_us = 1000000UL / TAXA_AMOSTRAGEM_PADRAO;
bool modo_stream = false;
bool modo_binario = false;
bool modo_stream_binario = false;

uint16_t *amostras_corrente = nullptr;
uint16_t *amostras_tensao = nullptr;
uint32_t *tempos = nullptr;

bool configurarCaptura(String comando) {
  comando.trim();

  if (comando == "START") {
    taxa_amostragem = TAXA_AMOSTRAGEM_PADRAO;
    tempo_captura = TEMPO_CAPTURA_PADRAO;
    modo_stream = false;
    modo_binario = false;
    modo_stream_binario = false;
  } else if (comando.startsWith("START,")) {
    int primeira_virgula = comando.indexOf(',');
    int segunda_virgula = comando.indexOf(',', primeira_virgula + 1);

    if (segunda_virgula < 0) {
      Serial.println("ERROR,Formato esperado: START,SPS,TEMPO_S");
      return false;
    }

    taxa_amostragem = comando.substring(primeira_virgula + 1, segunda_virgula).toInt();

    int terceira_virgula = comando.indexOf(',', segunda_virgula + 1);
    if (terceira_virgula < 0) {
      tempo_captura = comando.substring(segunda_virgula + 1).toInt();
      modo_stream = false;
      modo_binario = false;
      modo_stream_binario = false;
    } else {
      tempo_captura = comando.substring(segunda_virgula + 1, terceira_virgula).toInt();
      String modo = comando.substring(terceira_virgula + 1);
      modo.trim();
      modo.toUpperCase();
      modo_stream = modo == "STREAM";
      modo_binario = modo == "BIN" || modo == "BINARY" || modo == "BINARIO";
      modo_stream_binario = modo == "STREAM_BIN" || modo == "BIN_STREAM" || modo == "CONTINUO_BINARIO";
    }
  } else {
    return false;
  }

  if (taxa_amostragem < SPS_MIN || taxa_amostragem > SPS_MAX) {
    Serial.println("ERROR,SPS fora do limite");
    return false;
  }

  if ((!(modo_stream || modo_stream_binario) && tempo_captura < TEMPO_MIN) || tempo_captura > TEMPO_MAX) {
    Serial.println("ERROR,Tempo fora do limite");
    return false;
  }

  num_amostras = taxa_amostragem * tempo_captura;
  if (!(modo_stream || modo_stream_binario) && num_amostras == 0) {
    Serial.println("ERROR,Quantidade de amostras fora do limite");
    return false;
  }

  if (num_amostras > NUM_AMOSTRAS_MAX) {
    Serial.println("ERROR,Quantidade de amostras fora do limite");
    return false;
  }

  intervalo_us = 1000000UL / taxa_amostragem;
  if (intervalo_us == 0) {
    Serial.println("ERROR,Intervalo invalido");
    return false;
  }

  return true;
}

bool prepararBuffers() {
  free(amostras_corrente);
  free(amostras_tensao);
  free(tempos);
  amostras_corrente = nullptr;
  amostras_tensao = nullptr;
  tempos = nullptr;

  amostras_corrente = (uint16_t *)malloc(num_amostras * sizeof(uint16_t));
  amostras_tensao = (uint16_t *)malloc(num_amostras * sizeof(uint16_t));
  tempos = (uint32_t *)malloc(num_amostras * sizeof(uint32_t));

  if (amostras_corrente == nullptr || amostras_tensao == nullptr || tempos == nullptr) {
    free(amostras_corrente);
    free(amostras_tensao);
    free(tempos);
    amostras_corrente = nullptr;
    amostras_tensao = nullptr;
    tempos = nullptr;
    Serial.println("ERROR,Memoria insuficiente");
    return false;
  }

  return true;
}

void aguardarComando() {
  Serial.println("ESP32-S3 pronto.");
  Serial.println("Envie START ou START,SPS,TEMPO_S,MODO pela serial para capturar.");

  while (true) {
    if (Serial.available()) {
      String comando = Serial.readStringUntil('\n');
      comando.trim();

      if (comando.length() == 0) {
        continue;
      }

      Serial.print("COMANDO_RECEBIDO,");
      Serial.println(comando);

      if (configurarCaptura(comando) && (modo_stream || modo_stream_binario || prepararBuffers())) {
        return;
      }

      Serial.println("Aguardando novo comando.");
    }

    delay(10);
  }
}

void capturar() {
  uint32_t inicio = micros();
  uint32_t proxima_amostra = inicio;

  for (uint32_t i = 0; i < num_amostras; i++) {
    while ((int32_t)(micros() - proxima_amostra) < 0) {
    }

    uint32_t agora = micros();
    tempos[i] = agora - inicio;
    amostras_corrente[i] = analogRead(ADC_CORRENTE_PIN);
    amostras_tensao[i] = analogRead(ADC_TENSAO_PIN);

    proxima_amostra += intervalo_us;
  }
}

void transmitir() {
  Serial.println("BEGIN_CAPTURE");
  Serial.print("SPS,");
  Serial.println(taxa_amostragem);
  Serial.print("DURATION_S,");
  Serial.println(tempo_captura);
  Serial.print("SAMPLES,");
  Serial.println(num_amostras);
  Serial.println("MODE,BLOCK");
  Serial.println("CHANNELS,CURRENT_GPIO4,VOLTAGE_GPIO5");
  Serial.println("indice,tempo_us,adc_corrente,adc_tensao");

  for (uint32_t i = 0; i < num_amostras; i++) {
    Serial.print(i);
    Serial.print(",");
    Serial.print(tempos[i]);
    Serial.print(",");
    Serial.print(amostras_corrente[i]);
    Serial.print(",");
    Serial.println(amostras_tensao[i]);
  }

  Serial.println("END_CAPTURE");
}

void transmitirBinario() {
  Serial.println("BEGIN_CAPTURE");
  Serial.print("SPS,");
  Serial.println(taxa_amostragem);
  Serial.print("DURATION_S,");
  Serial.println(tempo_captura);
  Serial.print("SAMPLES,");
  Serial.println(num_amostras);
  Serial.println("MODE,BIN");
  Serial.println("CHANNELS,CURRENT_GPIO4,VOLTAGE_GPIO5");
  Serial.println("FORMAT,BINARY_LE_U32_U16_U16");
  Serial.println("RECORD_BYTES,8");
  Serial.println("BINARY_BEGIN");

  for (uint32_t i = 0; i < num_amostras; i++) {
    Serial.write((uint8_t *)&tempos[i], sizeof(uint32_t));
    Serial.write((uint8_t *)&amostras_corrente[i], sizeof(uint16_t));
    Serial.write((uint8_t *)&amostras_tensao[i], sizeof(uint16_t));
  }

  Serial.println();
  Serial.println("END_CAPTURE");
}

bool stopSolicitado() {
  if (!Serial.available()) {
    return false;
  }

  String comando = Serial.readStringUntil('\n');
  comando.trim();
  comando.toUpperCase();
  return comando == "STOP";
}

void capturarTransmitindo() {
  uint16_t pacote_corrente[STREAM_PACOTE_AMOSTRAS];
  uint16_t pacote_tensao[STREAM_PACOTE_AMOSTRAS];
  uint32_t pacote_tempos[STREAM_PACOTE_AMOSTRAS];

  Serial.println("BEGIN_CAPTURE");
  Serial.print("SPS,");
  Serial.println(taxa_amostragem);
  Serial.print("DURATION_S,");
  Serial.println(tempo_captura);
  Serial.print("SAMPLES,");
  if (tempo_captura == 0) {
    Serial.println("CONTINUOUS");
  } else {
    Serial.println(num_amostras);
  }
  Serial.println("MODE,STREAM");
  Serial.println("CHANNELS,CURRENT_GPIO4,VOLTAGE_GPIO5");
  Serial.println("indice,tempo_us,adc_corrente,adc_tensao");

  uint32_t inicio = micros();
  uint32_t indice = 0;

  while (tempo_captura == 0 || indice < num_amostras) {
    uint32_t restantes = tempo_captura == 0 ? STREAM_PACOTE_AMOSTRAS : num_amostras - indice;
    uint32_t tamanho_pacote = min((uint32_t)STREAM_PACOTE_AMOSTRAS, restantes);
    uint32_t proxima_amostra = micros();

    for (uint32_t j = 0; j < tamanho_pacote; j++) {
      while ((int32_t)(micros() - proxima_amostra) < 0) {
      }

      uint32_t agora = micros();
      pacote_tempos[j] = agora - inicio;
      pacote_corrente[j] = analogRead(ADC_CORRENTE_PIN);
      pacote_tensao[j] = analogRead(ADC_TENSAO_PIN);
      proxima_amostra += intervalo_us;
    }

    for (uint32_t j = 0; j < tamanho_pacote; j++) {
      Serial.print(indice + j);
      Serial.print(",");
      Serial.print(pacote_tempos[j]);
      Serial.print(",");
      Serial.print(pacote_corrente[j]);
      Serial.print(",");
      Serial.println(pacote_tensao[j]);
    }

    if (stopSolicitado()) {
      Serial.println("STOPPED");
      break;
    }

    indice += tamanho_pacote;
  }

  Serial.println("END_CAPTURE");
}

void capturarTransmitindoBinario() {
  uint16_t pacote_corrente[STREAM_PACOTE_AMOSTRAS];
  uint16_t pacote_tensao[STREAM_PACOTE_AMOSTRAS];
  uint32_t pacote_tempos[STREAM_PACOTE_AMOSTRAS];

  Serial.println("BEGIN_CAPTURE");
  Serial.print("SPS,");
  Serial.println(taxa_amostragem);
  Serial.print("DURATION_S,");
  Serial.println(tempo_captura);
  Serial.print("SAMPLES,");
  if (tempo_captura == 0) {
    Serial.println("CONTINUOUS");
  } else {
    Serial.println(num_amostras);
  }
  Serial.println("MODE,STREAM_BIN");
  Serial.println("CHANNELS,CURRENT_GPIO4,VOLTAGE_GPIO5");
  Serial.println("FORMAT,BINARY_LE_U32_U16_U16");
  Serial.println("RECORD_BYTES,8");
  Serial.println("PACKET_FORMAT,BINARY_PACKET_INDEX_COUNT");

  uint32_t inicio = micros();
  uint32_t indice = 0;

  while (tempo_captura == 0 || indice < num_amostras) {
    uint32_t restantes = tempo_captura == 0 ? STREAM_PACOTE_AMOSTRAS : num_amostras - indice;
    uint32_t tamanho_pacote = min((uint32_t)STREAM_PACOTE_AMOSTRAS, restantes);
    uint32_t proxima_amostra = micros();

    for (uint32_t j = 0; j < tamanho_pacote; j++) {
      while ((int32_t)(micros() - proxima_amostra) < 0) {
      }

      uint32_t agora = micros();
      pacote_tempos[j] = agora - inicio;
      pacote_corrente[j] = analogRead(ADC_CORRENTE_PIN);
      pacote_tensao[j] = analogRead(ADC_TENSAO_PIN);
      proxima_amostra += intervalo_us;
    }

    Serial.print("BINARY_PACKET,");
    Serial.print(indice);
    Serial.print(",");
    Serial.println(tamanho_pacote);

    for (uint32_t j = 0; j < tamanho_pacote; j++) {
      Serial.write((uint8_t *)&pacote_tempos[j], sizeof(uint32_t));
      Serial.write((uint8_t *)&pacote_corrente[j], sizeof(uint16_t));
      Serial.write((uint8_t *)&pacote_tensao[j], sizeof(uint16_t));
    }

    if (stopSolicitado()) {
      Serial.println("STOPPED");
      break;
    }

    indice += tamanho_pacote;
  }

  Serial.println("END_CAPTURE");
}

void setup() {
  Serial.begin(921600);
  Serial.setTimeout(100);

  uint32_t inicio_espera = millis();
  while (!Serial && millis() - inicio_espera < 5000) {
    delay(10);
  }

  delay(500);

  analogReadResolution(12);

  Serial.println();
  Serial.println("BOOT,ESP32-S3 SCT013 DAQ");
  Serial.println("BAUD,921600");
}

void loop() {
  aguardarComando();

  Serial.println("CAPTURANDO");
  if (modo_stream) {
    capturarTransmitindo();
    return;
  }
  if (modo_stream_binario) {
    capturarTransmitindoBinario();
    return;
  }

  capturar();
  Serial.println("TRANSMITINDO");
  if (modo_binario) {
    transmitirBinario();
  } else {
    transmitir();
  }

  free(amostras_corrente);
  free(amostras_tensao);
  free(tempos);
  amostras_corrente = nullptr;
  amostras_tensao = nullptr;
  tempos = nullptr;
}
