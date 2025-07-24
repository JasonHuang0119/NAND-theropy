import pandas as pd
import os
from tkinter import filedialog, messagebox, Tk

def merge_and_calculate_csv():
    # 開啟檔案選擇對話框，選兩個 CSV
    file_paths = filedialog.askopenfilenames(
        title="選擇兩個 Tick 統計的 CSV 檔案進行合併",
        filetypes=[("CSV Files", "*.csv")]
    )
    if len(file_paths) != 2:
        messagebox.showerror("❌ 錯誤", "請選擇兩個 CSV 檔案！")
        return

    # 載入兩個 DataFrame（跳過平均值、標準差列）
    dfs = []
    for path in file_paths:
        df = pd.read_csv(path, index_col=0)
        df = df[~df.index.isin(["平均值", "標準差"])]
        # ✅ 濾除非整數 index（如平均值與標準差列）
        df = df[df.index.str.match(r"^-?\d+$")]  # 只保留純數字（Tick）
        df.index = df.index.astype(int)
        dfs.append(df)

    # 合併後相加
    merged_df = dfs[0].add(dfs[1], fill_value=0)

    # === 改成加權平均與加權標準差計算（Tick 為 x 軸）===
    weighted_means = {}
    weighted_stds = {}

    ticks = merged_df.index.to_numpy()

    for col in merged_df.columns:
        weights = merged_df[col].fillna(0).to_numpy()

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

    # 插入
    merged_df = pd.concat([mean_row.to_frame().T, std_row.to_frame().T, merged_df])
    merged_df.index.name = "Tick"

    # 儲存
    folder_path = os.path.dirname(file_paths[0])
    folder_name = os.path.basename(folder_path)  # 當前資料夾名稱
    parent_folder_name = os.path.basename(os.path.dirname(folder_path))  # 前一個資料夾名稱

    save_path = os.path.join(
        os.path.dirname(file_paths[0]),
        f"Merged_Tick_Distribution_{parent_folder_name}_{folder_name}.csv"
    )

    merged_df.to_csv(save_path, encoding="utf-8-sig")
    messagebox.showinfo("✅ 合併完成", f"輸出：\n{save_path}")

# 啟動小 GUI 叫選擇檔案用
if __name__ == "__main__":
    root = Tk()
    root.withdraw()
    merge_and_calculate_csv()
    root.mainloop()
