# ESP32-S3 SCT013 DAQ para Raspberry Pi 4

Programa de aquisicao de sinais analogicos para Raspberry Pi 4 com Raspberry Pi OS. O Raspberry executa a interface Python e conversa por USB serial com um ESP32-S3 gravado com o firmware deste repositorio.

Versao atual:

```text
1.0.3-rpi
```

## Hardware

- Raspberry Pi 4 com Raspberry Pi OS.
- ESP32-S3 N16R8 conectado ao Raspberry por USB.
- SCT013-100 para corrente no GPIO4 do ESP32-S3.
- ZMPT101B para tensao no GPIO5 do ESP32-S3.
- Firmware do ESP32-S3 em `arduino/esp32_s3_sct013_capture/esp32_s3_sct013_capture.ino`.

Porta serial padrao no Raspberry:

```text
/dev/ttyACM0
```

Se o dispositivo aparecer com outro nome, confira com:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

## Instalar no Raspberry Pi OS

Na pasta do projeto:

```bash
chmod +x install_raspberry_pi.sh run_gui.sh run_cli_capture.sh
./install_raspberry_pi.sh
```

O instalador cria um ambiente virtual em `.venv`, instala as dependencias Python e prepara as pastas de dados do usuario.

## Abrir a Interface

```bash
./run_gui.sh
```

A interface usa:

- porta serial configuravel;
- baud padrao `921600`;
- SPS configuravel;
- tempo de captura configuravel;
- modos `Bloco`, `Binario`, `Continuo` e `Continuo Binario`;
- graficos no tempo e FFT;
- visualizacao corrente + tensao;
- calibracao RMS de corrente e tensao;
- exportacao da ultima captura em CSV.

As configuracoes e calibracoes ficam em:

```text
~/.config/esp32_s3_daq/calibracao_daq.json
```

Os CSVs sugeridos ficam em:

```text
~/Documents/esp32_s3_daq/
```

## Capturar pelo Terminal

Modo binario, recomendado para taxas maiores:

```bash
./run_cli_capture.sh --porta /dev/ttyACM0 --baud 921600 --sps 2000 --tempo 5 --modo binario --plot
```

Modo texto:

```bash
./run_cli_capture.sh --porta /dev/ttyACM0 --modo texto
```

Modo continuo binario:

```bash
./run_cli_capture.sh --porta /dev/ttyACM0 --sps 2000 --tempo 5 --modo continuo-binario
```

## Modos de Captura

| Modo na interface | Modo no firmware | Fluxo | Formato |
| --- | --- | --- | --- |
| `Bloco` | `BLOCK` | captura tudo na RAM e envia depois | CSV/texto |
| `Binario` | `BIN` | captura tudo na RAM e envia depois | binario |
| `Continuo` | `STREAM` | captura pacote e envia pacote | CSV/texto |
| `Continuo Binario` | `STREAM_BIN` | captura pacote e envia pacote | binario |

Para alta taxa de amostragem, prefira `Binario`. Para visualizacao quase em tempo real, teste `Continuo Binario`.

## Formato dos Dados

CSV:

```csv
indice,tempo_us,adc_corrente,adc_tensao
0,0,1902,2048
1,500,1904,2050
```

Registro binario:

```text
tempo_us      uint32  4 bytes
adc_corrente  uint16  2 bytes
adc_tensao    uint16  2 bytes
```

Total:

```text
8 bytes por amostra
```

## Firmware do ESP32-S3

O Raspberry Pi executa apenas o programa Python. O ESP32-S3 precisa estar previamente gravado com o firmware DAQ.

Configuracao usada no ESP32-S3:

```text
USB CDC On Boot: Enabled
USB Mode: Hardware CDC and JTAG
Upload Mode: UART0 / Hardware CDC
Flash Size: 16MB (128Mb)
PSRAM: OPI PSRAM
Upload Speed: 921600
```

O arquivo `arduino/esp32_s3_sct013_capture/sketch.yaml` ja usa `/dev/ttyACM0` como porta padrao para ambientes Linux.

## Diagnostico Rapido

Se nao capturar:

1. Confira se o ESP32-S3 aparece em `/dev/ttyACM0` ou `/dev/ttyUSB0`.
2. Feche qualquer outro programa usando a serial.
3. Confira se o firmware DAQ foi gravado no ESP32-S3.
4. Confira se o baud esta em `921600`.
5. No Raspberry, confira permissao de serial com `groups`; o usuario normalmente deve estar no grupo `dialout`.

Se precisar adicionar o usuario ao grupo serial:

```bash
sudo usermod -a -G dialout "$USER"
```

Depois reinicie a sessao do Raspberry.

## Estrutura Atual

```text
arduino/esp32_s3_sct013_capture/esp32_s3_sct013_capture.ino
arduino/esp32_s3_sct013_capture/sketch.yaml
python/daq_gui.py
python/captura_esp32.py
python/requirements.txt
install_raspberry_pi.sh
run_gui.sh
run_cli_capture.sh
README.md
```

## Proximos Caminhos

- Testar estabilidade real no Raspberry Pi 4.
- Medir lacunas com `tempo_us` no modo `Continuo Binario`.
- Reduzir atualizacoes de grafico em capturas longas.
- Avaliar buffer duplo, ADC continuo/DMA ou ESP-IDF para aquisicao continua real.
- Avaliar ADC externo ADS131M04.
