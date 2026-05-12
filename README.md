# ESP32-S3 SCT013 DAQ inicial

Este pacote tem duas partes:

- `arduino/esp32_s3_sct013_capture/esp32_s3_sct013_capture.ino`: codigo para gravar no ESP32-S3 pela Arduino IDE.
- `python/captura_esp32.py`: programa para rodar neste computador, capturar os dados via USB serial, salvar CSV e fazer analise basica.
- `python/daq_gui.py`: interface grafica com porta serial, Inicio, Stop, grafico e resumo da captura.

## 1. Gravar o ESP32-S3

1. Abra a Arduino IDE.
2. Abra o arquivo:
   `esp32_s3_daq/arduino/esp32_s3_sct013_capture/esp32_s3_sct013_capture.ino`
3. Selecione a placa `ESP32S3 Dev Module`.
4. Use as configuracoes que ja funcionaram:
   - USB CDC On Boot: `Enabled`
   - Flash Size: `16MB`
   - PSRAM: `OPI PSRAM`
   - Upload Mode: `UART0 / Hardware CDC`
   - Upload Speed: `921600`
   - USB Mode: `Hardware CDC and JTAG`
5. Selecione a porta, por exemplo `COM10`.
6. Clique em Upload.

## 2. Preparar o Python no computador

No terminal, entre na pasta do programa:

```powershell
cd "C:\Antigravity Files\studio\esp32_s3_daq\python"
```

Instale as bibliotecas:

```powershell
py -m pip install -r requirements.txt
```

## 3. Capturar dados

Feche o Serial Monitor da Arduino IDE antes de rodar o Python. A porta serial nao pode ser usada por dois programas ao mesmo tempo.

Rode:

```powershell
py captura_esp32.py --porta COM10 --csv captura_esp32.csv --plot
```

Para escolher taxa e tempo:

```powershell
py captura_esp32.py --porta COM10 --sps 2000 --tempo 5 --csv captura_esp32.csv --plot
```

O programa vai:

1. abrir a serial;
2. enviar `START` para o ESP32-S3;
3. esperar a captura terminar;
4. salvar `captura_esp32.csv`;
5. calcular offset medio;
6. calcular RMS em contagens ADC;
7. estimar o SPS real;
8. listar os maiores picos de FFT;
9. mostrar um grafico se `--plot` for usado.

## 4. Resultado esperado

O CSV tera este formato:

```csv
indice,tempo_us,adc
0,0,1912
1,500,1915
2,1000,1921
```

No terminal, voce deve ver um resumo parecido com:

```text
Resumo da captura
-----------------
Amostras: 10000
Duracao: 4.999500 s
SPS real aproximado: 2000.00
ADC min/max: 1800 / 2050
Offset medio: 1912.34
RMS em contagens ADC: 42.10
```

## 5. Observacoes

- O valor RMS inicial esta em contagens ADC, ainda nao em amperes.
- Para converter em amperes, ainda sera necessario calibrar o circuito.
- A FFT depende do SPS real, por isso o Python calcula o SPS usando `tempo_us`.
- Para testes com seguranca, desligue a USB antes de alterar ligacoes na protoboard.
- Limites atuais: `100` a `20000` SPS, `1` a `60` segundos e no maximo `120000` amostras por captura.

## 6. Rodar a interface grafica

Feche o Serial Monitor da Arduino IDE antes de abrir a interface.

No terminal:

```powershell
cd "C:\Antigravity Files\studio\esp32_s3_daq\python"
py -m pip install -r requirements.txt
py daq_gui.py
```

Na janela:

1. selecione a porta, por exemplo `COM10`;
2. informe `SPS`, por exemplo `2000`;
3. informe `Tempo (s)`, por exemplo `5`;
4. escolha o modo:
   - `Bloco`: captura tudo na RAM do ESP32-S3 e envia no final;
   - `Continuo`: captura pequenos pacotes e envia durante a aquisicao;
5. confirme o arquivo CSV de saida;
6. clique em `Iniciar`;
7. aguarde a captura e a transmissao;
8. veja o grafico e o resumo.

O botao `Stop` cancela a leitura no computador. No modo `Continuo`, o programa tambem envia `STOP` para o ESP32-S3 parar no proximo pacote. No modo `Bloco`, o ESP32-S3 pode terminar a captura em RAM antes de aceitar outro comando.

No modo `Continuo`, use `Tempo (s) = 0` para capturar sem limite de tempo ate clicar em `Stop`.

## 7. Gerar executavel

No terminal:

```powershell
cd "C:\Antigravity Files\studio\esp32_s3_daq\python"
.\build_exe.bat
```

O executavel sera criado em:

```text
C:\Antigravity Files\studio\esp32_s3_daq\python\dist\ESP32_S3_DAQ.exe
```

Se o projeto estiver na pasta do TCC, use o mesmo comando dentro de:

```text
C:\Users\andre\Documents\tcc\esp32_s3_daq\python
```
