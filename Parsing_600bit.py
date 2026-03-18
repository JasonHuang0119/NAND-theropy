import sys, re, os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QGroupBox, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt

class EccCorrelationAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.files = [None] * 4 
        self.a_thresh = 600   
        self.b_thresh = 1000  
        self.group_a_all_pages = [] 
        self.group_b_all_pages = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('NAND ECC Correlation Analyzer (X:40k, Y:60k) - Plane Aware')
        self.resize(1200, 900)
        self.setStyleSheet("""
            QWidget { background-color: #EFEDE8; font-family: 'Consolas', 'Microsoft JhengHei'; }
            QGroupBox { font-weight: bold; border: 1px solid #DCD9D2; margin-top: 10px; padding: 10px; }
            QPushButton { background-color: #8E9775; color: white; border-radius: 5px; padding: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #7A845F; }
            QTextEdit { background-color: #FAF9F6; border: 1px solid #E8E6E0; font-size: 12px; }
        """)

        layout = QVBoxLayout(self)
        fg = QGroupBox(f"1. 檔案載入 (逆推條件: 60k 任意 Page >= {self.b_thresh})")
        fl = QVBoxLayout(fg)
        
        p1, p2 = QHBoxLayout(), QHBoxLayout()
        labels = ['A1 (40k)', 'A2 (60k)', 'B1 (40k)', 'B2 (60k)']
        for i in range(4):
            btn = QPushButton(f"載入 {labels[i]}")
            setattr(self, f'btn_{i}', btn)
            btn.clicked.connect(lambda checked, idx=i: self.select_file(idx))
            if i < 2: p1.addWidget(btn)
            else: p2.addWidget(btn)
        fl.addLayout(p1); fl.addLayout(p2); layout.addWidget(fg)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("執行分析並顯示文字報告")
        self.run_btn.setStyleSheet("background-color: #6D8299; height: 45px;")
        self.run_btn.clicked.connect(self.start_analysis)
        
        self.export_btn = QPushButton("匯出 Excel 散佈圖 (按 Plane+WL 分色)")
        self.export_btn.setStyleSheet("background-color: #4CAF50; height: 45px;")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_to_excel)
        
        btn_layout.addWidget(self.run_btn); btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.result_area)

    def select_file(self, idx):
        path, _ = QFileDialog.getOpenFileName(self, "開啟 Log 檔案")
        if path:
            self.files[idx] = path
            btns = [self.btn_0, self.btn_1, self.btn_2, self.btn_3]
            btns[idx].setText(os.path.basename(path))

    def parse_section4(self, path):
        if not path or not os.path.exists(path): return {}
        data = {}
        interval_id = 1
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i in range(len(lines)):
            line = lines[i].strip()
            if "MinFBC_SAR_order" in line and i + 2 < len(lines):
                c_pos, c_ecc = lines[i+1].strip(), lines[i+2].strip()
                p_match = re.search(r"Plane=(\w+),WL=(\w+)", c_pos)
                if p_match and interval_id == 4:
                    e_match = re.search(r"ECC\s*=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", c_ecc)
                    if e_match:
                        data[(p_match.group(1), p_match.group(2))] = [int(e_match.group(j)) for j in range(1, 5)]
                if p_match and "TOP" in c_pos and p_match.group(1)=="03" and p_match.group(2)=="1089":
                    interval_id += 1
        return data

    def start_analysis(self):
        if None in self.files: return
        d_a1 = self.parse_section4(self.files[0])
        d_a2 = self.parse_section4(self.files[1])
        d_b1 = self.parse_section4(self.files[2])
        d_b2 = self.parse_section4(self.files[3])

        report = ["=== NAND ECC 逆推詳細報告 (60k >= 1000) ===\n"]

        def process_group(d_early, d_late, label):
            targets = [k for k, v in d_late.items() if any(e >= self.b_thresh for e in v)]
            targets.sort(key=lambda x: (int(x[0]), int(x[1])))
            
            all_page_points = []
            res_text = [f"【{label}】", f"● 符合條件之位置數 (Plane+WL): {len(targets)}", "-" * 100]

            for k in targets:
                v_late = d_late[k]
                v_early = d_early.get(k, [0, 0, 0, 0])
                
                res_text.append(f"Plane {k[0]} | WL {k[1]:<5} | 40k: {v_early} | 60k: {v_late}")
                res_text.append("-" * 50)

                # 建立唯一 ID 用於繪圖分組
                unique_id = f"P{k[0]}_WL{k[1]}"

                for pg in range(4):
                    all_page_points.append({
                        'Series_ID': unique_id, # 用於 Excel 分組分色
                        'Plane': k[0],
                        'WL': k[1],
                        'Chunk': pg,
                        'X_40k': v_early[pg],
                        'Y_60k': v_late[pg]
                    })
            
            return "\n".join(res_text), all_page_points

        txt_a, self.group_a_all_pages = process_group(d_a1, d_a2, "第一組 A")
        txt_b, self.group_b_all_pages = process_group(d_b1, d_b2, "第二組 B")
        
        self.result_area.setPlainText("\n".join(report + [txt_a, "\n", txt_b]))
        self.export_btn.setEnabled(True)

    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "儲存散佈圖報告", "ECC_Correlation_Plane_WL.xlsx", "Excel Files (*.xlsx)")
        if not path: return

        try:
            with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                for sheet_name, data in [('Group_A', self.group_a_all_pages), ('Group_B', self.group_b_all_pages)]:
                    if not data: continue
                    df = pd.DataFrame(data)
                    # 數據寫入 Excel (Series_ID 在第一欄 B, 數據在 E, F 欄)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    worksheet = writer.sheets[sheet_name]
                    
                    chart = workbook.add_chart({'type': 'scatter'})
                    
                    # 依 Series_ID 分組畫點，確保不同 Plane 同 WL 是不同顏色
                    unique_ids = df['Series_ID'].unique()
                    for uid in unique_ids:
                        subset = df[df['Series_ID'] == uid]
                        # 找到該分組在 DataFrame 中的起始與結束列索引
                        start_row = subset.index[0] + 1
                        end_row = subset.index[-1] + 1
                        
                        chart.add_series({
                            'name':       uid,
                            'categories': [sheet_name, start_row, 4, end_row, 4], # X: X_40k (欄位索引 4)
                            'values':     [sheet_name, start_row, 5, end_row, 5], # Y: Y_60k (欄位索引 5)
                            'marker':     {'type': 'circle', 'size': 5},
                        })

                    chart.set_title({'name': f'ECC Correlation (X:40k, Y:60k) - {sheet_name}'})
                    chart.set_x_axis({'name': '40k FBC (X)', 'major_gridlines': {'visible': True}})
                    chart.set_y_axis({'name': '60k FBC (Y)', 'major_gridlines': {'visible': True}})
                    chart.set_legend({'position': 'right'})
                    
                    # 插入圖表並放大
                    worksheet.insert_chart('H2', chart, {'x_scale': 2.0, 'y_scale': 2.0})

            QMessageBox.information(self, "成功", f"散佈圖 Excel 報表已匯出！\n已根據 Plane 與 WL 區分顏色。")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出失敗: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EccCorrelationAnalyzer(); ex.show()
    sys.exit(app.exec())