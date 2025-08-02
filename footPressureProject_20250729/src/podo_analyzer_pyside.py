import sys
import os
import glob
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QPixmap, QFont, QPainter
from PySide6.QtCore import Qt

# 실시간 분석을 위한 모듈 추가
from analyzer_engine import FootPressureAnalyzer
import numpy as np

class PodoAnalysisAppPySide(QWidget):
    """
    족저압 분석 GUI 애플리케이션 (PySide6 기반)
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("족저압 분석기 v3.2 (PySide6 - 결과 테이블 추가)")
        self.setGeometry(100, 100, 1000, 700) # 창 기본 크기 확장
        
        self.input_path = ""
        self.current_report_path = None # 현재 표시된 리포트 경로 저장
        self._init_ui()
        self._log_message("프로그램이 시작되었습니다.")
    
    def _init_ui(self):
        # --- 레이아웃 설정 ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        control_layout = QHBoxLayout()
        results_layout = QHBoxLayout() # 이미지와 테이블을 담을 레이아웃

        # --- 위젯 생성 ---
        self.btn_input_path = QPushButton("inputPath")
        self.btn_analyze = QPushButton("Analyze Podo")
        self.path_label = QLabel("선택된 경로: 없음")
        self.image_label = QLabel("분석 결과가 여기에 표시됩니다")
        self.results_table = QTableWidget()
        self.log_text = QTextEdit()

        # --- 컨트롤 버튼 설정 ---
        self.btn_input_path.setFont(QFont("Arial", 12))
        self.btn_input_path.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 20px;")
        self.btn_input_path.clicked.connect(self.select_input_path)
        
        self.btn_analyze.setFont(QFont("Arial", 12))
        self.btn_analyze.setStyleSheet("background-color: #2196F3; color: white; padding: 10px 20px;")
        self.btn_analyze.clicked.connect(self.analyze_podo)
        
        control_layout.addWidget(self.btn_input_path)
        control_layout.addWidget(self.btn_analyze)
        control_layout.addStretch(1)

        # 'Print' 버튼 추가
        self.btn_print = QPushButton("Print")
        self.btn_print.setFont(QFont("Arial", 12))
        self.btn_print.setStyleSheet("background-color: #f44336; color: white; padding: 10px 20px;")
        self.btn_print.clicked.connect(self.print_widget)
        control_layout.addWidget(self.btn_print)

        # 'Exit' 버튼 추가
        self.btn_exit = QPushButton("Exit")
        self.btn_exit.setFont(QFont("Arial", 12))
        self.btn_exit.setStyleSheet("background-color: #607D8B; color: white; padding: 10px 20px;")
        self.btn_exit.clicked.connect(self.close)
        control_layout.addWidget(self.btn_exit)

        # --- 경로 라벨 설정 ---
        self.path_label.setFont(QFont("Arial", 10))

        # --- 결과 표시부 (이미지 + 테이블) ---
        self.image_label.setMinimumSize(600, 400)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: lightgray; border: 2px solid gray;")
        self._setup_results_table() # 테이블 초기화

        results_layout.addWidget(self.image_label, 2) # 이미지 영역이 2/3 차지
        results_layout.addWidget(self.results_table, 1) # 테이블 영역이 1/3 차지

        # --- 로그 박스 설정 ---
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(100)
        
        # --- 메인 레이아웃에 위젯 추가 ---
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.path_label)
        main_layout.addLayout(results_layout, 1) # 결과 영역이 늘어나도록 설정
        main_layout.addWidget(QLabel("로그:"))
        main_layout.addWidget(self.log_text)

    def _setup_results_table(self):
        """결과 테이블의 초기 모양을 설정합니다."""
        self.results_table.setRowCount(5)
        self.results_table.setColumnCount(3)
        
        self.results_table.setHorizontalHeaderLabels(["항목", "왼쪽 발", "오른쪽 발"])
        self.results_table.verticalHeader().setVisible(False)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        items = ["상태", "아치 지수 (AI)", "뒤 압력 (%)", "중간 압력 (%)", "앞 압력 (%)"]
        for i, item_text in enumerate(items):
            item = QTableWidgetItem(item_text)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(i, 0, item)
        
        self._clear_results_table()

    def _clear_results_table(self):
        """결과 테이블의 데이터 영역을 '-'로 초기화합니다."""
        for row in range(self.results_table.rowCount()):
            for col in range(1, self.results_table.columnCount()):
                self.results_table.setItem(row, col, self._create_table_item("-"))

    def _update_results_table(self, analysis_results):
        """분석 결과를 테이블에 채워 넣습니다."""
        if not analysis_results:
            self._clear_results_table()
            return
            
        foot_types = analysis_results.get('foot_types', {})
        distribution = analysis_results.get('distribution', {})
        
        data_map = {
            '왼쪽': {'col': 1, 'prefix': 'L'},
            '오른쪽': {'col': 2, 'prefix': 'R'}
        }
        
        for foot_key, foot_info in data_map.items():
            col_idx = foot_info['col']
            prefix = foot_info['prefix']
            
            foot_type_data = foot_types.get(foot_key, {})
            
            type_text = foot_type_data.get('type', 'N/A').split(' ')[0]
            arch_index = foot_type_data.get('value', 0)
            hind_pressure = distribution.get(f'{prefix}H', 0)
            mid_pressure = distribution.get(f'{prefix}M', 0)
            fore_pressure = distribution.get(f'{prefix}F', 0)
            
            self.results_table.setItem(0, col_idx, self._create_table_item(type_text))
            self.results_table.setItem(1, col_idx, self._create_table_item(f"{arch_index:.3f}"))
            self.results_table.setItem(2, col_idx, self._create_table_item(f"{hind_pressure:.1f}"))
            self.results_table.setItem(3, col_idx, self._create_table_item(f"{mid_pressure:.1f}"))
            self.results_table.setItem(4, col_idx, self._create_table_item(f"{fore_pressure:.1f}"))

    def _create_table_item(self, text):
        """테이블에 들어갈 아이템(셀)을 생성하고 기본 속성을 설정합니다."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item
        
    def _log_message(self, message):
        if message.startswith("[ENGINE]"):
            log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        else:
            log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] [GUI] {message}"
        
        self.log_text.append(log_entry)
        print(log_entry)

    def select_input_path(self):
        self._log_message("inputPath 버튼이 클릭되었습니다.")
        self._clear_results()
        
        initial_dir = os.path.join(os.getcwd(), 'data', 'input')
        file_path, _ = QFileDialog.getOpenFileName(
            self, "족저압 데이터 파일 선택",
            initial_dir if os.path.exists(initial_dir) else os.getcwd(),
            "JSON files (*.json);;All files (*.*)"
        )
        
        if file_path:
            self.input_path = file_path
            filename = os.path.basename(file_path)
            self.path_label.setText(f"선택된 경로: {filename}")
            self._log_message(f"파일이 선택되었습니다: {filename}")
        else:
            self._log_message("파일 선택이 취소되었습니다.")
            
    def analyze_podo(self):
        self._log_message("Analyze Podo 버튼이 클릭되었습니다.")
        
        if not self.input_path:
            QMessageBox.warning(self, "경고", "먼저 inputPath 버튼을 클릭하여 파일을 선택해주세요.")
            self._log_message("경고: 파일이 선택되지 않았습니다.")
            return
            
        self._log_message(f"분석을 시작합니다: {os.path.basename(self.input_path)}")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            analyzer = FootPressureAnalyzer(self.input_path, ui_logger=self._log_message)
            if not analyzer.run_analysis():
                QMessageBox.critical(self, "분석 오류", analyzer.error_message or "알 수 없는 오류 발생")
                return

            vis_data = analyzer.get_visualization_data()
            if not vis_data:
                QMessageBox.warning(self, "경고", "시각화 데이터를 생성할 수 없습니다.")
                return

            vis_data['pressure_data'] = np.array(vis_data['pressure_data'])

            reports_dir = os.path.join(os.path.dirname(os.path.dirname(self.input_path)),'output','analysis_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            input_basename = os.path.splitext(os.path.basename(self.input_path))[0]
            output_filename = f"{input_basename}_{timestamp}_report.png"
            output_path = os.path.join(reports_dir, output_filename)

            analyzer.save_visualization(output_path, vis_data)
            
            self._update_results_table(vis_data.get('analysis_results'))
            self.current_report_path = output_path
            self._display_analysis_image(output_path)
            self._log_message(f"분석 완료: {output_filename}")

        except Exception as e:
            QMessageBox.critical(self, "치명적 오류", f"분석 중 예외가 발생했습니다: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _display_analysis_image(self, image_path, is_resize=False):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self._log_message(f"이미지 로드 실패: {image_path}")
            return

        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        if not is_resize:
             self._log_message("이미지가 성공적으로 표시되었습니다.")

    def _clear_results(self):
        """이미지와 테이블을 모두 초기화합니다."""
        self.image_label.clear()
        self.image_label.setText("분석 결과가 여기에 표시됩니다")
        self.current_report_path = None
        self._clear_results_table()
        self._log_message("이전 분석 결과가 제거되었습니다.")

    def print_widget(self):
        """'Print' 버튼 클릭 시 현재 위젯의 내용을 프린트합니다."""
        self._log_message("프린트 버튼이 클릭되었습니다.")
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.Accepted:
            pixmap = self.grab()
            painter = QPainter(printer)
            rect = painter.viewport()
            size = pixmap.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(pixmap.rect())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            self._log_message("인쇄가 프린터로 전송되었습니다.")
        else:
            self._log_message("인쇄가 취소되었습니다.")

    def resizeEvent(self, event):
        if self.image_label.pixmap() and self.current_report_path:
            self._display_analysis_image(self.current_report_path, is_resize=True)
        super().resizeEvent(event)

def main():
    print("=== 족저압 분석기 v3.2 (PySide6) 시작 ===")
    app = QApplication(sys.argv)
    window = PodoAnalysisAppPySide()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
