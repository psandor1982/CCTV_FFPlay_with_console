
# DashboardV5 - Ping & RTSP Monitoring Dashboard (with Ping Graph restored)

import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import time
import platform
import re
import cv2
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

class DashboardV5:
    def __init__(self, master):
        self.master = master
        master.title("DashboardV5")

        # ================= IP / PORT =================
        tk.Label(master, text="IP Address").pack()
        self.ip_entry = tk.Entry(master)
        self.ip_entry.insert(0, "192.168.0.83")
        self.ip_entry.pack()

        tk.Label(master, text="RTSP Port").pack()
        self.port_entry = tk.Entry(master, width=10)
        self.port_entry.insert(0, "554")
        self.port_entry.pack()

        # ================= PING CONTROLS =================
        self.ping_btn_frame = tk.Frame(master)
        self.ping_btn_frame.pack(pady=5)

        self.start_ping_btn = tk.Button(self.ping_btn_frame, text="Start Ping", command=self.start_ping)
        self.start_ping_btn.pack(side=tk.LEFT, padx=5)

        self.stop_ping_btn = tk.Button(self.ping_btn_frame, text="Stop Ping", command=self.stop_ping)
        self.stop_ping_btn.pack(side=tk.LEFT, padx=5)

        self.ping_label = tk.Label(master, text="Ping: N/A")
        self.ping_label.pack()

        # ================= PING GRAPH =================
        self.fig, self.ax = plt.subplots(figsize=(6, 2))
        self.ping_times = []
        self.ping_values = []
        self.line, = self.ax.plot([], [], 'g-')
        self.ax.set_title("Ping History")
        self.ax.set_ylabel("ms")
        self.canvas = FigureCanvasTkAgg(self.fig, master)
        self.canvas.get_tk_widget().pack()

        # ================= AUTH =================
        tk.Label(master, text="Username").pack()
        self.username_entry = tk.Entry(master)
        self.username_entry.pack()

        tk.Label(master, text="Password").pack()
        self.password_entry = tk.Entry(master, show="*")
        self.password_entry.pack()

        # ================= GEN2 PRESETS =================
        tk.Label(master, text="GEN2 Vendor Preset").pack()
        self.vendor_var = tk.StringVar(value="Generic")
        self.vendor_presets = {
            "Generic": (1, 0),
            "Hikvision": (1, 1),
            "Dahua": (2, 0),
            "Axis": (1, 0)
        }
        self.vendor_menu = tk.OptionMenu(master, self.vendor_var, *self.vendor_presets.keys(), command=self.apply_vendor_preset)
        self.vendor_menu.pack()

        # ================= CHANNEL SELECT =================
        self.channel_frame = tk.Frame(master)
        self.channel_frame.pack(pady=5)

        tk.Label(self.channel_frame, text="Main Stream").pack(side=tk.LEFT)
        self.channel_a = tk.IntVar(value=1)
        self.channel_a_menu = tk.OptionMenu(self.channel_frame, self.channel_a, *range(1, 21))
        self.channel_a_menu.pack(side=tk.LEFT, padx=5)

        tk.Label(self.channel_frame, text="Sub Stream").pack(side=tk.LEFT)
        self.channel_b = tk.IntVar(value=0)
        self.channel_b_menu = tk.OptionMenu(self.channel_frame, self.channel_b, 0, 1)
        self.channel_b_menu.pack(side=tk.LEFT, padx=5)

        # ================= RTSP PREVIEW =================
        tk.Label(master, text="RTSP URL Preview").pack()
        self.rtsp_preview = tk.Entry(master, width=80, state="readonly")
        self.rtsp_preview.pack()

        # ================= BUTTONS =================
        self.btn_frame = tk.Frame(master)
        self.btn_frame.pack(pady=10)

        self.gen2_btn = tk.Button(self.btn_frame, text="SWANN", command=self.run_gen2)
        self.gen2_btn.pack(side=tk.LEFT, padx=5)

        self.gen3_btn = tk.Button(self.btn_frame, text="360Vision", command=self.run_gen3)
        self.gen3_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(self.btn_frame, text="STOP", command=self.stop_stream)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # ================= VIDEO =================
        self.status = tk.Label(master, text="Stream: Disconnected", fg="red")
        self.status.pack()

        self.video_label = tk.Label(master)
        self.video_label.pack()

        # ================= STATE =================
        self.streaming = False
        self.pinging = False
        self.cap = None
        self.reconnect_delay = 2

    # ================= PING LOGIC =================
    def start_ping(self):
        if not self.pinging:
            self.pinging = True
            threading.Thread(target=self.ping_loop, daemon=True).start()

    def stop_ping(self):
        self.pinging = False

    def ping_loop(self):
        while self.pinging:
            ip = self.ip_entry.get().strip()
            ping = self.ping_ip(ip)
            now = datetime.datetime.now()

            if ping is not None:
                self.ping_label.config(text=f"Ping: {ping:.2f} ms")
                self.ping_times.append(now)
                self.ping_values.append(ping)

                if len(self.ping_values) > 100:
                    self.ping_times.pop(0)
                    self.ping_values.pop(0)

                self.update_graph()

            time.sleep(1)

    def ping_ip(self, ip):
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            cmd = ["ping", param, "1", ip]
            result = subprocess.run(cmd, capture_output=True, text=True)
            match = re.search(r'time[=<]\s*(\d+\.?\d*)', result.stdout)
            return float(match.group(1)) if match else None
        except:
            return None

    def update_graph(self):
        self.line.set_data(range(len(self.ping_values)), self.ping_values)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    # ================= STREAM LOGIC =================
    def apply_vendor_preset(self, vendor):
        a, b = self.vendor_presets[vendor]
        self.channel_a.set(a)
        self.channel_b.set(b)
        self.update_preview()

    def validate_channels(self):
        if not (1 <= self.channel_a.get() <= 20):
            raise ValueError("Channel must be 1–20")
        if self.channel_b.get() not in (0, 1):
            raise ValueError("Sub stream must be 0 or 1")

    def build_rtsp_url(self, path):
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        u = self.username_entry.get()
        p = self.password_entry.get()
        if u and p:
            return f"rtsp://{u}:{p}@{ip}:{port}{path}"
        return f"rtsp://{ip}:{port}{path}"

    def update_preview(self):
        try:
            self.validate_channels()
            url = self.build_rtsp_url(f"/ch{self.channel_a.get()}/{self.channel_b.get()}")
            self.rtsp_preview.config(state="normal")
            self.rtsp_preview.delete(0, tk.END)
            self.rtsp_preview.insert(0, url)
            self.rtsp_preview.config(state="readonly")
        except:
            pass

    def run_gen2(self):
        self.update_preview()
        self.start_stream(self.build_rtsp_url(f"/ch{self.channel_a.get()}/{self.channel_b.get()}"))

    def run_gen3(self):
        self.start_stream(self.build_rtsp_url("/stream1"))

    def start_stream(self, url):
        self.stop_stream()
        self.streaming = True
        threading.Thread(target=self.video_loop, args=(url,), daemon=True).start()

    def stop_stream(self):
        self.streaming = False
        if self.cap:
            self.cap.release()
        self.video_label.config(image="")
        self.status.config(text="Stream: Disconnected", fg="red")

    def video_loop(self, url):
        while self.streaming:
            self.cap = cv2.VideoCapture(url)
            if not self.cap.isOpened():
                self.status.config(text="Reconnecting...", fg="orange")
                time.sleep(self.reconnect_delay)
                continue

            self.status.config(text="Connected", fg="green")

            while self.streaming and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break
                frame = cv2.resize(frame, (700, 400))
                img = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                self.video_label.imgtk = img
                self.video_label.config(image=img)

            self.cap.release()
            time.sleep(self.reconnect_delay)

if __name__ == "__main__":
    root = tk.Tk()
    DashboardV5(root)
    root.mainloop()
