import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

try:
    import config
    DEFAULT_TOKEN = config.API_KEY
except ImportError:
    DEFAULT_TOKEN = ""

class QuantumApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("900x750")

        input_frame = tk.Frame(root, pady=10)
        input_frame.pack(side=tk.TOP, fill=tk.X, padx=10)

        tk.Label(input_frame, text="API atslēga:").pack(side=tk.LEFT)
        
        self.token_entry = tk.Entry(input_frame, width=50)
        self.token_entry.pack(side=tk.LEFT, padx=5)
        self.token_entry.insert(0, DEFAULT_TOKEN)

        self.run_btn = tk.Button(input_frame, text="SĀKT EKSPERIMENTU", bg="#6929c4", fg="white", command=self.start_thread)
        self.run_btn.pack(side=tk.LEFT, padx=10)

        self.log_area = scrolledtext.ScrolledText(root, height=18, state='disabled', bg="#f0f0f0")
        self.log_area.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.plot_frame = tk.Frame(root)
        self.plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.figure = plt.Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def log(self, message):
        self.root.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def start_thread(self):
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Kļūda", "API atslēga ir obligāta! Readme failā ir norādīts, kā to iegūt.")
            return
        
        self.run_btn.config(state=tk.DISABLED, text="Izpilda...")
        self.ax.clear()
        self.canvas.draw()
        
        thread = threading.Thread(target=self.run_quantum_logic, args=(token,))
        thread.daemon = True
        thread.start()

    def log_per_qubit_statistics(self, counts):
        total_shots = sum(counts.values())
        
        if not counts:
            return
            
        num_qubits = len(list(counts.keys())[0])
        
        expected_mean = total_shots / 2
        std_dev = math.sqrt(total_shots * 0.5 * 0.5)
        
        self.log(f"\n--- (Kopējais mērījumu skaits: {total_shots}) ---")
        self.log(f"Teorētiskais vidējais: {expected_mean:.0f}, Standartnovirze: {std_dev:.2f}")

        for i in range(num_qubits):
            zeros = 0
            ones = 0
            
            for bitstring, count in counts.items():
                state = bitstring[i] 
                
                if state == '0':
                    zeros += count
                elif state == '1':
                    ones += count
            
            zero_percent = (zeros / total_shots) * 100
            one_percent = (ones / total_shots) * 100
            
            delta = abs(zeros - expected_mean)
            z_score = delta / std_dev
            
            prob_random = (1.0 - math.erf(z_score / math.sqrt(2.0))) * 100
            
            self.log(f"Pozīcija {i}:")
            self.log(f"  Stāvoklis '0': {zeros} ({zero_percent:.2f}%)")
            self.log(f"  Stāvoklis '1': {ones} ({one_percent:.2f}%)")
            self.log(f"  Novirze: {delta:.0f} mērījumi ({z_score:.2f} Sigma)")
            self.log(f"  Varbūtība, ka tā ir nejaušība: {prob_random:.2f}%")
            self.log("-" * 30)

    def run_quantum_logic(self, token):
        try:
            self.log("--- Sāk jaunu uzdevumu ---")
            
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
            
            backend = service.least_busy(operational=True, simulator=False)
            
            self.log(f"Pieslēgts pie: {backend.name}")
            self.log(f"Rindā gaidošie uzdevumi: {backend.status().pending_jobs}")

            qc = QuantumCircuit(2)
            qc.h(0)
            qc.cx(0, 1)
            qc.measure_all()

            qc = transpile(qc, backend)

            sampler = SamplerV2(backend)
            job = sampler.run([qc])
            
            self.log(f"Uzdevuma ID: {job.job_id()}")
            self.log("Gaida rezultātus...")
            
            result = job.result()

            counts = result[0].data.meas.get_counts()
            
            self.log(f"{counts}")
            
            self.log_per_qubit_statistics(counts)

            self.root.after(0, self.draw_plot, counts)

        except Exception as e:
            self.log(f"KĻŪDA: {str(e)}")
        
        finally:
            self.root.after(0, lambda: self.run_btn.config(state=tk.NORMAL, text="SĀKT EKSPERIMENTU"))

    def draw_plot(self, counts):
        self.ax.clear()
        
        sorted_keys = sorted(counts.keys())
        sorted_values = [counts[k] for k in sorted_keys]
        
        bars = self.ax.bar(sorted_keys, sorted_values, color='#6929c4')
        
        self.ax.set_title(f"(Kopējais mērījumu skaits: {sum(sorted_values)})")
        self.ax.set_ylabel("Skaits")
        self.ax.set_xlabel("Stāvoklis")
        self.ax.grid(axis='y', linestyle='--', alpha=0.5)

        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height,
                         f'{int(height)}',
                         ha='center', va='bottom')

        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = QuantumApp(root)
    root.mainloop()