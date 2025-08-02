import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import glob
from datetime import datetime

class PodoAnalysisApp(tk.Tk):
    """
    족저압 분석 GUI 애플리케이션
    요구사항에 맞춘 단순한 인터페이스 제공
    """
    def __init__(self):
        print("PodoAnalysisApp.__init__() 시작")
        
        try:
            super().__init__()
            print("tkinter.Tk 초기화 완료")
            
            self.title("족저압 분석기 v2.0")
            self.geometry("800x600")
            print("창 제목 및 크기 설정 완료")
            
            # 입력 경로 저장
            self.input_path = ""
            self.current_image = None
            print("변수 초기화 완료")
            
            # UI 위젯 생성
            print("UI 위젯 생성 시작...")
            self._create_widgets()
            print("UI 위젯 생성 완료")
            
            self._log_message("프로그램이 시작되었습니다.")
            print("PodoAnalysisApp.__init__() 완료")
            
        except Exception as e:
            print(f"PodoAnalysisApp.__init__() 에러: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _create_widgets(self):
        """UI 위젯들을 생성합니다."""
        # 메인 프레임
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단 컨트롤 프레임
        control_frame = tk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # inputPath 버튼
        self.btn_input_path = tk.Button(
            control_frame, 
            text="inputPath", 
            font=("Arial", 12),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=10,
            command=self.select_input_path
        )
        self.btn_input_path.pack(side=tk.LEFT, padx=(0, 10))
        
        # Analyze Podo 버튼
        self.btn_analyze = tk.Button(
            control_frame,
            text="Analyze Podo",
            font=("Arial", 12),
            bg="#2196F3",
            fg="white", 
            padx=20,
            pady=10,
            command=self.analyze_podo
        )
        self.btn_analyze.pack(side=tk.LEFT)
        
        # 경로 표시 라벨
        self.path_label = tk.Label(
            main_frame,
            text="선택된 경로: 없음",
            font=("Arial", 10),
            fg="gray",
            anchor="w"
        )
        self.path_label.pack(fill=tk.X, pady=(0, 20))
        
        # 이미지 표시 프레임
        self.image_frame = tk.Frame(main_frame, bg="lightgray", relief=tk.SUNKEN, bd=2)
        self.image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 이미지 라벨 (초기에는 빈 상태)
        self.image_label = tk.Label(
            self.image_frame,
            text="분석 결과가 여기에 표시됩니다",
            font=("Arial", 14),
            fg="darkgray"
        )
        self.image_label.pack(expand=True)
        
        # 하단 로그 프레임
        log_frame = tk.LabelFrame(main_frame, text="로그", padx=10, pady=10)
        log_frame.pack(fill=tk.X)
        
        # 로그 텍스트
        self.log_text = tk.Text(log_frame, height=5, wrap=tk.WORD, state=tk.DISABLED)
        log_scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def _log_message(self, message):
        """로그 메시지를 출력합니다."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # UI 로그에 추가
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 터미널에도 출력 [[memory:4703375]]
        print(log_entry)
    
    def select_input_path(self):
        """inputPath 버튼 클릭 시 실행되는 함수"""
        self._log_message("inputPath 버튼이 클릭되었습니다.")
        
        # 기존 이미지 제거
        self._clear_image()
        
        # 파일 선택 다이얼로그 열기
        initial_dir = os.path.join(os.getcwd(), 'footPressureProject_20250729', 'data', 'input')
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir if os.path.exists(initial_dir) else os.getcwd(),
            title="족저압 데이터 파일 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.input_path = file_path
            filename = os.path.basename(file_path)
            self.path_label.config(text=f"선택된 경로: {filename}")
            self._log_message(f"파일이 선택되었습니다: {filename}")
        else:
            self._log_message("파일 선택이 취소되었습니다.")
    
    def analyze_podo(self):
        """Analyze Podo 버튼 클릭 시 실행되는 함수"""
        self._log_message("Analyze Podo 버튼이 클릭되었습니다.")
        
        if not self.input_path:
            messagebox.showwarning("경고", "먼저 inputPath 버튼을 클릭하여 파일을 선택해주세요.")
            self._log_message("경고: 파일이 선택되지 않았습니다.")
            return
        
        self._log_message("분석을 시작합니다...")
        
        # 해당하는 분석 리포트 이미지 찾기
        report_image_path = self._find_analysis_report_image()
        
        if report_image_path:
            self._display_analysis_image(report_image_path)
            self._log_message(f"분석 완료: {os.path.basename(report_image_path)}")
        else:
            messagebox.showwarning("경고", "해당 파일에 대한 분석 리포트를 찾을 수 없습니다.")
            self._log_message("경고: 분석 리포트를 찾을 수 없습니다.")
    
    def _find_analysis_report_image(self):
        """입력 파일에 해당하는 분석 리포트 이미지를 찾습니다."""
        if not self.input_path:
            return None
        
        # 입력 파일명에서 확장자 제거
        input_filename = os.path.basename(self.input_path)
        base_name = os.path.splitext(input_filename)[0]  # .json 제거
        
        # analysis_reports 폴더 경로
        reports_dir = os.path.join(
            os.path.dirname(os.path.dirname(self.input_path)),  # data 폴더
            'output', 
            'analysis_reports'
        )
        
        if not os.path.exists(reports_dir):
            self._log_message(f"분석 리포트 폴더를 찾을 수 없습니다: {reports_dir}")
            return None
        
        # 해당 파일명으로 시작하는 리포트 이미지 찾기
        pattern = os.path.join(reports_dir, f"{base_name}_*_report.png")
        matching_files = glob.glob(pattern)
        
        if matching_files:
            # 가장 최근 파일 선택 (파일명에 날짜/시간이 포함되어 있으므로)
            latest_file = max(matching_files, key=os.path.getctime)
            self._log_message(f"분석 리포트 이미지를 찾았습니다: {os.path.basename(latest_file)}")
            return latest_file
        else:
            self._log_message(f"패턴에 맞는 파일이 없습니다: {pattern}")
            return None
    
    def _display_analysis_image(self, image_path):
        """분석 결과 이미지를 UI에 표시합니다."""
        try:
            # PIL로 이미지 로드
            pil_image = Image.open(image_path)
            
            # 이미지 크기를 프레임에 맞게 조정
            frame_width = 600
            frame_height = 400
            
            # 비율을 유지하면서 크기 조정
            pil_image.thumbnail((frame_width, frame_height), Image.Resampling.LANCZOS)
            
            # Tkinter에서 사용할 수 있는 형태로 변환
            self.current_image = ImageTk.PhotoImage(pil_image)
            
            # 이미지 라벨 업데이트
            self.image_label.config(
                image=self.current_image,
                text=""  # 텍스트 제거
            )
            
            self._log_message("이미지가 성공적으로 표시되었습니다.")
            
        except Exception as e:
            self._log_message(f"이미지 표시 오류: {str(e)}")
            messagebox.showerror("오류", f"이미지를 표시하는 중 오류가 발생했습니다:\n{str(e)}")
    
    def _clear_image(self):
        """현재 표시된 이미지를 제거합니다."""
        self.current_image = None
        self.image_label.config(
            image="",
            text="분석 결과가 여기에 표시됩니다"
        )
        self._log_message("이전 분석 결과가 제거되었습니다.")

def main():
    """메인 함수"""
    print("=== 족저압 분석기 v2.0 시작 ===")
    
    try:
        print("PodoAnalysisApp 인스턴스 생성 중...")
        app = PodoAnalysisApp()
        print("GUI 창 시작 중...")
        app.mainloop()
        print("GUI가 정상적으로 종료되었습니다.")
        
    except Exception as e:
        print(f"GUI 앱 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        input("Enter를 눌러 종료하세요...")

if __name__ == "__main__":
    main()