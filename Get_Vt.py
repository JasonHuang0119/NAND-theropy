import sys, re, os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QTextEdit, QGroupBox, QHBoxLayout)
from PyQt6.QtCore import Qt

class VtParserGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.input_file = ""
        self.initUI()

    def initUI(self):
        self.setWindowTitle('NAND Vt 數據合成器 v2.3 - 自動進位偵測版')
        self.resize(850, 700)
        
        # 現代化 UI 樣式
        self.setStyleSheet("""
            QWidget { background-color: #F8F9FA; font-family: 'Microsoft JhengHei', 'Segoe UI'; color: #333333; }
            QGroupBox { 
                background-color: #FFFFFF; 
                border: 1px solid #E1E4E8; 
                border-radius: 12px; 
                margin-top: 15px; 
                padding-top: 25px; 
                color: #1A73E8; 
                font-weight: bold; 
            }
            QPushButton { 
                background-color: #FFFFFF; 
                color: #1A73E8; 
                border: 1px solid #1A73E8; 
                border-radius: 6px; 
                padding: 10px; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #F1F8FF; }
            #RunBtn { 
                background-color: #34A853; 
                color: white; 
                height: 55px; 
                font-size: 16px; 
                border: none; 
                border-radius: 8px;
            }
            #RunBtn:hover { background-color: #2D8E47; }
            #RunBtn:disabled { background-color: #BDC3C7; }
            QTextEdit { 
                background-color: #FFFFFF; 
                border: 1px solid #D1D5DA; 
                border-radius: 8px; 
                font-family: 'Consolas', 'Microsoft JhengHei'; 
                font-size: 13px; 
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 35, 35, 35)

        title = QLabel("NAND Vt 數據自動合成系統")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #202124;")
        layout.addWidget(title)

        # 1. 檔案選取
        file_group = QGroupBox("第一步：載入原始資料")
        file_layout = QHBoxLayout()
        self.file_label = QLabel("請選擇 Vt Log 檔案...")
        btn_select = QPushButton("瀏覽檔案")
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label); file_layout.addStretch(); file_layout.addWidget(btn_select)
        file_group.setLayout(file_layout); layout.addWidget(file_group)

        # 2. 執行
        self.run_btn = QPushButton("▶ 偵測進位制並執行解析")
        self.run_btn.setObjectName("RunBtn")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.clicked.connect(self.process_vt_data)
        layout.addWidget(self.run_btn)

        # 3. 日誌
        status_group = QGroupBox("第二步：系統處理狀態")
        status_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        status_layout.addWidget(self.log_area)
        status_group.setLayout(status_layout); layout.addWidget(status_group)

    def log(self, text):
        self.log_area.append(f"● {text}")
        QApplication.processEvents()

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "開啟 Vt Log", "", "文字檔案 (*.txt);;所有檔案 (*)")
        if file_path:
            self.input_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet("color: #1A73E8; font-weight: bold;")
            self.log(f"已載入檔案: {file_path}")

    def is_hex_file(self, lines):
        """
        掃描檔案中所有的 WL 標記，只要有一個符合 HEX 特徵，就判定整份為 HEX
        """
        meta_p = re.compile(r"WL:\s*([0-9A-Fa-f]+)", re.IGNORECASE)
        for line in lines:
            m = meta_p.search(line)
            if m:
                wl_str = m.group(1).strip()
                # 特徵 1: 包含 A-F
                if any(c in 'abcdefABCDEF' for c in wl_str):
                    return True
                # 特徵 2: 以 0 開頭且為 4 位數 (例如 0442)
                if len(wl_str) == 4 and wl_str.startswith('0'):
                    return True
        return False

    def process_vt_data(self):
        if not self.input_file or not os.path.exists(self.input_file):
            self.log("錯誤: 請先選擇輸入檔案。")
            return

        self.log_area.clear()
        self.run_btn.setEnabled(False)

        try:
            with open(self.input_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            self.log(f"讀取失敗: {e}")
            self.run_btn.setEnabled(True)
            return

        # 全域辨識進位制
        hex_mode = self.is_hex_file(lines)
        self.log(f"系統辨識結果: {'【十六進位 (HEX)】' if hex_mode else '【十進位 (DEC)】'}")

        # 設定輸出路徑
        source_dir = os.path.dirname(os.path.abspath(self.input_file))
        output_dir = os.path.join(source_dir, "Vt_output")
        os.makedirs(output_dir, exist_ok=True)
        file_prefix = os.path.splitext(os.path.basename(self.input_file))[0]

        # Regex
        start_p = re.compile(r"WLDownDataStart\b", re.IGNORECASE)
        end_p = re.compile(r"WLDownDataEnd\b", re.IGNORECASE)
        val_p = re.compile(r"([-+]?\d+)$")
        meta_p = re.compile(r"CH:(\d+)\s*,\s*CE:(\d+)\s*,\s*DIE:(\d+)\s*,\s*Block:([0-9A-Fa-f]+)\s*,\s*Plane:(\d+)\s*,\s*WL:\s*([0-9A-Fa-f]+)", re.IGNORECASE)

        vt_data_map = {}
        inside_b, current_b, last_m, last_m_raw = False, [], None, None

        for raw in lines:
            line = raw.strip()
            m = meta_p.search(line)
            if m:
                last_m = {"ch": m.group(1), "ce": m.group(2), "die": m.group(3), "block": m.group(4), "plane": m.group(5), "wl": m.group(6)}
                last_m_raw = line
            
            if start_p.search(line):
                inside_b, current_b = True, []
                c_meta, c_meta_raw = last_m, last_m_raw
                continue

            if end_p.search(line):
                if inside_b and c_meta:
                    f_n = f"{file_prefix}_Ch{int(c_meta['ch'])}_Ce{int(c_meta['ce'])}_Die{int(c_meta['die'])}_Blk{c_meta['block']}_Plane{int(c_meta['plane'])}"
                    
                    # 依辨識結果轉換 WL 編號
                    wl_val = int(c_meta['wl'], 16) if hex_mode else int(c_meta['wl'], 10)
                    wl_key = f"WL{wl_val:04d}"
                    
                    if f_n not in vt_data_map: vt_data_map[f_n] = {}
                    vt_data_map[f_n][wl_key] = {"header": c_meta_raw, "values": current_b}
                inside_b = False
                continue

            if inside_b:
                mv = val_p.search(line)
                if mv: current_b.append(int(mv.group(1)))

        # 寫入檔案
        for folder_name, wls in vt_data_map.items():
            self.log(f"正在彙整: {folder_name}")
            folder_path = os.path.join(output_dir, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            
            excel_dict = {}
            sorted_keys = sorted(wls.keys())
            for wl_key in sorted_keys:
                content = wls[wl_key]
                # TXT 輸出
                with open(os.path.join(folder_path, f"{wl_key}.txt"), "w", encoding="utf-8") as out:
                    out.write(f"{content['header']}\nWLDownDataStart\n" + "\n".join(map(str, content['values'])) + "\nWLDownDataEnd\n")
                excel_dict[wl_key] = content['values']

            # Excel 彙總
            if excel_dict:
                df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in excel_dict.items()]))
                df = df.reindex(sorted(df.columns), axis=1)
                df.insert(0, "索引", range(len(df)))
                
                excel_path = os.path.join(output_dir, f"{folder_name}.xlsx")
                with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='彙總報告')
                    workbook, worksheet = writer.book, writer.sheets['彙總報告']
                    # 淡綠色表頭設定
                    header_fmt = workbook.add_format({'bg_color': '#D7E4BC', 'bold': True, 'border': 1, 'align': 'center'})
                    for col_num, val in enumerate(df.columns.values):
                        worksheet.write(0, col_num, val, header_fmt)
                        worksheet.set_column(col_num, col_num, 12)

        self.log(f"任務完成！檔案已存至輸入目錄下的 Vt_output。")
        self.run_btn.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VtParserGUI(); ex.show()
    sys.exit(app.exec())