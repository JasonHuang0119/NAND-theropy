import pandas as pd
import matplotlib.pyplot as plt
import os
from tkinter import filedialog, messagebox, Tk
import re
import numpy as np

def simplify_folder_name(folder_name):
    match = re.match(r"(DR\d+)", folder_name)
    return match.group(1) if match else folder_name

def extract_average_vt_row(file_path):
    df = pd.read_csv(file_path, index_col=0)
    if "Average (Vt)" not in df.index:
        raise ValueError(f"檔案缺少 'Average (Vt)' 列: {file_path}")
    return df.loc["Average (Vt)"].filter(regex=r"S\d+R")

def get_grandparent_folder_name(file_path):
    # C:/.../DR48p2h/0p1k/file.csv -> 回傳 DR48p2h
    parent_dir = os.path.dirname(file_path)
    grandparent_dir = os.path.dirname(parent_dir)
    return os.path.basename(grandparent_dir)

def merge_and_plot_lines():
    root = Tk()
    root.withdraw()

    file_paths = []
    while True:
        file_path = filedialog.askopenfilename(
            title="選擇一個 Merged_Tick_Distribution_*.csv 檔案（取消結束）",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            break
        file_paths.append(file_path)

    if len(file_paths) == 0:
        messagebox.showerror("❌ 錯誤", "請至少選擇一個檔案")
        return

    sensor_data = {}

    for path in file_paths:
        grandparent_folder = get_grandparent_folder_name(path)
        time_tag = simplify_folder_name(grandparent_folder)

        try:
            avg_row = extract_average_vt_row(path)
            for sensor, vt_value in avg_row.items():
                if vt_value == "":
                    continue
                sensor_data.setdefault(sensor, {})[time_tag] = float(vt_value)
        except Exception as e:
            messagebox.showerror("❌ 錯誤", str(e))
            return

    df = pd.DataFrame(sensor_data).T
    time_order = sorted(df.columns, key=lambda x: int(re.search(r"\d+", x).group()))
    df = df[time_order]

    # 畫圖（每個 sensor 一條線，x 軸為時間 DR）
    plt.figure(figsize=(10, 6))
    for sensor in sorted(df.index, key=lambda s: int(re.search(r"\d+", s).group())):
        plt.plot(time_order, df.loc[sensor], marker='o', label=sensor)

    plt.title("Average Vt per Sensor over Time")
    plt.xlabel("Time (DR)")
    plt.ylabel("Average Vt")
    plt.grid(True)
    plt.legend(title="State", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()

    # ✅ 加上 Y 軸間距縮小（例如每 1）
    ax = plt.gca()
    y_min = np.floor(df.min().min()) - 1
    y_max = np.ceil(df.max().max()) + 1
    ax.set_yticks(np.arange(y_min, y_max + 1, 0.5))  # ⬅️ 改成每 1.0 間

    save_path = os.path.join(os.path.dirname(file_paths[0]), "Sensor_LinePlot_by_Time.png")
    plt.savefig(save_path, dpi=300)
    plt.show()

    messagebox.showinfo("✅ 完成", f"圖已儲存：\n{save_path}")

if __name__ == "__main__":
    merge_and_plot_lines()
