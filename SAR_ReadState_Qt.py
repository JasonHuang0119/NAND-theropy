import sys, re, os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QFrame, QSplitter, QFileDialog, QLineEdit)
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QPalette
from PyQt6.QtCore import Qt, QTimer

class CozySarStudio(QWidget):
    def __init__(self):
        super().__init__()
        self.all_lines = []
        self.setAcceptDrops(True)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('NAND SAR - Cozy Edition')
        self.resize(1150, 850)
        
        # 莫蘭迪色系風格：低飽和度、舒適、專業
        self.setStyleSheet("""
            QWidget { 
                background-color: #EFEDE8; /* 暖灰偏米色背景 */
                font-family: 'Segoe UI', 'Microsoft JhengHei'; 
                color: #4A4A4A; 
            }
            
            /* 圓角白底卡片 */
            QFrame#PanelCard { 
                background-color: #FFFFFF; 
                border-radius: 12px; 
                border: 1px solid #DCD9D2;
            }
            
            /* 低調搜尋框 */
            QLineEdit { 
                background-color: #F7F6F3; border: 1px solid #CFCBC2; border-radius: 8px;
                padding: 10px; font-size: 14px; color: #4A4A4A;
            }
            QLineEdit:focus { border: 1px solid #A8A294; background-color: #FFFFFF; }
            
            /* 文字區 */
            QTextEdit { background-color: transparent; border: none; font-size: 13px; color: #5F5F5F; }
            
            /* 莫蘭迪綠色按鈕 */
            QPushButton#SoftBtn {
                background-color: #8E9775; color: white; border-radius: 8px;
                padding: 10px 20px; font-weight: 600; border: none;
            }
            QPushButton#SoftBtn:hover { background-color: #7A845F; }
            QPushButton#SoftBtn:pressed { background-color: #697252; }

            /* 輔助按鈕 */
            QPushButton#GhostBtn {
                background-color: #E2E0D9; color: #6B6B6B; border-radius: 8px;
                padding: 8px 15px; border: 1px solid #CFCBC2;
            }
            QPushButton#GhostBtn:hover { background-color: #D6D3CB; }

            QSplitter::handle { background-color: transparent; width: 10px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # 頂部：優雅的操作列
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

        # 左側：搜尋與過濾區
        left_box = QFrame(); left_box.setObjectName("PanelCard")
        left_layout = QVBoxLayout(left_box)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("輸入 WL= 編號後按 Enter 搜尋...")
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

        # 右側：數據分析儀表板
        right_box = QFrame(); right_box.setObjectName("PanelCard")
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        right_layout.addWidget(QLabel("✦ 解析對照 (DEC)", styleSheet="font-weight: bold; color: #8E9775;"))
        self.data_display = QTextEdit()
        self.data_display.setFont(QFont("Consolas", 11))
        self.data_display.setReadOnly(True)
        self.data_display.setStyleSheet("background-color: #FAF9F6; border-radius: 8px; border: 1px inset #E8E6E0;")
        right_layout.addWidget(self.data_display)

        right_layout.addSpacing(10)
        right_layout.addWidget(QLabel("✦ Excel 數據列", styleSheet="font-weight: bold; color: #8E9775;"))
        self.excel_output = QTextEdit()
        self.excel_output.setFixedHeight(160)
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

    # --- 檔案人性化處理 ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files: self.process_file_load(files[0])

    def manual_load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "開啟 Log 檔案")
        if path: self.process_file_load(path)

    def process_file_load(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.all_lines = [l.strip().replace('\xa0', ' ') for l in f.readlines()]
            self.file_info.setText(f"目前載入：{os.path.basename(path)}")
            self.log_viewer.setPlainText("檔案讀取完成。請在左上方輸入關鍵字。")
        except Exception as e:
            self.file_info.setText(f"錯誤：{e}")

    # --- 效能優化：Enter 才搜尋 ---
    def perform_filter(self):
        kw = self.search_input.text().lower().strip()
        if not kw: #假如搜尋框是空白，只顯示前 200 行，避免塞入過多卡頓。
            self.log_viewer.setPlainText("\n".join(self.all_lines[:200]))
            return
        
        display = []
        for i, line in enumerate(self.all_lines):
            if kw in line.lower():
                # 滿足需求：顯示當前行及其上下各一行 (共三行)
                start = max(0, i-1) # max(0, i-1) 防止第一行往前超出邊界
                end = min(len(self.all_lines), i+2) # min(len(...), i+2) 防止最後一行往後超出邊界，切出上下各一行的三行區塊。
                block = self.all_lines[start:end]
                display.append("\n".join(block))
                display.append("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄") # 柔和的虛線分隔
                
        self.log_viewer.setPlainText("\n".join(display))
        self.soft_highlight()

    def soft_highlight(self):
        """舒適的淡色高亮，不刺眼"""
        cursor = self.log_viewer.textCursor()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#F0F2E8")) # 淡淡的草綠色底
        fmt.setForeground(QColor("#7A845F")) # 深灰綠色字
        fmt.setFontWeight(QFont.Weight.Bold)
        regex = re.compile(r"S\d+R=[0-9A-F]+")
        text = self.log_viewer.toPlainText()
        self.log_viewer.blockSignals(True)
        for m in regex.finditer(text):
            cursor.setPosition(m.start())
            cursor.setPosition(m.end(), QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt)
        self.log_viewer.blockSignals(False)

    # --- 選取與解析 ---
    def on_log_click(self, event):
        QTextEdit.mousePressEvent(self.log_viewer, event)
        cursor = self.log_viewer.textCursor()
        text_lines = self.log_viewer.toPlainText().split('\n')
        row = cursor.blockNumber()
        
        # 在點擊行附近 2 行內自動搜尋數據行
        found_data = ""
        for i in range(max(0, row-2), min(len(text_lines), row+3)):
            if "S1R=" in text_lines[i]:
                found_data = text_lines[i]
                break
        
        if found_data:
            self.parse_and_show(found_data)

    def parse_and_show(self, raw_line):
        matches = re.findall(r"S(\d+)R=([0-9A-F]{1,2})", raw_line, re.IGNORECASE)
        if not matches: return
        
        sorted_m = sorted(matches, key=lambda x: int(x[0]))
        table, excel = "", []
        for idx, hv in sorted_m:
            val = int(hv, 16)
            dec = val - 0x100 if val >= 0x80 else val
            table += f"S{int(idx):<2}  ▷  HEX: {hv.upper():<2}  ▷  DEC: {dec:>4}\n"
            excel.append(str(dec))
        
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