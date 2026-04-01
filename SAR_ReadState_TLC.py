import sys, re, os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QFrame, QSplitter, QFileDialog, QLineEdit)
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
from PyQt6.QtCore import Qt, QTimer

class CozySarStudio(QWidget):
    def __init__(self):
        super().__init__()
        self.all_lines = []
        self.setAcceptDrops(True)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('NAND SAR TLC Edition - Cozy Studio')
        self.resize(1150, 850)
        
        # 莫蘭迪色系風格：低飽和度、舒適、專業
        self.setStyleSheet("""
            QWidget { 
                background-color: #EFEDE8; 
                font-family: 'Segoe UI', 'Microsoft JhengHei'; 
                color: #4A4A4A; 
            }
            QFrame#PanelCard { 
                background-color: #FFFFFF; 
                border-radius: 12px; 
                border: 1px solid #DCD9D2;
            }
            QLineEdit { 
                background-color: #F7F6F3; border: 1px solid #CFCBC2; border-radius: 8px;
                padding: 10px; font-size: 14px; color: #4A4A4A;
            }
            QLineEdit:focus { border: 1px solid #A8A294; background-color: #FFFFFF; }
            QTextEdit { background-color: transparent; border: none; font-size: 13px; color: #5F5F5F; }
            QPushButton#SoftBtn {
                background-color: #8E9775; color: white; border-radius: 8px;
                padding: 10px 20px; font-weight: 600; border: none;
            }
            QPushButton#SoftBtn:hover { background-color: #7A845F; }
            QPushButton#GhostBtn {
                background-color: #E2E0D9; color: #6B6B6B; border-radius: 8px;
                padding: 8px 15px; border: 1px solid #CFCBC2;
            }
            QPushButton#GhostBtn:hover { background-color: #D6D3CB; }
            QSplitter::handle { background-color: transparent; width: 10px; }
            
            /* 右側資訊面板 */
            QFrame#InfoBox {
                background-color: #F4F5F0;
                border-radius: 8px;
                border: 1px solid #E1E3D9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # 頂部操作列
        top_bar = QHBoxLayout()
        self.file_info = QLabel("尚未讀取 Log (可直接拖曳檔案至此)")
        self.file_info.setStyleSheet("color: #8C8C8C; font-size: 13px;")
        
        self.btn_open = QPushButton("瀏覽檔案")
        self.btn_open.setObjectName("GhostBtn")
        self.btn_open.clicked.connect(self.manual_load_file)
        
        top_bar.addWidget(self.file_info)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_open)
        layout.addLayout(top_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # ================= 左側：搜尋與過濾區 =================
        left_box = QFrame(); left_box.setObjectName("PanelCard")
        left_layout = QVBoxLayout(left_box)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("輸入 WL=0001 (將自動為您整理出該 WL 所有最優 SAR 參數)...")
        self.search_input.returnPressed.connect(self.perform_filter)
        left_layout.addWidget(self.search_input)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Consolas", 10))
        self.log_viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_viewer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_viewer.mousePressEvent = self.on_log_click
        left_layout.addWidget(self.log_viewer)
        self.splitter.addWidget(left_box)

        # ================= 右側：數據分析儀表板 =================
        right_box = QFrame(); right_box.setObjectName("PanelCard")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # 優化：獨立的資訊面板 (更清楚顯示 WL 與 Order 類型)
        info_frame = QFrame(); info_frame.setObjectName("InfoBox")
        info_layout = QVBoxLayout(info_frame)
        self.info_wl_label = QLabel("✦ Word Line (WL): --")
        self.info_wl_label.setStyleSheet("font-weight: bold; color: #7A845F; font-size: 15px;")
        self.info_target_label = QLabel("✦ 參數目標: --")
        self.info_target_label.setStyleSheet("font-weight: bold; color: #D4A373; font-size: 16px;")
        info_layout.addWidget(self.info_wl_label)
        info_layout.addWidget(self.info_target_label)
        right_layout.addWidget(info_frame)

        right_layout.addSpacing(10)

        right_layout.addWidget(QLabel("✦ 解析對照 (A~G DEC)", styleSheet="font-weight: bold; color: #8E9775;"))
        self.data_display = QTextEdit()
        self.data_display.setFont(QFont("Consolas", 11))
        self.data_display.setReadOnly(True)
        self.data_display.setStyleSheet("background-color: #FAF9F6; border-radius: 8px; border: 1px inset #E8E6E0;")
        right_layout.addWidget(self.data_display)

        right_layout.addSpacing(10)
        right_layout.addWidget(QLabel("✦ Excel 數據列", styleSheet="font-weight: bold; color: #8E9775;"))
        self.excel_output = QTextEdit()
        self.excel_output.setFixedHeight(180)
        self.excel_output.setReadOnly(True)
        self.excel_output.setStyleSheet("background-color: #FAF9F6; border-radius: 8px; border: 1px inset #E8E6E0; color: #7A845F;")
        right_layout.addWidget(self.excel_output)

        self.btn_copy = QPushButton("一鍵複製數據")
        self.btn_copy.setObjectName("SoftBtn")
        self.btn_copy.clicked.connect(self.copy_result)
        right_layout.addWidget(self.btn_copy)

        self.splitter.addWidget(right_box)
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)
        layout.addWidget(self.splitter)

    # --- 檔案載入 ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files: self.process_file_load(files[0])

    def manual_load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "開啟 TLC Log 檔案")
        if path: self.process_file_load(path)

    def process_file_load(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.all_lines = [l.strip().replace('\xa0', ' ') for l in f.readlines()]
            self.file_info.setText(f"目前載入：{os.path.basename(path)}")
            self.log_viewer.setPlainText("TLC 檔案讀取完成。請在左上方輸入 WL= 進行精準搜尋。")
        except Exception as e:
            self.file_info.setText(f"錯誤：{e}")

    # --- 優化版：區塊淨化過濾 ---
    def perform_filter(self):
        kw = self.search_input.text().upper().strip()
        if not kw: 
            self.log_viewer.setPlainText("\n".join(self.all_lines[:200]))
            return
        
        display = []
        in_target_wl_block = False

        for line in self.all_lines:
            # 如果這行是 WL 開頭的標記行
            if "WL=" in line.upper():
                if kw in line.upper():
                    in_target_wl_block = True
                    display.append("\n" + "━" * 55) # 加入明顯的分隔線 (如 LSB/CSB 切換)
                    display.append(line) # 印出 WL 標題行
                else:
                    # 遇到不是目標的 WL，關閉區塊收集
                    in_target_wl_block = False
            
            # 如果在目標 WL 區塊內，我們只收集有用的參數行
            elif in_target_wl_block:
                if "ORDER" in line.upper() or "AR=" in line.upper():
                    display.append(line)

        # 如果找不到特定 WL 格式，退回一般搜尋
        if not display:
            for i, line in enumerate(self.all_lines):
                if kw in line.upper():
                    start, end = max(0, i-2), min(len(self.all_lines), i+3)
                    display.append("\n".join(self.all_lines[start:end]))
                    display.append("┄" * 40)

        self.log_viewer.setPlainText("\n".join(display) if display else "查無資料")
        self.soft_highlight()

    def soft_highlight(self):
        """舒適的高亮顯示：標註 AR~GR 與 MinSAR"""
        cursor = self.log_viewer.textCursor()
        
        # 高亮 A~G 電壓
        fmt_voltage = QTextCharFormat()
        fmt_voltage.setBackground(QColor("#F0F2E8")) 
        fmt_voltage.setForeground(QColor("#7A845F")) 
        fmt_voltage.setFontWeight(QFont.Weight.Bold)
        
        # 高亮 MinSAR 與 Order
        fmt_target = QTextCharFormat()
        fmt_target.setForeground(QColor("#D4A373"))
        fmt_target.setFontWeight(QFont.Weight.Bold)

        text = self.log_viewer.toPlainText()
        self.log_viewer.blockSignals(True)
        
        # 標記電壓
        for m in re.finditer(r"[A-G]R=[0-9A-F]{1,2}", text, re.IGNORECASE):
            cursor.setPosition(m.start())
            cursor.setPosition(m.end(), QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt_voltage)
            
        # 標記 Order 關鍵字
        for m in re.finditer(r"(MinSAR order_\d+|[A-Z]+_SAR_\d+th order)", text, re.IGNORECASE):
            cursor.setPosition(m.start())
            cursor.setPosition(m.end(), QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt_target)

        self.log_viewer.blockSignals(False)

    # --- 選取與解析 ---
    def on_log_click(self, event):
        QTextEdit.mousePressEvent(self.log_viewer, event)
        cursor = self.log_viewer.textCursor()
        text_lines = self.log_viewer.toPlainText().split('\n')
        row = cursor.blockNumber()
        if row >= len(text_lines): return
        
        # 在點擊行附近自動搜尋含有 AR= 且包含 order 的數據行
        found_data = ""
        for i in range(max(0, row-1), min(len(text_lines), row+2)):
            if "AR=" in text_lines[i].upper() and ("ORDER" in text_lines[i].upper() or "MINSAR" in text_lines[i].upper()):
                found_data = text_lines[i]
                break
        
        if found_data:
            # 1. 向上溯源尋找最近的 WL 編號
            target_wl = "??"
            for i in range(row, -1, -1):
                match_wl = re.search(r"WL=(\d+)", text_lines[i], re.IGNORECASE)
                if match_wl:
                    target_wl = match_wl.group(1)
                    break
            
            # 2. 精確擷取「是哪一種 Order」(例如 LSB_SAR_5th order 或 MinSAR order_3)
            # 利用正規表達式抓取冒號 ':' 前面的所有文字特徵
            match_identity = re.search(r"([A-Za-z0-9_]+(?:\s*order(?:_\d+)?))", found_data, re.IGNORECASE)
            target_identity = match_identity.group(1).strip() if match_identity else "Unknown Order"
            
            # 更新右側標題 (明確顯示)
            self.info_wl_label.setText(f"✦ Word Line (WL): {target_wl}")
            self.info_target_label.setText(f"✦ 參數目標: {target_identity}")
            
            # 進行 TLC 解析
            self.parse_and_show(found_data)

    def parse_and_show(self, raw_line):
        matches = re.findall(r"([A-G])R=([0-9A-F]{1,2})", raw_line, re.IGNORECASE)
        if not matches: return
        
        val_dict = {m[0].upper(): m[1].upper() for m in matches}
        table, excel = "", []
        
        for key in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            if key in val_dict:
                hv = val_dict[key]
                val = int(hv, 16)
                dec = val - 0x100 if val >= 0x80 else val
                table += f" {key}R  ▷  HEX: {hv:<2}  ▷  DEC: {dec:>4}\n"
                excel.append(str(dec))
            else:
                table += f" {key}R  ▷  Missing\n"
                excel.append("0")
        
        self.data_display.setPlainText(table)
        self.excel_output.setPlainText("\n".join(excel))

    def copy_result(self):
        QApplication.clipboard().setText(self.excel_output.toPlainText())
        self.btn_copy.setText("已成功複製")
        QTimer.singleShot(1000, lambda: self.btn_copy.setText("一鍵複製數據"))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CozySarStudio()
    ex.show()
    sys.exit(app.exec())