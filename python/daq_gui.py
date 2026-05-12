import csv
import math
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import serial
from serial.tools import list_ports

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


class DaqApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("ESP32-S3 SCT013 DAQ")
        self.geometry("1100x720")
        self.minsize(920, 620)

        self.eventos: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.ser: serial.Serial | None = None
        self.amostras: list[tuple[int, int, int]] = []
        self.modo_atual = "BLOCK"
        self.sps_atual = 2000
        self.amostras_esperadas: int | None = None

        self.porta_var = tk.StringVar(value="COM10")
        self.baud_var = tk.StringVar(value="921600")
        self.sps_var = tk.StringVar(value="2000")
        self.tempo_var = tk.StringVar(value="5")
        self.modo_var = tk.StringVar(value="Bloco")
        self.csv_var = tk.StringVar(value=str(Path.cwd() / "captura_esp32_gui.csv"))
        self.x_min_var = tk.StringVar()
        self.x_max_var = tk.StringVar()
        self.y_min_var = tk.StringVar()
        self.y_max_var = tk.StringVar()
        self.grafico_var = tk.StringVar(value="ADC - offset")
        self.visualizacao_var = tk.StringVar(value="Tempo")
        self.corrente_ref_var = tk.StringVar()
        self.fator_a_por_adc = 0.0
        self.status_var = tk.StringVar(value="Pronto")
        self.resumo_var = tk.StringVar(value="Sem captura ainda.")

        self._criar_layout()
        self._atualizar_portas()
        self.after(120, self._processar_eventos)

    def _criar_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        barra = ttk.Frame(self, padding=10)
        barra.grid(row=0, column=0, sticky="ew")
        barra.columnconfigure(6, weight=1)

        ttk.Label(barra, text="Porta").grid(row=0, column=0, padx=(0, 6))
        self.porta_combo = ttk.Combobox(barra, textvariable=self.porta_var, width=12)
        self.porta_combo.grid(row=0, column=1, padx=(0, 10))

        ttk.Button(barra, text="Atualizar", command=self._atualizar_portas).grid(row=0, column=2, padx=(0, 16))

        ttk.Label(barra, text="Baud").grid(row=0, column=3, padx=(0, 6))
        ttk.Entry(barra, textvariable=self.baud_var, width=10).grid(row=0, column=4, padx=(0, 16))

        ttk.Label(barra, text="SPS").grid(row=0, column=5, padx=(0, 6))
        ttk.Entry(barra, textvariable=self.sps_var, width=8).grid(row=0, column=6, padx=(0, 12))

        ttk.Label(barra, text="Tempo (s)").grid(row=0, column=7, padx=(0, 6))
        ttk.Entry(barra, textvariable=self.tempo_var, width=8).grid(row=0, column=8, padx=(0, 16))

        ttk.Button(barra, text="CSV", command=self._salvar_ultima_captura).grid(row=1, column=0, padx=(0, 6), pady=(8, 0))
        ttk.Entry(barra, textvariable=self.csv_var).grid(row=1, column=1, columnspan=5, sticky="ew", padx=(0, 16), pady=(8, 0))

        ttk.Label(barra, text="Modo").grid(row=1, column=6, padx=(0, 6), pady=(8, 0))
        self.modo_combo = ttk.Combobox(barra, textvariable=self.modo_var, width=10, state="readonly", values=["Bloco", "Continuo"])
        self.modo_combo.grid(row=1, column=7, padx=(0, 12), pady=(8, 0))

        self.iniciar_btn = ttk.Button(barra, text="Iniciar", command=self.iniciar)
        self.iniciar_btn.grid(row=1, column=8, padx=(0, 8), pady=(8, 0))

        self.parar_btn = ttk.Button(barra, text="Stop", command=self.parar, state="disabled")
        self.parar_btn.grid(row=1, column=9, pady=(8, 0))

        corpo = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        corpo.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        grafico_frame = ttk.Frame(corpo)
        grafico_frame.rowconfigure(1, weight=1)
        grafico_frame.columnconfigure(0, weight=1)
        corpo.add(grafico_frame, weight=4)

        escala_frame = ttk.Frame(grafico_frame, padding=(0, 0, 0, 8))
        escala_frame.grid(row=0, column=0, sticky="ew")
        escala_frame.columnconfigure(11, weight=1)

        ttk.Label(escala_frame, text="X min").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(escala_frame, textvariable=self.x_min_var, width=8).grid(row=0, column=1, padx=(0, 8))
        ttk.Label(escala_frame, text="X max").grid(row=0, column=2, padx=(0, 4))
        ttk.Entry(escala_frame, textvariable=self.x_max_var, width=8).grid(row=0, column=3, padx=(0, 12))

        ttk.Label(escala_frame, text="Y min").grid(row=0, column=4, padx=(0, 4))
        ttk.Entry(escala_frame, textvariable=self.y_min_var, width=8).grid(row=0, column=5, padx=(0, 8))
        ttk.Label(escala_frame, text="Y max").grid(row=0, column=6, padx=(0, 4))
        ttk.Entry(escala_frame, textvariable=self.y_max_var, width=8).grid(row=0, column=7, padx=(0, 12))

        ttk.Button(escala_frame, text="Aplicar escala", command=self._aplicar_escala).grid(row=0, column=8, padx=(0, 8))
        ttk.Button(escala_frame, text="Auto", command=self._escala_auto).grid(row=0, column=9)

        ttk.Label(escala_frame, text="Grafico").grid(row=0, column=10, padx=(12, 4))
        self.grafico_combo = ttk.Combobox(
            escala_frame,
            textvariable=self.grafico_var,
            width=14,
            state="readonly",
            values=["ADC bruto", "ADC - offset", "Corrente (A)"],
        )
        self.grafico_combo.grid(row=0, column=11, padx=(0, 8))
        self.grafico_combo.bind("<<ComboboxSelected>>", self._trocar_modo_grafico)

        ttk.Label(escala_frame, text="Visualizacao").grid(row=0, column=12, padx=(12, 4))
        self.visualizacao_combo = ttk.Combobox(
            escala_frame,
            textvariable=self.visualizacao_var,
            width=12,
            state="readonly",
            values=["Tempo", "FFT", "Tempo + FFT"],
        )
        self.visualizacao_combo.grid(row=0, column=13, padx=(0, 8))
        self.visualizacao_combo.bind("<<ComboboxSelected>>", lambda _event: self._atualizar_grafico())

        ttk.Label(escala_frame, text="I ref RMS (A)").grid(row=1, column=0, padx=(0, 4), pady=(8, 0))
        ttk.Entry(escala_frame, textvariable=self.corrente_ref_var, width=10).grid(row=1, column=1, padx=(0, 8), pady=(8, 0))
        ttk.Button(escala_frame, text="Calibrar", command=self._calibrar_corrente).grid(row=1, column=2, padx=(0, 8), pady=(8, 0))
        ttk.Button(escala_frame, text="Limpar calib.", command=self._limpar_calibracao).grid(row=1, column=3, padx=(0, 8), pady=(8, 0))

        self.fig = Figure(figsize=(7, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Sinal capturado")
        self.ax.set_xlabel("Tempo (s)")
        self.ax.set_ylabel("ADC - offset")
        self.ax.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=grafico_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        self.toolbar = NavigationToolbar2Tk(self.canvas, grafico_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=2, column=0, sticky="ew")

        lateral = ttk.Frame(corpo, padding=10)
        lateral.columnconfigure(0, weight=1)
        corpo.add(lateral, weight=1)

        ttk.Label(lateral, text="Status").grid(row=0, column=0, sticky="w")
        ttk.Label(lateral, textvariable=self.status_var, wraplength=260).grid(row=1, column=0, sticky="ew", pady=(2, 16))

        ttk.Label(lateral, text="Resumo").grid(row=2, column=0, sticky="w")
        ttk.Label(lateral, textvariable=self.resumo_var, justify="left", wraplength=260).grid(row=3, column=0, sticky="ew", pady=(2, 16))

        ttk.Label(lateral, text="Log").grid(row=4, column=0, sticky="w")
        self.log = tk.Text(lateral, height=18, width=34, state="disabled")
        self.log.grid(row=5, column=0, sticky="nsew", pady=(2, 0))
        lateral.rowconfigure(5, weight=1)

    def _atualizar_portas(self) -> None:
        portas = [porta.device for porta in list_ports.comports()]
        self.porta_combo["values"] = portas
        if portas and self.porta_var.get() not in portas:
            self.porta_var.set(portas[0])

    def _salvar_ultima_captura(self) -> None:
        if not self.amostras:
            messagebox.showerror("Sem captura", "Nao ha captura para salvar ainda.")
            return

        caminho = filedialog.asksaveasfilename(
            title="Salvar ultima captura como CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
            initialfile=Path(self.csv_var.get()).name,
        )
        if caminho:
            self._exportar_csv(Path(caminho))
            self.csv_var.set(caminho)
            self.status_var.set(f"CSV salvo: {caminho}")
            self._log(f"CSV salvo: {caminho}")

    def _exportar_csv(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with caminho.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["indice", "tempo_us", "adc"])
            writer.writerows(self.amostras)

    def iniciar(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        try:
            baud = int(self.baud_var.get())
            sps = int(self.sps_var.get())
            tempo_s = int(self.tempo_var.get())
        except ValueError:
            messagebox.showerror("Valor invalido", "Informe baud, SPS e tempo como numeros inteiros.")
            return

        if not 100 <= sps <= 20000:
            messagebox.showerror("SPS invalido", "Use SPS entre 100 e 20000.")
            return

        modo = "STREAM" if self.modo_var.get() == "Continuo" else "BLOCK"

        if modo == "STREAM":
            tempo_valido = 0 <= tempo_s <= 60
            mensagem_tempo = "Use tempo entre 0 e 60 segundos. No modo Continuo, 0 roda ate clicar Stop."
        else:
            tempo_valido = 1 <= tempo_s <= 60
            mensagem_tempo = "Use tempo entre 1 e 60 segundos no modo Bloco."

        if not tempo_valido:
            messagebox.showerror("Tempo invalido", mensagem_tempo)
            return

        if tempo_s > 0 and sps * tempo_s > 120000:
            messagebox.showerror("Captura grande demais", "Use no maximo 120000 amostras por captura.")
            return

        self.amostras.clear()
        self.modo_atual = modo
        self.sps_atual = sps
        self.amostras_esperadas = None
        self.stop_event.clear()
        self._limpar_grafico()
        self._set_rodando(True)

        porta = self.porta_var.get().strip()
        self.worker = threading.Thread(target=self._capturar_worker, args=(porta, baud, sps, tempo_s, modo), daemon=True)
        self.worker.start()

    def parar(self) -> None:
        self.stop_event.set()
        self.status_var.set("Parando...")
        try:
            if self.ser and self.ser.is_open:
                self.ser.write(b"STOP\n")
        except serial.SerialException:
            pass

    def _capturar_worker(self, porta: str, baud: int, sps: int, tempo_s: int, modo: str) -> None:
        try:
            self.eventos.put(("status", f"Abrindo {porta}..."))
            self.ser = serial.Serial(porta, baud, timeout=1)
            time.sleep(2)
            self.ser.reset_input_buffer()

            comando = f"START,{sps},{tempo_s},{modo}\n"
            self.eventos.put(("log", f"Enviando {comando.strip()} para o ESP32-S3."))
            self.ser.write(comando.encode("ascii"))

            while not self.stop_event.is_set():
                linha = self._ler_linha_serial()
                if linha:
                    self.eventos.put(("log", linha))
                if linha == "BEGIN_CAPTURE":
                    break

            if self.stop_event.is_set():
                self.eventos.put(("cancelado", None))
                return

            cabecalho = False
            metadados: dict[str, str] = {}

            while not self.stop_event.is_set():
                linha = self._ler_linha_serial()
                if not linha:
                    continue

                if linha == "END_CAPTURE":
                    break

                if linha == "STOPPED":
                    self.eventos.put(("log", "ESP32-S3 parou a captura continua."))
                    continue

                partes = linha.split(",")

                if not cabecalho and len(partes) == 2:
                    metadados[partes[0]] = partes[1]
                    self.eventos.put(("metadata", dict(metadados)))
                    continue

                if linha == "indice,tempo_us,adc":
                    cabecalho = True
                    self.eventos.put(("status", "Recebendo amostras..."))
                    continue

                if cabecalho and len(partes) == 3:
                    try:
                        amostra = (int(partes[0]), int(partes[1]), int(partes[2]))
                    except ValueError:
                        continue

                    self.eventos.put(("amostra", amostra))

            if self.stop_event.is_set():
                self.eventos.put(("cancelado", None))
                return

            self.eventos.put(("finalizado", None))
        except serial.SerialException as exc:
            self.eventos.put(("erro", f"Erro serial: {exc}"))
        except OSError as exc:
            self.eventos.put(("erro", f"Erro de arquivo/sistema: {exc}"))
        finally:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
            except serial.SerialException:
                pass
            self.ser = None

    def _ler_linha_serial(self) -> str:
        if not self.ser or not self.ser.is_open:
            return ""
        return self.ser.readline().decode("utf-8", errors="ignore").strip()

    def _processar_eventos(self) -> None:
        mudou_grafico = False

        while True:
            try:
                tipo, valor = self.eventos.get_nowait()
            except queue.Empty:
                break

            if tipo == "status":
                self.status_var.set(str(valor))
            elif tipo == "log":
                self._log(str(valor))
            elif tipo == "amostra":
                self.amostras.append(valor)  # type: ignore[arg-type]
                mudou_grafico = True
            elif tipo == "metadata":
                metadados = valor  # type: ignore[assignment]
                try:
                    samples = metadados.get("SAMPLES")  # type: ignore[union-attr]
                    self.amostras_esperadas = int(samples) if samples and samples.isdigit() else None
                except (AttributeError, ValueError):
                    self.amostras_esperadas = None
            elif tipo == "finalizado":
                self._set_rodando(False)
                self.status_var.set("Captura finalizada. Clique em CSV para salvar.")
                self._atualizar_resumo()
                mudou_grafico = True
            elif tipo == "cancelado":
                self._set_rodando(False)
                self.status_var.set("Captura cancelada.")
                self._atualizar_resumo()
                mudou_grafico = True
            elif tipo == "erro":
                self._set_rodando(False)
                self.status_var.set(str(valor))
                messagebox.showerror("Erro", str(valor))

        if mudou_grafico:
            self._atualizar_grafico()

        self.after(120, self._processar_eventos)

    def _set_rodando(self, rodando: bool) -> None:
        self.iniciar_btn.configure(state="disabled" if rodando else "normal")
        self.parar_btn.configure(state="normal" if rodando else "disabled")

    def _log(self, texto: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", texto + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _limpar_grafico(self) -> None:
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Sinal capturado")
        self.ax.set_xlabel("Tempo (s)")
        self.ax.set_ylabel(self._rotulo_eixo_y())
        self.ax.grid(True)
        self.canvas.draw_idle()
        self.resumo_var.set("Capturando...")

    def _atualizar_grafico(self) -> None:
        if not self.amostras:
            return

        if self.modo_atual == "STREAM":
            pontos = self.amostras[-4000:]
        else:
            pontos = self.amostras
        tempos = [item[1] / 1_000_000 for item in pontos]
        indices = [item[0] for item in pontos]
        adc = [item[2] for item in pontos]
        offset = sum(item[2] for item in self.amostras) / len(self.amostras)
        sinal_adc = [x - offset for x in adc]
        sinal = self._converter_sinal_para_modo(adc, sinal_adc)

        self.fig.clear()
        visualizacao = self.visualizacao_var.get()

        if visualizacao == "Tempo + FFT":
            self.ax = self.fig.add_subplot(211)
            self._desenhar_tempo(indices, tempos, sinal)
            ax_fft = self.fig.add_subplot(212)
            self._desenhar_fft(ax_fft)
        elif visualizacao == "FFT":
            self.ax = self.fig.add_subplot(111)
            self._desenhar_fft(self.ax)
        else:
            self.ax = self.fig.add_subplot(111)
            self._desenhar_tempo(indices, tempos, sinal)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _desenhar_tempo(self, indices: list[int], tempos: list[float], sinal: list[float]) -> None:
        self._plotar_com_lacunas(indices, tempos, sinal)
        try:
            self._aplicar_limites_salvos()
        except ValueError:
            pass
        self.ax.set_title("Sinal capturado")
        self.ax.set_xlabel("Tempo (s)")
        self.ax.set_ylabel(self._rotulo_eixo_y())
        self.ax.grid(True)

    def _desenhar_fft(self, ax_fft) -> None:
        try:
            import numpy as np
        except ImportError:
            ax_fft.text(0.5, 0.5, "numpy nao instalado", ha="center", va="center")
            return

        if len(self.amostras) < 4:
            ax_fft.text(0.5, 0.5, "Poucas amostras para FFT", ha="center", va="center")
            return

        tempos_us = [item[1] for item in self.amostras]
        duracao_s = (tempos_us[-1] - tempos_us[0]) / 1_000_000
        sps_real = (len(self.amostras) - 1) / duracao_s if duracao_s > 0 else self.sps_atual

        adc_total = [item[2] for item in self.amostras]
        offset = sum(adc_total) / len(adc_total)
        sinal_adc = [x - offset for x in adc_total]
        sinal = self._converter_sinal_para_modo(adc_total, sinal_adc)

        sinal_np = np.array(sinal, dtype=float)
        sinal_np = sinal_np - np.mean(sinal_np)
        janela = np.hanning(len(sinal_np))
        espectro = np.fft.rfft(sinal_np * janela)
        frequencias = np.fft.rfftfreq(len(sinal_np), d=1 / sps_real)
        magnitudes = np.abs(espectro) * 2 / max(np.sum(janela), 1)

        if len(magnitudes) > 0:
            magnitudes[0] = 0

        ax_fft.plot(frequencias, magnitudes, linewidth=1)
        ax_fft.set_title("FFT")
        ax_fft.set_xlabel("Frequencia (Hz)")
        ax_fft.set_ylabel(self._rotulo_fft_y())
        ax_fft.set_xlim(0, min(sps_real / 2, 1000))
        ax_fft.grid(True)

    def _rotulo_fft_y(self) -> str:
        if self.grafico_var.get() == "Corrente (A)" and self.fator_a_por_adc > 0:
            return "Magnitude (A)"
        return "Magnitude (contagens ADC)"

    def _converter_sinal_para_modo(self, adc: list[int], sinal_adc: list[float]) -> list[float]:
        if self.grafico_var.get() == "ADC bruto":
            return [float(valor) for valor in adc]
        if self.grafico_var.get() == "Corrente (A)" and self.fator_a_por_adc > 0:
            return [valor * self.fator_a_por_adc for valor in sinal_adc]
        return sinal_adc

    def _rotulo_eixo_y(self) -> str:
        if self.grafico_var.get() == "ADC bruto":
            return "Valor digital ADC (0 a 4095)"
        if self.grafico_var.get() == "Corrente (A)" and self.fator_a_por_adc > 0:
            return "Corrente instantanea estimada (A)"
        if self.grafico_var.get() == "Corrente (A)":
            return "Corrente (A) - calibre primeiro"
        return "ADC - offset"

    def _plotar_com_lacunas(self, indices: list[int], tempos: list[float], sinal: list[float]) -> None:
        if not indices:
            return

        intervalo_max = max(5 / max(self.sps_atual, 1), 0.01)
        inicio = 0

        for i in range(1, len(indices)):
            indice_pulou = indices[i] != indices[i - 1] + 1
            tempo_pulou = tempos[i] - tempos[i - 1] > intervalo_max

            if indice_pulou or tempo_pulou:
                self.ax.plot(tempos[inicio:i], sinal[inicio:i], linewidth=1)
                inicio = i

        self.ax.plot(tempos[inicio:], sinal[inicio:], linewidth=1)

    def _aplicar_limites_salvos(self) -> None:
        if self.x_min_var.get() and self.x_max_var.get():
            x_min = float(self.x_min_var.get())
            x_max = float(self.x_max_var.get())
            if x_min >= x_max:
                raise ValueError("X min precisa ser menor que X max.")
            self.ax.set_xlim(x_min, x_max)

        if self.y_min_var.get() and self.y_max_var.get():
            y_min = float(self.y_min_var.get())
            y_max = float(self.y_max_var.get())
            if y_min >= y_max:
                raise ValueError("Y min precisa ser menor que Y max.")
            self.ax.set_ylim(y_min, y_max)

    def _aplicar_escala(self) -> None:
        try:
            self._aplicar_limites_salvos()
            self.canvas.draw_idle()
        except ValueError as exc:
            messagebox.showerror("Escala invalida", str(exc) or "Use numeros validos para os limites dos eixos.")

    def _escala_auto(self) -> None:
        self.x_min_var.set("")
        self.x_max_var.set("")
        self.y_min_var.set("")
        self.y_max_var.set("")
        self._atualizar_grafico()

    def _trocar_modo_grafico(self, _event: object | None = None) -> None:
        self.y_min_var.set("")
        self.y_max_var.set("")
        if self.grafico_var.get() == "Corrente (A)" and self.fator_a_por_adc <= 0:
            self._log("Grafico de corrente selecionado, mas ainda nao ha calibracao.")
        self._atualizar_grafico()

    def _calibrar_corrente(self) -> None:
        if not self.amostras:
            messagebox.showerror("Sem captura", "Faca uma captura antes de calibrar.")
            return

        try:
            corrente_ref = float(self.corrente_ref_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Corrente invalida", "Informe a corrente RMS de referencia em amperes.")
            return

        if corrente_ref <= 0:
            messagebox.showerror("Corrente invalida", "A corrente de referencia precisa ser maior que zero.")
            return

        rms_adc = self._calcular_rms_adc()
        if rms_adc <= 0:
            messagebox.showerror("Sinal invalido", "RMS ADC ficou zero; nao e possivel calibrar.")
            return

        self.fator_a_por_adc = corrente_ref / rms_adc
        self._log(f"Calibrado: 1 contagem RMS ADC = {self.fator_a_por_adc:.8f} A")
        self._atualizar_resumo()
        self._atualizar_grafico()

    def _limpar_calibracao(self) -> None:
        self.fator_a_por_adc = 0.0
        self._log("Calibracao de corrente removida.")
        self._atualizar_resumo()
        self._atualizar_grafico()

    def _calcular_rms_adc(self) -> float:
        adc = [item[2] for item in self.amostras]
        offset = sum(adc) / len(adc)
        sinal = [x - offset for x in adc]
        return math.sqrt(sum(x * x for x in sinal) / len(sinal))

    def _atualizar_resumo(self) -> None:
        if not self.amostras:
            self.resumo_var.set("Nenhuma amostra recebida.")
            return

        tempos_us = [item[1] for item in self.amostras]
        adc = [item[2] for item in self.amostras]
        offset = sum(adc) / len(adc)
        rms_adc = self._calcular_rms_adc()
        duracao_s = (tempos_us[-1] - tempos_us[0]) / 1_000_000
        sps = (len(self.amostras) - 1) / duracao_s if duracao_s > 0 else 0
        corrente_txt = ""
        if self.fator_a_por_adc > 0:
            corrente_rms = rms_adc * self.fator_a_por_adc
            corrente_txt = f"\nCorrente RMS: {corrente_rms:.4f} A"

        self.resumo_var.set(
            f"Amostras: {len(self.amostras)}\n"
            f"Duracao: {duracao_s:.6f} s\n"
            f"SPS real: {sps:.2f}\n"
            f"ADC min/max: {min(adc)} / {max(adc)}\n"
            f"Offset medio: {offset:.2f}\n"
            f"RMS ADC: {rms_adc:.2f}"
            f"{corrente_txt}"
            + self._resumo_perdas(len(self.amostras))
        )

    def _resumo_perdas(self, recebidas: int) -> str:
        if self.amostras_esperadas is None:
            return ""

        faltantes = self.amostras_esperadas - recebidas
        if faltantes <= 0:
            return f"\nEsperadas: {self.amostras_esperadas}"

        percentual = faltantes * 100 / self.amostras_esperadas
        return f"\nEsperadas: {self.amostras_esperadas}\nAviso: faltaram {faltantes} ({percentual:.1f}%)"


if __name__ == "__main__":
    app = DaqApp()
    app.mainloop()
