import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class FastDataMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BIt 數據合併工具 v5.8 (手動開啟檔案版)")
        self.root.geometry("900x980")

        self.bit_pattern = re.compile(r"(BIt\s+(\d+)\s+:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+))")
        self.file_cache = {}
        self.file1_path = tk.StringVar()
        self.file2_path = tk.StringVar()
        self.occurrence_var = tk.StringVar(value="1")
        self.page_var = tk.StringVar(value="Total")
        self.info_text = tk.StringVar(value="等待載入檔案...")
        
        # 用於紀錄當前分析組別的行號資訊
        self.current_lines = {"f1": 0, "f2": 0, "occ": ""}
        self.final_output_rows = []
        
        self.setup_ui()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=20, pady=10)
        main_frame.pack(expand=True, fill="both")

        # 1. 檔案選取
        fg = tk.LabelFrame(main_frame, text="1. 檔案載入", padx=10, pady=10)
        fg.pack(fill="x", pady=5)
        for i, (label, var) in enumerate([("檔案一:", self.file1_path), ("檔案二:", self.file2_path)]):
            tk.Label(fg, text=label).grid(row=i, column=0, sticky="w")
            tk.Entry(fg, textvariable=var, width=70).grid(row=i, column=1, padx=5)
            tk.Button(fg, text="載入", command=lambda idx=i+1: self.load_and_cache(idx)).grid(row=i, column=2)
        tk.Label(fg, textvariable=self.info_text, fg="blue", font=("Arial", 9, "italic")).grid(row=2, column=1, sticky="w")

        # 2. 合併參數與執行
        og = tk.LabelFrame(main_frame, text="2. 合併與分析設定", padx=10, pady=10)
        og.pack(fill="x", pady=5)
        
        set_frame = tk.Frame(og)
        set_frame.pack(fill="x")
        tk.Label(set_frame, text="組數:").pack(side="left")
        self.occ_menu = ttk.Combobox(set_frame, textvariable=self.occurrence_var, values=["1", "2", "3", "4"], width=3, state="readonly")
        self.occ_menu.pack(side="left", padx=5)
        tk.Label(set_frame, text="顯示 Page:").pack(side="left", padx=(15, 0))
        self.page_menu = ttk.Combobox(set_frame, textvariable=self.page_var, values=["Total", "Page 0", "Page 1", "Page 2", "Page 3"], width=8, state="readonly")
        self.page_menu.pack(side="left", padx=5)
        
        self.run_btn = tk.Button(og, text="執行合併並繪圖", command=self.fast_process, 
                                 bg="#2196F3", fg="white", font=("Arial", 10, "bold"), height=2)
        self.run_btn.pack(fill="x", pady=(10, 5))

        # 新增：開啟原始檔案按鈕區
        btn_frame = tk.Frame(og)
        btn_frame.pack(fill="x")
        self.open1_btn = tk.Button(btn_frame, text="開啟檔案一原始位置", command=lambda: self.open_file_at_line(1), state="disabled")
        self.open1_btn.pack(side="left", expand=True, fill="x", padx=2)
        self.open2_btn = tk.Button(btn_frame, text="開啟檔案二原始位置", command=lambda: self.open_file_at_line(2), state="disabled")
        self.open2_btn.pack(side="left", expand=True, fill="x", padx=2)

        # 3. 圖表顯示區域
        self.chart_frame = tk.LabelFrame(main_frame, text="3. FBC 趨勢圖 (連線模式)", padx=5, pady=5)
        self.chart_frame.pack(fill="both", expand=True, pady=5)
        self.empty_label = tk.Label(self.chart_frame, text="執行後顯示圖表", fg="gray")
        self.empty_label.pack(pady=20)

        # 4. 表格區域
        table_frame = tk.Frame(main_frame, height=150)
        table_frame.pack(fill="x", pady=5)
        table_frame.pack_propagate(False)

        columns = ("bit", "f1_vals", "f2_vals", "sum_result")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for col in columns: self.tree.column(col, width=120, anchor="center")
        self.tree.heading("bit", text="BIt 編號"); self.tree.heading("f1_vals", text="檔案 1"); self.tree.heading("f2_vals", text="檔案 2"); self.tree.heading("sum_result", text="結果")

        # 5. 匯出按鈕
        self.save_btn = tk.Button(main_frame, text="匯出結果 (*.txt)", command=self.save_output, 
                                  state="disabled", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.save_btn.pack(pady=5, fill="x")

    def load_and_cache(self, file_idx):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path: return
        if file_idx == 1: self.file1_path.set(path)
        else: self.file2_path.set(path)
        groups = []; current_group = {}; last_bit = -1
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_idx, line in enumerate(f, 1):
                    match = self.bit_pattern.search(line)
                    if match:
                        b_idx = int(match.group(2))
                        vals = [int(match.group(i)) for i in range(3, 7)]
                        if b_idx <= last_bit:
                            groups.append(current_group); current_group = {}
                        current_group[b_idx] = (line_idx, match.group(1), vals)
                        last_bit = b_idx
                if current_group: groups.append(current_group)
            self.file_cache[path] = groups
            self.update_info()
        except Exception as e: messagebox.showerror("錯誤", f"讀取失敗: {e}")

    def update_info(self):
        p1, p2 = self.file1_path.get(), self.file2_path.get()
        c1 = len(self.file_cache.get(p1, [])); c2 = len(self.file_cache.get(p2, []))
        self.info_text.set(f"偵測完成 -> 檔案一: {c1} 組 | 檔案二: {c2} 組")

    def fast_process(self):
        p1, p2 = self.file1_path.get(), self.file2_path.get()
        try: target_idx = int(self.occurrence_var.get()) - 1
        except: return
        g1, g2 = self.file_cache.get(p1), self.file_cache.get(p2)
        if not g1 or not g2 or target_idx >= len(g1) or target_idx >= len(g2):
            messagebox.showerror("錯誤", "檔案未載入或該組數不存在"); return

        d1, d2 = g1[target_idx], g2[target_idx]
        self.tree.delete(*self.tree.get_children())
        self.final_output_rows = []; all_page_results = []; all_bits = sorted(set(d1.keys()) | set(d2.keys()))
        if not all_bits: return

        # 紀錄起始行號供按鈕使用
        self.current_lines["f1"] = d1[all_bits[0]][0]
        self.current_lines["f2"] = d2[all_bits[0]][0]
        self.current_lines["occ"] = self.occurrence_var.get()

        for b in all_bits:
            info1 = d1.get(b, (0, "None", [0]*4)); info2 = d2.get(b, (0, "None", [0]*4))
            v1, v2 = info1[2], info2[2]
            res = [x + y for x, y in zip(v1, v2)]
            self.final_output_rows.append("\t".join(map(str, res)))
            all_page_results.append(res)
            self.tree.insert("", "end", values=(f"BIt {b}", v1, v2, res))

        self.save_btn.config(state="normal")
        self.open1_btn.config(state="normal")
        self.open2_btn.config(state="normal")
        self.draw_scatter(all_bits, all_page_results)
        messagebox.showinfo("完成", f"數據合併完成！\n如需查看原始檔案，請點擊下方按鈕。")

    def open_file_at_line(self, file_idx):
        path = self.file1_path.get() if file_idx == 1 else self.file2_path.get()
        line = self.current_lines["f1"] if file_idx == 1 else self.current_lines["f2"]
        occ = self.current_lines["occ"]
        
        if not path or not os.path.exists(path):
            messagebox.showwarning("警告", "找不到檔案路徑")
            return

        msg = f"即將開啟檔案：\n{os.path.basename(path)}\n\n" \
              f"當前為第 {occ} 組數據\n" \
              f"起始行號為：{line}\n\n" \
              f"提示：在 Notepad 中按 Ctrl + G 可快速跳轉行號。"
        messagebox.showinfo("準備開啟檔案", msg)
        try: os.startfile(path)
        except: messagebox.showerror("錯誤", "無法開啟檔案")

    def draw_scatter(self, x_data, all_page_results):
        for widget in self.chart_frame.winfo_children(): widget.destroy()
        selection = self.page_var.get()
        if selection == "Total":
            y_data = [sum(row) for row in all_page_results]; title = "Total Fail Bits"; color = '#E91E63'
        else:
            page_idx = int(selection.split(" ")[1])
            y_data = [row[page_idx] for row in all_page_results]
            title = f"Fail Bits for {selection}"; colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0']
            color = colors[page_idx]

        fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
        ax.set_yscale('log')
        ax.plot(x_data, y_data, color=color, linewidth=1.0, alpha=0.8)
        ax.set_title(f"{title} - Trend Analysis (Log Scale)")
        ax.set_xlabel("BIt Number"); ax.set_ylabel("Fail Bits (Log)")
        ax.grid(True, which="both", linestyle='--', alpha=0.4)

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        toolbar_frame = tk.Frame(self.chart_frame); toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame); toolbar.update()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def save_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="Merge_FBC.txt")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f: f.write("\n".join(self.final_output_rows))
                messagebox.showinfo("成功", "存檔完成！")
            except Exception as e: messagebox.showerror("錯誤", f"存檔失敗: {e}")

if __name__ == "__main__":
    root = tk.Tk(); app = FastDataMergerApp(root); root.mainloop()