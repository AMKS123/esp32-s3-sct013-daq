# Guia para recriar o software do projeto

Este guia descreve como recriar o ambiente em outro computador a partir do repositorio GitHub.

Repositorio:

```text
https://github.com/AMKS123/esp32-s3-sct013-daq.git
```

## 1. Baixar o projeto

Instale o Git, se ainda nao estiver instalado:

```text
https://git-scm.com/download/win
```

Depois, no PowerShell:

```powershell
cd C:\
mkdir Codex
cd C:\Codex
git clone https://github.com/AMKS123/esp32-s3-sct013-daq.git
cd esp32-s3-sct013-daq
```

Neste guia, `C:\Codex\esp32-s3-sct013-daq` representa uma instalacao nova feita por `git clone`.

No computador atual do projeto, a pasta usada e:

```text
C:\Codex\tcc\esp32_s3_daq
```

## 2. Estrutura do projeto

```text
esp32-s3-sct013-daq/
  arduino/
    esp32_s3_sct013_capture/
      esp32_s3_sct013_capture.ino

  python/
    daq_gui.py
    captura_esp32.py
    requirements.txt
    build_exe.bat

  README.md
  GUIA_RECRIAR_SOFTWARE.md
```

## 3. Instalar Python

Baixe e instale o Python para Windows:

```text
https://www.python.org/downloads/windows/
```

Durante a instalacao, marque:

```text
Add python.exe to PATH
```

Feche e abra o PowerShell novamente. Teste:

```powershell
py --version
```

Se `py` nao funcionar, teste:

```powershell
python --version
```

## 4. Instalar dependencias Python

Entre na pasta Python do projeto:

```powershell
cd "C:\Codex\esp32-s3-sct013-daq\python"
```

Instale as dependencias:

```powershell
py -m pip install -r requirements.txt
```

Se `py` nao funcionar:

```powershell
python -m pip install -r requirements.txt
```

## 5. Rodar a interface grafica

Com o ESP32-S3 conectado e o firmware ja gravado:

```powershell
cd "C:\Codex\esp32-s3-sct013-daq\python"
py daq_gui.py
```

Na interface:

1. selecione a porta serial, por exemplo `COM10`;
2. use `Baud = 921600`;
3. defina `SPS`;
4. defina `Tempo (s)`;
5. escolha `Modo`:
   - `Bloco`: captura em RAM e envia ao final;
   - `Continuo`: envia pacotes durante a captura;
6. clique em `Iniciar`;
7. clique em `CSV` depois da captura para salvar a ultima captura.

## 6. Gerar o executavel

No PowerShell:

```powershell
cd "C:\Codex\esp32-s3-sct013-daq\python"
.\build_exe.bat
```

O executavel sera criado em:

```text
C:\Codex\esp32-s3-sct013-daq\python\dist\ESP32_S3_DAQ.exe
```

Observacao: as pastas `build/` e `dist/` nao ficam no GitHub. Elas sao recriadas pelo `build_exe.bat`.

## 7. Instalar Arduino IDE

Baixe e instale a Arduino IDE:

```text
https://www.arduino.cc/en/software
```

Abra a Arduino IDE e instale o suporte ao ESP32:

1. Abra `File > Preferences`.
2. Em `Additional boards manager URLs`, adicione:

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

3. Abra `Tools > Board > Boards Manager`.
4. Pesquise por `esp32`.
5. Instale o pacote da Espressif.

## 8. Gravar o firmware no ESP32-S3

Abra na Arduino IDE:

```text
arduino/esp32_s3_sct013_capture/esp32_s3_sct013_capture.ino
```

Selecione:

```text
Board: ESP32S3 Dev Module
```

Configuracoes usadas:

```text
USB CDC On Boot: Enabled
Flash Size: 16MB
PSRAM: OPI PSRAM
Upload Mode: UART0 / Hardware CDC
Upload Speed: 921600
USB Mode: Hardware CDC and JTAG
```

Selecione a porta serial, por exemplo:

```text
COM10
```

Clique em `Upload`.

## 9. Protocolo serial usado

O programa Python envia comandos ao ESP32-S3:

```text
START,SPS,TEMPO_S,BLOCK
START,SPS,TEMPO_S,STREAM
STOP
```

Exemplos:

```text
START,2000,5,BLOCK
START,2000,0,STREAM
```

O ESP32-S3 responde em CSV:

```csv
indice,tempo_us,adc
0,0,1905
1,500,1907
2,1000,1902
```

## 10. Calibracao de corrente

O ADC gera valores digitais de `0` a `4095`.

A interface calcula:

```text
offset = media(adc)
ADC - offset = adc - offset
RMS_ADC = sqrt(media((adc - offset)^2))
```

Para calibrar:

1. faca uma captura com uma carga conhecida;
2. meca a corrente RMS com um multimetro, de preferencia True RMS;
3. digite a corrente no campo `I ref RMS (A)`;
4. clique em `Calibrar`.

O fator calculado e:

```text
fator = corrente_RMS_referencia / RMS_ADC
```

Depois:

```text
corrente instantanea estimada = (adc - offset) * fator
```

## 11. Visualizacoes

A interface permite:

```text
ADC bruto
ADC - offset
Corrente (A)
```

E tambem:

```text
Tempo
FFT
Tempo + FFT
```

A FFT usa o SPS real calculado pelos tempos recebidos, nao apenas o SPS solicitado.

## 12. Arquivos que nao vao para o GitHub

O `.gitignore` deixa fora:

```text
python/build/
python/dist/
python/*.spec
python/*.csv
__pycache__/
*.pyc
```

Esses arquivos sao locais, grandes ou gerados automaticamente.

## 13. Atualizar o GitHub depois de mudancas

Depois de editar o projeto:

```powershell
cd "C:\Codex\esp32-s3-sct013-daq"
git status
git add .
git commit -m "Descricao da mudanca"
git push
```
