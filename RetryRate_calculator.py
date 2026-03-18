import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QFrame, QGridLayout)
from PyQt6.QtCore import Qt

class NANDAdvancedCalc(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('BiCS8 Reliability Analysis Tool')
        self.setFixedWidth(520)
        self.setStyleSheet("""
            QWidget { background-color: #f0f2f5; font-family: 'Segoe UI', sans-serif; }
            QFrame#MainCard { 
                background-color: white; border-radius: 12px; 
                border: 1px solid #dce1e6; padding: 10px;
            }
            QLabel#Header { 
                font-size: 22px; font-weight: bold; color: #1a1a1b; 
                margin-bottom: 15px; 
            }
            QLabel#FieldLabel { font-size: 12px; color: #5f6368; font-weight: bold; text-transform: uppercase; }
            QLineEdit { 
                padding: 12px; border: 1px solid #ced4da; border-radius: 6px; 
                font-size: 15px; background: #fafafa; margin-bottom: 5px;
            }
            QLineEdit:focus { border: 2px solid #409eff; background: white; }
            QPushButton { 
                background-color: #007bff; color: white; border: none; 
                padding: 15px; border-radius: 6px; font-size: 16px; font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #0069d9; }
            QLabel#OutputBox { 
                background-color: #ffffff; border-radius: 8px; border-left: 5px solid #409eff;
                padding: 20px; font-size: 14px; color: #2c3e50;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)

        # 標題
        header = QLabel("Reliability Proposal Calculator")
        header.setObjectName("Header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # 輸入區域卡片
        input_card = QFrame()
        input_card.setObjectName("MainCard")
        grid = QGridLayout(input_card)
        grid.setSpacing(10)

        # 1. HB 330bit
        grid.addWidget(QLabel("HB 330 bit"), 0, 0)
        self.in_hb = QLineEdit("330")
        grid.addWidget(self.in_hb, 0, 1)

        # 2. N4SB 600bit
        grid.addWidget(QLabel("N4SB 600 bit"), 1, 0)
        self.in_n4sb = QLineEdit("600")
        grid.addWidget(self.in_n4sb, 1, 1)

        # 3. Total Input
        grid.addWidget(QLabel("TOTAL (Sum/Raw)"), 2, 0)
        self.in_total = QLineEdit("930")
        grid.addWidget(self.in_total, 2, 1)

        layout.addWidget(input_card)

        # 計算按鈕
        self.btn = QPushButton("CALCULATE REFRESH PROBABILITY")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self.run_calc)
        layout.addWidget(self.btn)

        # 結果顯示
        self.out_area = QLabel("Enter values and click calculate...")
        self.out_area.setObjectName("OutputBox")
        self.out_area.setWordWrap(True)
        layout.addWidget(self.out_area)

        self.setLayout(layout)

    def run_calc(self):
        try:
            # 參數設定
            DIV_SINGLE = 34880
            DIV_TOTAL = 34880 * 4  # 139,520
            EXP = 218 * 5 * 1      # 1090

            # 讀取數值
            v_hb = float(self.in_hb.text())
            v_n4sb = float(self.in_n4sb.text())
            v_total = float(self.in_total.text())

            # 計算 Retry Rates
            r_hb = v_hb / DIV_SINGLE
            r_n4sb = v_n4sb / DIV_SINGLE
            r_total = v_total / DIV_TOTAL

            # 計算 Refresh Probabilities
            p_hb = 1 - pow((1 - r_hb), EXP)
            p_n4sb = 1 - pow((1 - r_n4sb), EXP)
            p_total = 1 - pow((1 - r_total), EXP)

            # 動態顯色邏輯 (判定風險)
            def get_style(p): return "color:#d9534f; font-weight:bold;" if p > 0.6 else "color:#5cb85c;"

            res_html = f"""
            <div style='line-height:1.8;'>
                <b style='font-size:16px; color:#333;'>📈 Results Analysis</b><hr>
                <b>[HB 330bit]</b> (Base: 34,880)<br>
                &nbsp;&nbsp;• Retry Rate: <span style='color:#007bff;'>{r_hb:.4%}</span><br>
                &nbsp;&nbsp;• Refresh Prob: <span style='{get_style(p_hb)}'>{p_hb:.2%}</span><br><br>
                
                <b>[N4SB 600bit]</b> (Base: 34,880)<br>
                &nbsp;&nbsp;• Retry Rate: <span style='color:#007bff;'>{r_n4sb:.4%}</span><br>
                &nbsp;&nbsp;• Refresh Prob: <span style='{get_style(p_n4sb)}'>{p_n4sb:.2%}</span><br><br>
                
                <b style='background:#e7f3ff; padding:2px;'>[TOTAL]</b> (Base: 139,520)<br>
                &nbsp;&nbsp;• Retry Rate: <span style='color:#007bff;'>{r_total:.4%}</span><br>
                &nbsp;&nbsp;• Refresh Prob: <span style='{get_style(p_total)}'>{p_total:.2%}</span>
            </div>
            """
            self.out_area.setText(res_html)

        except Exception as e:
            self.out_area.setText(f"<b style='color:red;'>⚠️ Input Error:</b><br>{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = NANDAdvancedCalc()
    win.show()
    sys.exit(app.exec())