import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading
import queue
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analyzer_engine import FootPressureAnalyzer
from config import OUTPUT_DIR, FONT_PROP, VISUALIZATION

class FootPressureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("족저압 분석기")
        self.geometry("1200x800")

        # 입력 파일 경로
        self.input_path = tk.StringVar()
        self.log_queue = queue.Queue()
        self.log_poller = None

        # UI 위젯 생성 및 배치
        self._create_widgets()

    def _create_widgets(self):
        # --- 메인 프레임 설정 ---
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # --- 상단 프레임 (파일 선택 및 실행) ---
        top_frame = tk.Frame(main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        top_frame.grid_columnconfigure(1, weight=1)

        tk.Label(top_frame, text="분석할 데이터 파일:").grid(row=0, column=0, padx=(0, 5))
        self.entry_path = tk.Entry(top_frame, textvariable=self.input_path)
        self.entry_path.grid(row=0, column=1, sticky="ew")

        self.btn_browse = tk.Button(top_frame, text="파일 찾기", command=self.browse_file)
        self.btn_browse.grid(row=0, column=2, padx=5)

        self.btn_run = tk.Button(top_frame, text="분석 실행", command=self.run_analysis)
        self.btn_run.grid(row=0, column=3, padx=5)

        # --- 결과 이미지 프레임 ---
        image_frame = tk.LabelFrame(main_frame, text="분석 결과", padx=10, pady=10)
        image_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        image_frame.grid_rowconfigure(0, weight=1)
        image_frame.grid_columnconfigure(0, weight=1)
        
        # --- 로그 프레임 ---
        log_frame = tk.LabelFrame(main_frame, text="분석 로그", padx=10, pady=10)
        log_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        # --- 하단 상태 표시줄 ---
        status_frame = tk.Frame(self, padx=10, pady=5)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # --- Matplotlib Canvas ---
        self.fig, self.ax = plt.subplots(figsize=(5, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=image_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # --- 로그 텍스트 ---
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.log_scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=self.log_scrollbar.set)
        
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # --- 상태 표시 라벨 ---
        self.status_label = tk.Label(status_frame, text="준비 완료", anchor="w")
        self.status_label.pack(fill=tk.X)

    def _process_log_queue(self):
        """주기적으로 로그 큐를 확인하여 UI를 업데이트합니다. UI 프리징을 방지하기 위해 한번에 최대 50개까지만 처리합니다."""
        for _ in range(50): # 한번에 최대 50개 메시지만 처리
            try:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            except queue.Empty:
                break # 큐가 비었으면 중단
        
        # 100ms 마다 다시 확인하도록 예약
        self.log_poller = self.after(100, self._process_log_queue)

    def _log_to_ui(self, message):
        """타임스탬프와 함께 UI 로그 큐에 메시지를 추가합니다."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        self.log_queue.put(f"[{timestamp}] {message}")

    def browse_file(self):
        initial_dir = os.path.join(os.getcwd(), 'data', 'input')
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="JSON 데이터 파일 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.input_path.set(file_path)
            self._log_to_ui(f"파일 선택됨: {os.path.basename(file_path)}")

    def run_analysis(self):
        print("\n[DEBUG] '분석 실행' 버튼 클릭됨.") # 터미널 디버그 로그
        input_path = self.input_path.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("오류", "유효한 파일을 먼저 선택해주세요.")
            return
        
        # UI 초기화
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self._log_to_ui("="*50)
        self._log_to_ui(f"분석 시작: {os.path.basename(input_path)}")
        self._log_to_ui("="*50)

        # 로그 큐 폴링 시작
        if self.log_poller:
            self.after_cancel(self.log_poller)
        self._process_log_queue()

        self.status_label.config(text="분석 중... 잠시만 기다려주세요.")
        self.btn_run.config(state=tk.DISABLED)
        self.btn_browse.config(state=tk.DISABLED)
        
        # 백그라운드 스레드에서 분석 실행
        # UI 로깅을 위해 self._log_to_ui 콜백을 전달
        thread = threading.Thread(target=self._threaded_analysis, args=(input_path, self._log_to_ui))
        thread.daemon = True
        thread.start()

    def _threaded_analysis(self, input_path, ui_logger):
        """백그라운드 스레드에서 실행될 분석 함수"""
        try:
            # 1. 분석기 인스턴스 생성 및 실행 (UI 로거 콜백 전달)
            analyzer = FootPressureAnalyzer(input_path, ui_logger=ui_logger)
            success = analyzer.run_analysis()
            
            if not success:
                 raise Exception("분석 실행에 실패했습니다. 데이터를 확인해주세요.")

            # 2. 시각화 데이터 가져오기
            ui_logger("시각화 데이터 생성 중...")
            vis_data = analyzer.get_visualization_data()
            if not vis_data:
                raise Exception("시각화 데이터를 생성할 수 없습니다.")
            ui_logger("시각화 데이터 생성 완료.")

            # 3. 메인 스레드에서 UI 업데이트 예약
            self.after(0, self.on_analysis_complete, vis_data, None)

        except Exception as e:
            # 오류 발생 시 메인 스레드에 오류 정보 전달
            ui_logger(f"오류 발생: {e}")
            self.after(0, self.on_analysis_complete, None, e)
            
    def on_analysis_complete(self, vis_data, error):
        """분석 완료 후 메인 스레드에서 호출될 콜백 함수"""
        # 로그 큐 폴링 중지
        if self.log_poller:
            self.after_cancel(self.log_poller)
            self.log_poller = None

        if error:
            self._log_to_ui("="*50)
            self._log_to_ui("분석이 오류와 함께 종료되었습니다.")
            self._log_to_ui("="*50)
            messagebox.showerror("분석 오류", f"분석 중 오류가 발생했습니다:\n{error}")
            self.status_label.config(text="오류 발생")
        else:
            self._log_to_ui("="*50)
            self._log_to_ui("분석이 성공적으로 완료되었습니다.")
            self._log_to_ui("="*50)
            # 결과 이미지 표시
            self.display_matplotlib_figure(vis_data)
            self.status_label.config(text=f"분석 완료!")

        # 버튼 다시 활성화
        self.btn_run.config(state=tk.NORMAL)
        self.btn_browse.config(state=tk.NORMAL)

    def display_matplotlib_figure(self, vis_data):
        """Matplotlib Figure를 Tkinter Canvas에 그립니다."""
        try:
            self.ax.clear()
            
            # 스레드에서 전달받은 리스트를 시각화를 위해 다시 Numpy 배열로 변환
            pressure_data_np = np.array(vis_data['pressure_data'])
            
            # 시각화 함수에 전달할 데이터 복사본 생성
            vis_data_for_drawing = vis_data.copy()
            vis_data_for_drawing['pressure_data'] = pressure_data_np

            self.ax.imshow(pressure_data_np, cmap=VISUALIZATION['CMAP'], interpolation='nearest')
            
            # 공통 시각화 로직 호출 (Numpy 배열이 포함된 데이터 전달)
            self._draw_details_on_ax(self.ax, vis_data_for_drawing)

            self.ax.set_title('Foot Pressure Analysis Report', fontproperties=FONT_PROP)
            self.ax.axis('off')
            
            self.fig.tight_layout(pad=0)
            
            self.canvas.draw()
            
        except Exception as e:
            self._log_to_ui(f"이미지 표시 오류: {e}")
            messagebox.showerror("이미지 표시 오류", f"결과 이미지를 표시하는 데 실패했습니다:\n{e}")

    def _draw_details_on_ax(self, ax, vis_data):
        """주어진 Matplotlib ax에 분석 결과를 그립니다."""
        rows, cols = vis_data['pressure_data'].shape
        mid_col = cols // 2
        
        results = vis_data.get('analysis_results', {})
        final_bbox = results.get('final_bbox')
        distribution = results.get('distribution', {})
        zones = results.get('zones')

        if final_bbox:
            min_r, max_r = final_bbox
            ax.axhspan(min_r, max_r, facecolor=VISUALIZATION['BBOX_COLOR'], alpha=VISUALIZATION['BBOX_ALPHA'])
            
            if zones:
                # 구역선 그리기
                hind_end_y = zones['mid']['start'] - 0.5
                mid_end_y = zones['fore']['start'] - 0.5
                ax.axhline(y=hind_end_y, xmin=0.05, xmax=0.95, color=VISUALIZATION['LINE_COLOR'], linestyle='--', linewidth=1)
                ax.axhline(y=mid_end_y, xmin=0.05, xmax=0.95, color=VISUALIZATION['LINE_COLOR'], linestyle='--', linewidth=1)

                # 압력 분포 텍스트 (구역에 맞춰 위치 조정)
                if distribution:
                    text_props = {'color': VISUALIZATION['FONT_COLOR_DIST'], 'fontsize': VISUALIZATION['FONT_SIZE_DIST'], 
                                       'ha': 'center', 'va': 'center', 'fontproperties': FONT_PROP}
                    
                    y_hind = (zones['hind']['start'] + zones['hind']['stop']) / 2
                    y_mid = (zones['mid']['start'] + zones['mid']['stop']) / 2
                    y_fore = (zones['fore']['start'] + zones['fore']['stop']) / 2

                    ax.text(mid_col * 0.5, y_hind, f"뒤: {distribution.get('LH', 0):.1f}%", **text_props)
                    ax.text(mid_col * 0.5, y_mid, f"중간: {distribution.get('LM', 0):.1f}%", **text_props)
                    ax.text(mid_col * 0.5, y_fore, f"앞: {distribution.get('LF', 0):.1f}%", **text_props)

                    ax.text(mid_col * 1.5, y_hind, f"뒤: {distribution.get('RH', 0):.1f}%", **text_props)
                    ax.text(mid_col * 1.5, y_mid, f"중간: {distribution.get('RM', 0):.1f}%", **text_props)
                    ax.text(mid_col * 1.5, y_fore, f"앞: {distribution.get('RF', 0):.1f}%", **text_props)

        foot_types = results.get('foot_types', {})
        if foot_types:
            text_props_type = {'color': VISUALIZATION['FONT_COLOR_TYPE'], 'fontsize': VISUALIZATION['FONT_SIZE_TYPE'], 'ha': 'center', 'weight': 'bold', 'fontproperties': FONT_PROP}
            left_info = foot_types.get('left')
            if left_info and left_info['type'] not in ["데이터 없음", "데이터 부족"]:
                ax.text(mid_col / 2, rows * 0.05, f"{left_info['type']}\n(AI: {left_info['value']:.2f})", **text_props_type)
            right_info = foot_types.get('right')
            if right_info and right_info['type'] not in ["데이터 없음", "데이터 부족"]:
                ax.text(mid_col * 1.5, rows * 0.05, f"{right_info['type']}\n(AI: {right_info['value']:.2f})", **text_props_type)

if __name__ == "__main__":
    app = FootPressureApp()
    app.mainloop() 