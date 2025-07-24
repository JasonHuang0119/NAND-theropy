import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import pandas as pd
import re


def remap_tick_index(df):
    # 建立 Tick 映射表：原本的 index 0~255 → Vt: -128~127
    tick_to_vt = {i: i - 256 if i >= 128 else i for i in range(256)}

    # 替換 index
    df.index = df.index.map(tick_to_vt)

    # 重新排序 index：-128 ~ -1 再接 0 ~ 127
    reordered_index = list(range(-128, 0)) + list(range(0, 128))
    return df.loc[reordered_index]

def process_file(file_path):
    data = []
    ch_map = {'00': 'CH0', '01': 'CH1', '02': 'CH2', '03': 'CH3'}

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i in range(len(lines)):
        line = lines[i].strip()
        if 'TOP:MinFBC_SAR_order:' in line:
            sar_matches = re.findall(r'(S\d+R)=(\w+)', line)
            row = {}
            current_ch = None
            for j in range(i, len(lines)):
                ch_line = lines[j].strip()
                if 'TOP : Ch=' in ch_line:
                    ch_match = re.search(r'Ch=(\d+)', ch_line)
                    if ch_match:
                        ch_id = ch_match.group(1).zfill(2)
                        current_ch = ch_map.get(ch_id, None)
                        break
            if current_ch:
                row['CH'] = current_ch
                for sar_label, sar_value in sar_matches:
                    row[sar_label] = sar_value
                data.append(row)

    df = pd.DataFrame(data)
    sar_offsets = [0x03, 0xFF, 0xFF, 0xFE, 0xFF, 0xFF, 0xFF,
                   0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0xFE, 0xFD]
    sar_columns = [f"S{i}R" for i in range(1, 16)]

    for idx, col in enumerate(sar_columns):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: format((int(x, 16) + sar_offsets[idx]) & 0xFF, '02X') if pd.notnull(x) else x
            )

    tick_stats = {ch: pd.DataFrame(0, index=range(256), columns=sar_columns) for ch in df['CH'].unique()}
    for _, row in df.iterrows():
        ch = row['CH']
        for col in sar_columns:
            val = row.get(col)
            if pd.notnull(val):
                tick = int(val, 16)
                tick_stats[ch].at[tick, col] += 1

    # reordered_index = list(range(128, 256)) + list(range(0, 128))
    # for ch in tick_stats:
    #     tick_stats[ch] = tick_stats[ch].loc[reordered_index]

    combined_df = None
    for df in tick_stats.values():
        if combined_df is None:
            combined_df = df.copy()
        else:
            combined_df = combined_df.add(df, fill_value=0)
    combined_df.index.name = "Tick"

    # ✅ 這裡加上 Remap 成 -128 ~ 127 的 Tick
    combined_df = remap_tick_index(combined_df)

    # === 插入每欄位的加權平均值與標準差（Tick 為 x 軸，對應次數為權重）===
    weighted_means = {}
    weighted_stds = {}

    for col in combined_df.columns:
        values = combined_df[col]
        weights = values.fillna(0).to_numpy()
        ticks = combined_df.index.to_numpy()

        if weights.sum() == 0:
            weighted_means[col] = ""
            weighted_stds[col] = ""
        else:
            mean = (ticks * weights).sum() / weights.sum()
            std = (((ticks - mean) ** 2 * weights).sum() / weights.sum()) ** 0.5

            weighted_means[col] = f"{mean:.4f}"
            weighted_stds[col] = f"{std:.4f}"

    mean_row = pd.Series(weighted_means, name="Average (Vt)")
    std_row = pd.Series(weighted_stds, name="Std (Vt)")

    combined_df = pd.concat([mean_row.to_frame().T, std_row.to_frame().T, combined_df])



    base_name = os.path.splitext(os.path.basename(file_path))[0]  # 拿掉副檔名的檔名
    output_name = f"{base_name}_Tick_Distribution.csv"
    output_path = os.path.join(os.path.dirname(file_path), output_name)

    # output_path = os.path.join(os.path.dirname(file_path), "All_CH_Tick_Distribution_GUI.csv")
    combined_df.to_csv(output_path, encoding='utf-8-sig')
    return output_path

def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if file_path:
        try:
            output = process_file(file_path)
            messagebox.showinfo("✅ 完成", f"已輸出：\n{output}")
        except Exception as e:
            messagebox.showerror("❌ 錯誤", str(e))

# === GUI 主畫面 ===
root = tk.Tk()
root.title("🧮 SAR Tick State 轉換器")
root.geometry("450x250")
root.configure(bg="#f0f0f0")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Microsoft JhengHei", 11), padding=8)
style.configure("TLabel", background="#f0f0f0", font=("Microsoft JhengHei", 12))

ttk.Label(root, text="請選擇單一 SAR 檔案進行處理").pack(pady=(30, 10))
ttk.Button(root, text="📂 選擇檔案並開始處理", command=select_file).pack(pady=10)

root.mainloop()
