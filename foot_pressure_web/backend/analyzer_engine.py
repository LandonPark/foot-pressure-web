import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.ndimage import label, find_objects, binary_opening, center_of_mass, gaussian_filter
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime
import io
import base64

try:
    from .config import ANALYSIS_PARAMS, FOOT_TYPE_CRITERIA, VISUALIZATION
except ImportError:
    from config import ANALYSIS_PARAMS, FOOT_TYPE_CRITERIA, VISUALIZATION

def setup_matplotlib_font():
    """
    Matplotlib 폰트를 설정하는 함수.
    FastAPI 시작 시 한 번만 호출되도록 설계되었습니다.
    """
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        FONT_PATH = os.path.join(BASE_DIR, 'fonts', 'NanumGothic.ttf')

        if os.path.exists(FONT_PATH):
            font_manager.fontManager.addfont(FONT_PATH)
            plt.rcParams['font.family'] = 'NanumGothic'
            plt.rcParams['axes.unicode_minus'] = False
            print(f"✅ [Font Setup] 폰트 설정 완료: NanumGothic")
        else:
            print(f"❗️ [Font Setup] 경고: 폰트 파일을 찾을 수 없습니다: {FONT_PATH}. 시스템 기본 폰트를 사용합니다.")
            plt.rcParams['font.family'] = 'sans-serif'
    except Exception as e:
        print(f"❗️ [Font Setup] 폰트 설정 중 오류 발생: {e}")


def convert_numpy_to_native(data):
    if isinstance(data, dict):
        return {key: convert_numpy_to_native(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_to_native(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(convert_numpy_to_native(item) for item in data)
    elif isinstance(data, np.generic):
        return data.item()
    elif isinstance(data, np.ndarray):
        return data.tolist()
    else:
        return data

class FootPressureAnalyzer:
    def __init__(self, json_data, filename="uploaded_data.json", ui_logger=None):
        self.filename = filename
        self.json_data = json_data
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
        self.cop = None
        self.left_foot_indices = None
        self.right_foot_indices = None
        self.analysis_results = {}
        self.error_message = None

    def _log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_message = f"[{timestamp}] [ENGINE] {message}"
        if self.ui_logger:
            self.ui_logger(f"[ENGINE] {message}")
        else:
            print(log_message)

    def run_analysis(self):
        self._log("================= 분석 파이프라인 시작 =================")
        try:
            self._process_input_data()
            if self.pressure_array.size == 0:
                self.error_message = f"'{self.filename}'에 데이터가 없거나 형식이 잘못되었습니다."
                return False
            self._filter_noise()
            self._calculate_cop()
            self._calculate_pressure_distribution()
            self._analyze_foot_type()
            self._prepare_final_results()
            self._log("================= 분석 파이프라인 성공적으로 종료 =================")
        except Exception as e:
            self.error_message = f"분석 실행 중 오류 발생: {e}"
            self._log(f"❗️ {self.error_message}")
            return False
        return True

    def _process_input_data(self):
        self._log(f"데이터 처리 중: {self.filename}")
        try:
            pressure_rows = self.json_data.get('RawPressureByRows')
            if not pressure_rows:
                self.pressure_array = np.array([])
                return
            
            sorted_keys = sorted(pressure_rows.keys(), key=lambda x: int(x.split('_')[1]))
            pressure_matrix = [list(map(int, pressure_rows[key].split(', '))) for key in sorted_keys]
            self.pressure_array = np.array(pressure_matrix)
            self.pressure_data = self.pressure_array.copy()
        except (ValueError, TypeError, KeyError) as e:
            self._log(f"❗️ 오류: '{self.filename}' 데이터 처리 중 오류 발생 - {e}")
            self.pressure_array = np.array([])

    def get_visualization_data(self):
        if self.error_message:
            return None
        
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
        return vis_data

    def get_visualization_as_base64(self, vis_data):
        if not vis_data:
            return None

        pressure_data = np.array(vis_data['pressure_data'])
        smoothed_data = gaussian_filter(pressure_data, sigma=VISUALIZATION.get('gaussian_sigma', 1.0))
        
        figsize = vis_data['config'].get('figsize', (8, 10))
        cmap = VISUALIZATION.get('cmap', 'plasma')
        interpolation = VISUALIZATION.get('interpolation', 'bilinear')
        
        fig = plt.figure(figsize=figsize, facecolor='white')
        ax_main = fig.add_axes([0.05, 0.1, 0.9, 0.85])
        cax = fig.add_axes([0.05, 0.05, 0.9, 0.03])

        im = ax_main.imshow(smoothed_data, cmap=cmap, interpolation=interpolation)
        self._draw_visualization_details(fig, ax_main, vis_data)
        ax_main.axis('off')

        cbar = fig.colorbar(im, cax=cax, orientation='horizontal')
        cbar.set_label('Pressure', size=10)
        cbar.ax.tick_params(labelsize=8)
        
        try:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=VISUALIZATION.get('dpi', 150), bbox_inches='tight', pad_inches=0.1)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
        except Exception as e:
            self._log(f"❗️ Base64 인코딩 실패: {e}")
            return None
        finally:
            plt.close(fig)

    def _filter_noise(self):
        if self.pressure_array.size == 0: return
        max_pressure = np.max(self.pressure_array)
        if max_pressure == 0:
            self.cleaned_array = self.pressure_array.copy()
            return
            
        threshold = ANALYSIS_PARAMS.get('noise_threshold', 5)
        self.cleaned_array = np.where(self.pressure_array > threshold, self.pressure_array, 0)
        
        structure = np.ones((3, 3), dtype=int)
        self.cleaned_array = binary_opening(self.cleaned_array > 0, structure=structure).astype(int) * self.cleaned_array
        
    def _calculate_cop(self):
        if self.cleaned_array.size == 0 or np.sum(self.cleaned_array) == 0:
            self.cop = None
            return
        self.cop = center_of_mass(self.cleaned_array)

    def _separate_feet(self, array):
        if np.sum(array) == 0:
            return np.array([]), np.array([])
        rows, cols = array.shape
        mid_col = cols // 2
        labeled_array, num_features = label(array > 0)
        if num_features == 1:
            obj_slice = find_objects(labeled_array)[0]
            obj_min_col, obj_max_col = obj_slice[1].start, obj_slice[1].stop
            
            if (obj_min_col < mid_col < obj_max_col) and ((obj_max_col - obj_min_col) > cols / 3):
                left_mask = np.zeros_like(array, dtype=bool)
                left_mask[:, :mid_col] = labeled_array[:, :mid_col] == 1
                right_mask = np.zeros_like(array, dtype=bool)
                right_mask[:, mid_col:] = labeled_array[:, mid_col:] == 1
                left_foot, right_foot = array * left_mask, array * right_mask
                if np.sum(left_foot) > 0 and np.sum(right_foot) > 0:
                    return left_foot, right_foot
        left_mask = np.zeros_like(array, dtype=bool)
        right_mask = np.zeros_like(array, dtype=bool)
        coms = [center_of_mass(array, labeled_array, i + 1) for i in range(num_features)]
        for i, com in enumerate(coms):
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
        hind_ratio = VISUALIZATION['regions'].get('hindfoot_ratio', 0.3)
        mid_ratio = VISUALIZATION['regions'].get('midfoot_ratio', 0.4)
        hind_end = min_r + int(height * hind_ratio)
        mid_end = hind_end + int(height * mid_ratio)
        return {'hind': {'start': min_r, 'stop': hind_end}, 'mid': {'start': hind_end, 'stop': mid_end}, 'fore': {'start': mid_end, 'stop': max_r + 1}}

    def _calculate_pressure_distribution(self):
        self.left_foot, self.right_foot = self._separate_feet(self.cleaned_array)
        def get_virtual_footprint(foot_array):
            if np.sum(foot_array) == 0: return None
            rows_with_pressure = np.where(np.any(foot_array > 0, axis=1))[0]
            return (rows_with_pressure.min(), rows_with_pressure.max()) if len(rows_with_pressure) > 0 else None
        left_bbox, right_bbox = get_virtual_footprint(self.left_foot), get_virtual_footprint(self.right_foot)
        if not left_bbox and not right_bbox: return
        all_min_r = min(b[0] for b in [left_bbox, right_bbox] if b)
        all_max_r = max(b[1] for b in [left_bbox, right_bbox] if b)
        self.final_bbox = (all_min_r, all_max_r)
        if (total_pressure := np.sum(self.left_foot) + np.sum(self.right_foot)) == 0: return
        if not (zones := self._get_foot_zone_indices(self.final_bbox, self.pressure_array.shape[0])): return
        for prefix, foot_array in [('L', self.left_foot), ('R', self.right_foot)]:
            if (foot_total := np.sum(foot_array)) == 0: continue
            for zone_name, idx in zones.items():
                self.distribution[f"{prefix}{zone_name[0].upper()}"] = (np.sum(foot_array[idx['start']:idx['stop'], :]) / foot_total) * 100

    def _analyze_foot_type(self):
        if not (zones := self._get_foot_zone_indices(self.final_bbox, self.pressure_array.shape[0])): return
        for prefix, name in [('L', '왼쪽'), ('R', '오른쪽')]:
            foot_array = self.left_foot if prefix == 'L' else self.right_foot
            if (foot_total := np.sum(foot_array)) == 0:
                self.foot_types[name] = {'type': "데이터 없음", 'value': 0, 'score': 0}
                continue
            mid_pressure = np.sum(foot_array[zones['mid']['start']:zones['mid']['stop'], :])
            arch_index = mid_pressure / foot_total
            self.foot_types[name] = {'type': self._classify_arch(arch_index), 'value': arch_index, 'score': self._calculate_arch_score(arch_index)}

    def _classify_arch(self, ratio):
        if ratio <= FOOT_TYPE_CRITERIA.get('high_arch', 0.21): return "요족 (High Arch)"
        if ratio <= FOOT_TYPE_CRITERIA.get('normal', 0.26): return "정상 (Normal)"
        return "평발 (Flat Foot)"

    def _calculate_arch_score(self, arch_index):
        high, normal = FOOT_TYPE_CRITERIA.get('high_arch', 0.21), FOOT_TYPE_CRITERIA.get('normal', 0.26)
        ideal, width = (high + normal) / 2, (normal - high) / 2
        return round(max(0, 100 - (abs(arch_index - ideal) / width * 50)), 1) if width != 0 else (100.0 if arch_index == ideal else 0.0)

    def _prepare_final_results(self):
        self.analysis_results = {'distribution': self.distribution, 'foot_types': self.foot_types, 'final_bbox': self.final_bbox, 'zones': self._get_foot_zone_indices(self.final_bbox, self.pressure_array.shape[0]), 'cop': self.cop}

    def _draw_visualization_details(self, fig, ax, vis_data):
        results = vis_data.get('analysis_results', {})
        if (pressure_data := np.array(vis_data.get('pressure_data'))).size == 0 or not results: return
        rows, cols = pressure_data.shape
        mid_col = cols // 2
        ax.axvline(x=mid_col - 0.5, color=VISUALIZATION.get('CENTER_LINE_COLOR', 'white'), linestyle=VISUALIZATION.get('CENTER_LINE_STYLE', ':'), linewidth=VISUALIZATION.get('CENTER_LINE_WIDTH', 1))
        ax.axhline(y=(rows / 2) - 0.5, color=VISUALIZATION.get('CENTER_LINE_COLOR', 'white'), linestyle=VISUALIZATION.get('CENTER_LINE_STYLE', ':'), linewidth=VISUALIZATION.get('CENTER_LINE_WIDTH', 1))
        if (final_bbox := results.get('final_bbox')) and (zones := results.get('zones')):
            ax.axhline(y=zones['mid']['start'] - 0.5, color='white', linestyle='--', linewidth=1)
            ax.axhline(y=zones['fore']['start'] - 0.5, color='white', linestyle='--', linewidth=1)
        if cop_coords := results.get('cop'):
            cop_y, cop_x = cop_coords
            ax.plot(cop_x, cop_y, marker=VISUALIZATION.get('COP_MARKER', 'x'), color=VISUALIZATION.get('COP_COLOR', 'red'), markersize=VISUALIZATION.get('COP_MARKER_SIZE', 12), markeredgewidth=2)
