# Configuracao da Arduino IDE para ESP32-S3

Use esta lista antes de fazer upload do firmware `esp32_s3_sct013_capture.ino`.

## Placa

- Board: `ESP32S3 Dev Module`
- Port: `COM10` ou a porta que aparecer para o ESP32-S3

## Tools

As opcoes mais importantes para este projeto sao:

| Opcao | Valor |
| --- | --- |
| USB CDC On Boot | `Enabled` |
| USB Mode | `Hardware CDC and JTAG` |
| Upload Mode | `UART0 / Hardware CDC` |
| Flash Size | `16MB (128Mb)` |
| PSRAM | `OPI PSRAM` |
| Upload Speed | `921600` |

## Monitor Serial

- Baud: `921600`
- Final de linha: `Nova linha`

Depois de abrir o Monitor Serial, aperte `RESET/EN` no ESP32-S3. A saida esperada e:

```text
BOOT,ESP32-S3 SCT013 DAQ
BAUD,921600
ESP32-S3 pronto.
Envie START ou START,SPS,TEMPO_S,MODO pela serial para capturar.
```

Teste manual:

```text
START,2000,5,BLOCK
```

Resposta esperada:

```text
COMANDO_RECEBIDO,START,2000,5,BLOCK
CAPTURANDO
TRANSMITINDO
BEGIN_CAPTURE
...
END_CAPTURE
```

## Sintoma comum

Se `USB CDC On Boot` ficar `Disabled`, o Monitor Serial pode abrir, mas o firmware nao responde pela USB como esperado. Neste caso:

1. mude `USB CDC On Boot` para `Enabled`;
2. faca upload novamente;
3. feche e abra o Monitor Serial;
4. aperte `RESET/EN`.
