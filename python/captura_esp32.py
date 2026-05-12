import argparse
import csv
import math
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


def capturar(ser: serial.Serial, arquivo_csv: Path, sps: int, tempo_s: int) -> list[tuple[int, int, int]]:
    comando = f"START,{sps},{tempo_s}\n"
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

            if len(partes) == 2 and not cabecalho_encontrado:
                metadados[partes[0]] = partes[1]
                continue

            if linha == "indice,tempo_us,adc":
                cabecalho_encontrado = True
                writer.writerow(["indice", "tempo_us", "adc"])
                continue

            if cabecalho_encontrado and len(partes) == 3:
                indice = int(partes[0])
                tempo_us = int(partes[1])
                adc = int(partes[2])
                amostras.append((indice, tempo_us, adc))
                writer.writerow([indice, tempo_us, adc])

    print(f"CSV salvo em: {arquivo_csv}")
    if metadados:
        print("Metadados:", metadados)

    return amostras


def analisar(amostras: list[tuple[int, int, int]]) -> None:
    if not amostras:
        print("Nenhuma amostra recebida.")
        return

    tempos_us = [item[1] for item in amostras]
    adc = [item[2] for item in amostras]

    offset = sum(adc) / len(adc)
    sinal = [x - offset for x in adc]
    rms_adc = math.sqrt(sum(x * x for x in sinal) / len(sinal))

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


def plotar(amostras: list[tuple[int, int, int]]) -> None:
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
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--sps", type=int, default=2000, help="Amostras por segundo")
    parser.add_argument("--tempo", type=int, default=5, help="Tempo de captura em segundos")
    parser.add_argument("--csv", default="captura_esp32.csv", help="Arquivo CSV de saida")
    parser.add_argument("--plot", action="store_true", help="Mostra grafico ao final")
    args = parser.parse_args()

    arquivo_csv = Path(args.csv)

    if not 100 <= args.sps <= 20000:
        raise SystemExit("Use --sps entre 100 e 20000.")

    if not 1 <= args.tempo <= 60:
        raise SystemExit("Use --tempo entre 1 e 60 segundos.")

    if args.sps * args.tempo > 120000:
        raise SystemExit("Use no maximo 120000 amostras por captura.")

    with abrir_serial(args.porta, args.baud) as ser:
        amostras = capturar(ser, arquivo_csv, args.sps, args.tempo)

    analisar(amostras)

    if args.plot:
        plotar(amostras)


if __name__ == "__main__":
    main()
