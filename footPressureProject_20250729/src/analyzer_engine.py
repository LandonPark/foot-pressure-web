import os
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, find_objects, binary_opening, center_of_mass, gaussian_filter
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime

from config import (
    ANALYSIS_PARAMS, FOOT_TYPE_CRITERIA, VISUALIZATION
)

def convert_numpy_to_native(data):
    """
    분석 결과에 포함된 Numpy 데이터 타입을 파이썬 기본 데이터 타입으로 재귀적으로 변환합니다.
    tkinter와 스레드 간의 데이터 전달 시 발생할 수 있는 문제를 예방합니다.
    """
    if isinstance(data, dict):
        return {key: convert_numpy_to_native(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_to_native(item) for item in data]
    elif isinstance(data, np.generic):
        return data.item()
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

class FootPressureAnalyzer:
    """
    족부 압력 데이터를 분석하고 시각화하는 클래스.
    하나의 데이터 파일(JSON)에 대한 모든 분석 과정을 캡슐화합니다.
    """
    def __init__(self, json_path, ui_logger=None):
        self.json_path = json_path
        self.ui_logger = ui_logger
        self.pressure_array = np.array([])
        self.cleaned_array = np.array([])
        self.left_foot = np.array([])
        self.right_foot = np.array([])
        self.distribution = {}
        self.foot_types = {}
        self.final_bbox = None
        self.pressure_data = None
        self.total_pressure = None
        self.cop = None  # 압력 중심점(CoP) 추가
        self.left_foot_indices = None
        self.right_foot_indices = None
        self.analysis_results = {}
        self.error_message = None

    def _log(self, message):
        """UI 로거가 있으면 UI/터미널에, 없으면 터미널에만 로그를 남깁니다."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_message = f"[{timestamp}] [ENGINE] {message}"
        
        if self.ui_logger:
            self.ui_logger(f"[ENGINE] {message}")
        else:
            print(log_message)

    def run_analysis(self):
        """분석 파이프라인 전체를 실행합니다."""
        self._log("================= 분석 파이프라인 시작 =================")
        try:
            self._load_data()
            if self.pressure_array.size == 0:
                self._log(f"❗️ 경고: '{os.path.basename(self.json_path)}'에 데이터가 없거나 형식이 잘못되었습니다.")
                return False
            self._filter_noise()
            self._calculate_cop()  # CoP 계산 추가
            self._calculate_pressure_distribution()
            self._analyze_foot_type()
            self._prepare_final_results()
            self._log("================= 분석 파이프라인 성공적으로 종료 =================")
        except Exception as e:
            self.error_message = f"분석 실행 중 오류 발생: {e}"
            self._log(f"❗️ {self.error_message}")
            self._log("================= 분석 파이프라인 오류로 종료 =================")
            return False
        return True

    def get_visualization_data(self):
        """시각화에 필요한 데이터를 딕셔너리로 반환합니다."""
        if self.error_message:
            return None
        
        self._log("시각화에 필요한 데이터를 준비합니다.")
        vis_data = {
            "pressure_data": self.cleaned_array,
            "analysis_results": self.analysis_results,
            "config": {
                "figsize": VISUALIZATION.get('figsize', (8, 10)),
                "cmap": VISUALIZATION.get('cmap', 'plasma'),
                "interpolation": VISUALIZATION.get('interpolation', 'bilinear'),
                "gaussian_sigma": VISUALIZATION.get('gaussian_sigma', 1.0)
            }
        }
        native_data = convert_numpy_to_native(vis_data)
        self._log("Numpy 타입을 파이썬 기본 타입으로 변환 완료.")
        return native_data

    def save_visualization(self, output_path, vis_data):
        """ 분석 결과를 이미지 파일로 저장합니다. (텍스트 정보 없이 그래프만) """
        if not vis_data:
            self._log(f"오류: 시각화 데이터가 제공되지 않았습니다.")
            return

        # 1. (개선) 가우시안 필터를 적용하여 데이터를 부드럽게 만듭니다.
        pressure_data = np.array(vis_data['pressure_data'])
        smoothed_data = gaussian_filter(pressure_data, sigma=VISUALIZATION.get('gaussian_sigma', 1.0))
        
        # 2. (개선) 컬러맵과 보간법을 설정합니다.
        figsize = vis_data['config'].get('figsize', (8, 10))
        cmap = VISUALIZATION.get('cmap', 'plasma') # 'plasma'를 기본값으로 변경
        interpolation = VISUALIZATION.get('interpolation', 'bilinear') # 'bilinear'를 기본값으로
        
        fig = plt.figure(figsize=figsize, facecolor='white')
        
        # 그래프와 컬러바가 전체 이미지 영역을 차지하도록 레이아웃 조정
        ax_main = fig.add_axes([0.05, 0.1, 0.9, 0.85]) # [left, bottom, width, height]
        cax = fig.add_axes([0.05, 0.05, 0.9, 0.03]) # 컬러바를 위한 축

        im = ax_main.imshow(smoothed_data, cmap=cmap, interpolation=interpolation)
        
        # 시각화 상세 정보 그리기 (CoP, 중심선 등)
        self._draw_visualization_details(fig, ax_main, vis_data)
        
        ax_main.axis('off')

        # 컬러바 생성 (레이블 텍스트 크기 조정)
        cbar = fig.colorbar(im, cax=cax, orientation='horizontal')
        cbar.set_label('Pressure', size=10)
        cbar.ax.tick_params(labelsize=8)
        
        try:
            # bbox_inches='tight' 옵션으로 저장 시 여백을 최소화
            fig.savefig(output_path, dpi=VISUALIZATION.get('dpi', 150), bbox_inches='tight', pad_inches=0.1)
            self._log(f"✅ 분석 보고서 저장 완료: {os.path.basename(output_path)}")
        except Exception as e:
            self._log(f"❗️ 이미지 파일 저장 실패: {e}")
        finally:
            plt.close(fig)

    def _load_data(self):
        self._log(f"데이터 로딩 중: {os.path.basename(self.json_path)}")
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            pressure_rows = data.get('RawPressureByRows')
            if not pressure_rows: 
                self._log("'RawPressureByRows' 키를 찾을 수 없습니다.")
                self.pressure_array = np.array([])
                return
            
            # 행(row) 키에서 숫자 부분을 추출하여 정렬
            # 예: "Row_0", "Row_1", ...
            sorted_keys = sorted(pressure_rows.keys(), key=lambda x: int(x.split('_')[1]))
            
            # 정렬된 키를 바탕으로 압력 데이터를 2D 리스트로 구성
            pressure_matrix = [list(map(int, pressure_rows[key].split(', '))) for key in sorted_keys]

            self.pressure_array = np.array(pressure_matrix)
            self.pressure_data = self.pressure_array.copy()
            self._log(f"데이터 로딩 완료. 압력 매트릭스 크기: {self.pressure_array.shape}")
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
            self._log(f"❗️ 오류: '{os.path.basename(self.json_path)}' 파일 처리 중 오류 발생 - {e}")
            self.pressure_array = np.array([])
        self._log("----------------- 데이터 로딩 완료 -----------------")

    def _filter_noise(self):
        self._log("----------------- 노이즈 필터링 시작 -----------------")
        if self.pressure_array.size == 0: return

        max_pressure = np.max(self.pressure_array)
        if max_pressure == 0:
            self.cleaned_array = self.pressure_array.copy()
            self._log("최대 압력이 0이므로 노이즈 필터링을 건너뜁니다.")
            return
            
        threshold = ANALYSIS_PARAMS.get('noise_threshold', 5)
        self.cleaned_array = np.where(self.pressure_array > threshold, self.pressure_array, 0)
        
        # 연결된 작은 객체들(노이즈)을 제거하기 위해 binary_opening 사용
        structure = np.ones((3, 3), dtype=int)
        self.cleaned_array = binary_opening(self.cleaned_array > 0, structure=structure).astype(int) * self.cleaned_array
        self._log("----------------- 노이즈 필터링 완료 -----------------")
        
    def _calculate_cop(self):
        """전체 압력 중심점(Center of Pressure)을 계산합니다."""
        self._log("-------------- 압력 중심점(CoP) 계산 시작 --------------")
        if self.cleaned_array.size == 0 or np.sum(self.cleaned_array) == 0:
            self._log("압력 데이터가 없어 CoP를 계산할 수 없습니다.")
            self.cop = None
            return

        self.cop = center_of_mass(self.cleaned_array)
        self._log(f"➡️ 계산된 CoP 위치 (y, x): ({self.cop[0]:.2f}, {self.cop[1]:.2f})")
        self._log("-------------- 압력 중심점(CoP) 계산 완료 --------------")

    def _separate_feet(self, array):
        self._log("----------------- 좌우 발 분리 시작 -----------------")
        if np.sum(array) == 0:
            return np.array([]), np.array([])

        rows, cols = array.shape
        mid_col = cols // 2
        labeled_array, num_features = label(array > 0)

        # CASE 1: 두 발이 붙어 하나의 큰 객체로 인식될 경우 강제 분리
        if num_features == 1:
            obj_slice = find_objects(labeled_array)[0]
            obj_min_col, obj_max_col = obj_slice[1].start, obj_slice[1].stop
            
            # 객체가 중앙을 가로지르고, 너비가 충분히 넓은 경우
            is_spanning_center = obj_min_col < mid_col < obj_max_col
            is_wide_enough = (obj_max_col - obj_min_col) > cols / 3 # 센서 너비의 1/3 이상
            
            if is_spanning_center and is_wide_enough:
                self._log("두 발이 연결된 것으로 판단하여 중앙을 기준으로 강제 분리합니다.")
                left_mask = np.zeros_like(array, dtype=bool)
                left_mask[:, :mid_col] = labeled_array[:, :mid_col] == 1
                
                right_mask = np.zeros_like(array, dtype=bool)
                right_mask[:, mid_col:] = labeled_array[:, mid_col:] == 1

                left_foot = array * left_mask
                right_foot = array * right_mask

                # 분리 후 양쪽에 모두 데이터가 있는지 확인
                if np.sum(left_foot) > 0 and np.sum(right_foot) > 0:
                    return left_foot, right_foot

        # CASE 2: 여러 객체가 분리되어 있을 경우 (일반적인 경우)
        left_mask = np.zeros_like(array, dtype=bool)
        right_mask = np.zeros_like(array, dtype=bool)
        coms = [center_of_mass(array, labeled_array, i + 1) for i in range(num_features)]
        
        for i, com in enumerate(coms):
            # 무게 중심의 x좌표(com[1])가 중앙보다 왼쪽에 있으면 왼발
            if com[1] < mid_col:
                left_mask[labeled_array == i + 1] = True
            else:
                right_mask[labeled_array == i + 1] = True
                
        return array * left_mask, array * right_mask

    def _get_foot_zone_indices(self, foot_bbox, total_rows):
        if not foot_bbox: return None
        min_r, max_r = foot_bbox
        height = max_r - min_r + 1
        if height < 3: return None
        
        # 발 영역을 config에서 정의된 비율로 나눔
        hind_ratio = VISUALIZATION['regions'].get('hindfoot_ratio', 0.3)
        mid_ratio = VISUALIZATION['regions'].get('midfoot_ratio', 0.4)
        
        hind_end = min_r + int(height * hind_ratio)
        mid_end = hind_end + int(height * mid_ratio)
        
        return {
            'hind': {'start': min_r, 'stop': hind_end},
            'mid': {'start': hind_end, 'stop': mid_end},
            'fore': {'start': mid_end, 'stop': max_r + 1}
        }

    def _calculate_pressure_distribution(self):
        self._log("-------------- 압력 분포 계산 시작 --------------")
        self.left_foot, self.right_foot = self._separate_feet(self.cleaned_array)
        
        def get_virtual_footprint(foot_array):
            if np.sum(foot_array) == 0: return None
            # 압력이 감지된 행들의 인덱스를 찾음
            rows_with_pressure = np.where(np.any(foot_array > 0, axis=1))[0]
            if len(rows_with_pressure) == 0: return None
            min_r, max_r = rows_with_pressure.min(), rows_with_pressure.max()
            return (min_r, max_r)

        left_bbox = get_virtual_footprint(self.left_foot)
        right_bbox = get_virtual_footprint(self.right_foot)
        if not left_bbox and not right_bbox: return

        # 양발의 전체 BBox 계산
        all_min_r = min([b[0] for b in [left_bbox, right_bbox] if b])
        all_max_r = max([b[1] for b in [left_bbox, right_bbox] if b])
        self.final_bbox = (all_min_r, all_max_r)
        
        total_pressure = np.sum(self.left_foot) + np.sum(self.right_foot)
        if total_pressure == 0: return
        
        zones = self._get_foot_zone_indices(self.final_bbox, self.pressure_array.shape[0])
        if not zones: return
        
        # 각 발, 각 영역의 압력 계산
        for prefix, foot_array in [('L', self.left_foot), ('R', self.right_foot)]:
            foot_total_pressure = np.sum(foot_array)
            if foot_total_pressure == 0: continue

            for zone_name, zone_indices in zones.items():
                sum_in_zone = np.sum(foot_array[zone_indices['start']:zone_indices['stop'], :])
                # 각 발의 전체 압력 대비 해당 영역의 압력 비율
                self.distribution[f"{prefix}{zone_name[0].upper()}"] = (sum_in_zone / foot_total_pressure) * 100

    def _analyze_foot_type(self):
        self._log("----------------- 발 유형 분석 시작 -----------------")
        
        zones = self._get_foot_zone_indices(self.final_bbox, self.pressure_array.shape[0])
        if not zones: 
            self._log("발 영역이 정의되지 않아 유형 분석을 건너뜁니다.")
            return

        for prefix, name in [('L', '왼쪽'), ('R', '오른쪽')]:
            # Midfoot 영역의 압력을 가져옴
            mid_pressure = np.sum(self.left_foot[zones['mid']['start']:zones['mid']['stop'], :] if prefix == 'L' 
                                  else self.right_foot[zones['mid']['start']:zones['mid']['stop'], :])
            
            foot_total_pressure = np.sum(self.left_foot if prefix == 'L' else self.right_foot)

            if foot_total_pressure == 0:
                self.foot_types[name] = {'type': "데이터 없음", 'value': 0, 'score': 0}
                continue

            arch_index = mid_pressure / foot_total_pressure
            
            type_str = self._classify_arch(arch_index)
            score = self._calculate_arch_score(arch_index)
            self.foot_types[name] = {'type': type_str, 'value': arch_index, 'score': score}
            self._log(f"분석 완료 ({name}): AI={arch_index:.3f}, Type={type_str}, Score={score}")

    def _classify_arch(self, ratio):
        if ratio <= FOOT_TYPE_CRITERIA.get('high_arch', 0.21): return "요족 (High Arch)"
        if ratio <= FOOT_TYPE_CRITERIA.get('normal', 0.26): return "정상 (Normal)"
        return "평발 (Flat Foot)"

    def _calculate_arch_score(self, arch_index):
        high_thresh = FOOT_TYPE_CRITERIA.get('high_arch', 0.21)
        normal_thresh = FOOT_TYPE_CRITERIA.get('normal', 0.26)
        
        ideal = (high_thresh + normal_thresh) / 2
        width = (normal_thresh - high_thresh) / 2
        if width == 0: return 100.0 if arch_index == ideal else 0.0
        
        deviation = abs(arch_index - ideal) / width
        score = max(0, 100 - (deviation * 50)) # 점수 편차를 더 크게 조절
        return round(score, 1)

    def _prepare_final_results(self):
        """최종 분석 결과를 정리합니다."""
        self.analysis_results = {
            'distribution': self.distribution,
            'foot_types': self.foot_types,
            'final_bbox': self.final_bbox,
            'zones': self._get_foot_zone_indices(self.final_bbox, self.pressure_array.shape[0]),
            'cop': self.cop
        }

    def _draw_visualization_details(self, fig, ax, vis_data):
        """시각화 이미지에 각종 분석 정보를 그립니다."""
        results = vis_data.get('analysis_results', {})
        pressure_data = np.array(vis_data.get('pressure_data'))
        if pressure_data.size == 0 or not results: return
            
        rows, cols = pressure_data.shape
        mid_col = cols // 2
        
        # 중앙 기준선 추가
        ax.axvline(x=mid_col - 0.5, color=VISUALIZATION.get('CENTER_LINE_COLOR', 'white'), 
                    linestyle=VISUALIZATION.get('CENTER_LINE_STYLE', ':'), 
                    linewidth=VISUALIZATION.get('CENTER_LINE_WIDTH', 1))
        ax.axhline(y=(rows / 2) - 0.5, color=VISUALIZATION.get('CENTER_LINE_COLOR', 'white'), 
                    linestyle=VISUALIZATION.get('CENTER_LINE_STYLE', ':'), 
                    linewidth=VISUALIZATION.get('CENTER_LINE_WIDTH', 1))
        
        # 발 영역 및 압력 분포 텍스트
        final_bbox = results.get('final_bbox')
        zones = results.get('zones')
        if final_bbox and zones:
            min_r, max_r = final_bbox
            # ax.axhspan(min_r, max_r, facecolor='grey', alpha=0.1)
            ax.axhline(y=zones['mid']['start'] - 0.5, color='white', linestyle='--', linewidth=1)
            ax.axhline(y=zones['fore']['start'] - 0.5, color='white', linestyle='--', linewidth=1)

        # 압력 중심점(CoP) 표시
        cop_coords = results.get('cop')
        if cop_coords:
            cop_y, cop_x = cop_coords
            ax.plot(cop_x, cop_y, 
                    marker=VISUALIZATION.get('COP_MARKER', 'x'), 
                    color=VISUALIZATION.get('COP_COLOR', 'red'), 
                    markersize=VISUALIZATION.get('COP_MARKER_SIZE', 12),
                    markeredgewidth=2)
