import argparse
import csv
import math
import struct
import time
from pathlib import Path

import serial


def abrir_serial(porta: str, baud: int) -> serial.Serial:
    ser = serial.Serial(porta, baud, timeout=2)
    time.sleep(2)
    ser.reset_input_buffer()
    return ser


def ler_linha(ser: serial.Serial) -> str:
    return ser.readline().decode("utf-8", errors="ignore").strip()


def ler_bytes_exatos(ser: serial.Serial, total_bytes: int) -> bytes:
    partes = []
    recebidos = 0
    bytes_por_segundo = max(ser.baudrate / 10, 1)
    limite = time.monotonic() + max(5.0, total_bytes / bytes_por_segundo + 5.0)

    while recebidos < total_bytes:
        pedaco = ser.read(total_bytes - recebidos)
        if pedaco:
            partes.append(pedaco)
            recebidos += len(pedaco)
            continue

        if time.monotonic() > limite:
            raise TimeoutError(f"Timeout recebendo dados binarios: {recebidos} de {total_bytes} bytes.")

    return b"".join(partes)


def capturar(ser: serial.Serial, arquivo_csv: Path, sps: int, tempo_s: int, modo: str) -> list[tuple[int, ...]]:
    if modo == "binario":
        modo_serial = "BIN"
    elif modo == "continuo-binario":
        modo_serial = "STREAM_BIN"
    else:
        modo_serial = "BLOCK"
    comando = f"START,{sps},{tempo_s},{modo_serial}\n"
    print(f"Enviando {comando.strip()} para o ESP32-S3...")
    ser.write(comando.encode("ascii"))

    print("Aguardando inicio da captura...")
    while True:
        linha = ler_linha(ser)
        if linha:
            print(linha)
        if linha == "BEGIN_CAPTURE":
            break

    metadados = {}
    amostras = []
    cabecalho_encontrado = False

    with arquivo_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        while True:
            linha = ler_linha(ser)

            if not linha:
                continue

            if linha == "END_CAPTURE":
                break

            partes = linha.split(",")

            if len(partes) == 3 and partes[0] == "BINARY_PACKET":
                indice_inicial = int(partes[1])
                quantidade = int(partes[2])
                pacote = struct.Struct("<IHH")

                if not cabecalho_encontrado:
                    cabecalho_encontrado = True
                    writer.writerow(["indice", "tempo_us", "adc_corrente", "adc_tensao"])

                for posicao in range(quantidade):
                    dados = ler_bytes_exatos(ser, pacote.size)
                    tempo_us, adc_corrente, adc_tensao = pacote.unpack(dados)
                    amostra = (indice_inicial + posicao, tempo_us, adc_corrente, adc_tensao)
                    amostras.append(amostra)
                    writer.writerow(amostra)

                continue

            if len(partes) == 2 and not cabecalho_encontrado:
                metadados[partes[0]] = partes[1]
                continue

            if linha == "BINARY_BEGIN":
                total_amostras = int(metadados["SAMPLES"])
                record_bytes = int(metadados.get("RECORD_BYTES", "8"))
                if record_bytes != 8:
                    raise RuntimeError(f"Formato binario nao suportado: {record_bytes} bytes por registro.")

                writer.writerow(["indice", "tempo_us", "adc_corrente", "adc_tensao"])
                pacote = struct.Struct("<IHH")
                print(f"Recebendo {total_amostras} amostras em binario...")

                for indice in range(total_amostras):
                    dados = ler_bytes_exatos(ser, record_bytes)
                    tempo_us, adc_corrente, adc_tensao = pacote.unpack(dados)
                    amostra = (indice, tempo_us, adc_corrente, adc_tensao)
                    amostras.append(amostra)
                    writer.writerow(amostra)

                continue

            if linha in ("indice,tempo_us,adc", "indice,tempo_us,adc_corrente,adc_tensao"):
                cabecalho_encontrado = True
                writer.writerow(["indice", "tempo_us", "adc_corrente", "adc_tensao"])
                continue

            if cabecalho_encontrado and len(partes) in (3, 4):
                indice = int(partes[0])
                tempo_us = int(partes[1])
                adc_corrente = int(partes[2])
                adc_tensao = int(partes[3]) if len(partes) == 4 else adc_corrente
                amostras.append((indice, tempo_us, adc_corrente, adc_tensao))
                writer.writerow([indice, tempo_us, adc_corrente, adc_tensao])

    print(f"CSV salvo em: {arquivo_csv}")
    if metadados:
        print("Metadados:", metadados)

    return amostras


def analisar(amostras: list[tuple[int, ...]]) -> None:
    if not amostras:
        print("Nenhuma amostra recebida.")
        return

    tempos_us = [item[1] for item in amostras]
    adc = [item[2] for item in amostras]
    adc_tensao = [item[3] if len(item) > 3 else item[2] for item in amostras]

    offset = sum(adc) / len(adc)
    sinal = [x - offset for x in adc]
    rms_adc = math.sqrt(sum(x * x for x in sinal) / len(sinal))
    offset_tensao = sum(adc_tensao) / len(adc_tensao)
    sinal_tensao = [x - offset_tensao for x in adc_tensao]
    rms_tensao_adc = math.sqrt(sum(x * x for x in sinal_tensao) / len(sinal_tensao))

    duracao_s = (tempos_us[-1] - tempos_us[0]) / 1_000_000
    sps_real = (len(amostras) - 1) / duracao_s if duracao_s > 0 else 0
    adc_min = min(adc)
    adc_max = max(adc)

    print()
    print("Resumo da captura")
    print("-----------------")
    print(f"Amostras: {len(amostras)}")
    print(f"Duracao: {duracao_s:.6f} s")
    print(f"SPS real aproximado: {sps_real:.2f}")
    print(f"ADC min/max: {adc_min} / {adc_max}")
    print(f"Offset medio: {offset:.2f}")
    print(f"RMS em contagens ADC: {rms_adc:.2f}")
    print(f"ADC tensao min/max: {min(adc_tensao)} / {max(adc_tensao)}")
    print(f"Offset tensao medio: {offset_tensao:.2f}")
    print(f"RMS tensao em contagens ADC: {rms_tensao_adc:.2f}")

    try:
        import numpy as np

        sinal_np = np.array(sinal)
        janela = np.hanning(len(sinal_np))
        espectro = np.fft.rfft(sinal_np * janela)
        frequencias = np.fft.rfftfreq(len(sinal_np), d=1 / sps_real)
        magnitudes = np.abs(espectro)

        if len(magnitudes) > 1:
            magnitudes[0] = 0
            indices = np.argsort(magnitudes)[-8:][::-1]

            print()
            print("Picos principais da FFT")
            print("-----------------------")
            for i in indices:
                print(f"{frequencias[i]:8.2f} Hz  magnitude {magnitudes[i]:.2f}")
    except ImportError:
        print()
        print("Instale numpy para calcular FFT: py -m pip install numpy")


def plotar(amostras: list[tuple[int, ...]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Instale matplotlib para plotar: py -m pip install matplotlib")
        return

    tempos_s = [item[1] / 1_000_000 for item in amostras]
    adc = [item[2] for item in amostras]
    offset = sum(adc) / len(adc)
    sinal = [x - offset for x in adc]

    plt.figure()
    plt.plot(tempos_s, sinal)
    plt.xlabel("Tempo (s)")
    plt.ylabel("ADC - offset")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Captura dados do ESP32-S3 via serial.")
    parser.add_argument("--porta", default="COM10", help="Porta serial. Exemplo: COM10")
    parser.add_argument("--baud", type=int, default=921600, help="Baud rate")
    parser.add_argument("--sps", type=int, default=2000, help="Amostras por segundo")
    parser.add_argument("--tempo", type=int, default=5, help="Tempo de captura em segundos")
    parser.add_argument(
        "--modo",
        choices=["binario", "texto", "continuo-binario"],
        default="binario",
        help="Formato de transmissao",
    )
    parser.add_argument("--csv", default="captura_esp32.csv", help="Arquivo CSV de saida")
    parser.add_argument("--plot", action="store_true", help="Mostra grafico ao final")
    args = parser.parse_args()

    arquivo_csv = Path(args.csv)

    if not 100 <= args.sps <= 20000:
        raise SystemExit("Use --sps entre 100 e 20000.")

    if args.modo == "continuo-binario":
        if not 0 <= args.tempo <= 60:
            raise SystemExit("Use --tempo entre 0 e 60 segundos no modo continuo-binario.")
    elif not 1 <= args.tempo <= 60:
        raise SystemExit("Use --tempo entre 1 e 60 segundos.")

    if args.sps * args.tempo > 120000:
        raise SystemExit("Use no maximo 120000 amostras por captura.")

    with abrir_serial(args.porta, args.baud) as ser:
        amostras = capturar(ser, arquivo_csv, args.sps, args.tempo, args.modo)

    analisar(amostras)

    if args.plot:
        plotar(amostras)


if __name__ == "__main__":
    main()
