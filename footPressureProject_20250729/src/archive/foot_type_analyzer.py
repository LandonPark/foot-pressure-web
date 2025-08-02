import json
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from datetime import datetime
import matplotlib.font_manager as fm
from scipy.ndimage import binary_opening

# --- (기존 함수들은 그대로 유지) ---
# 한글 폰트 설정, filter_noise, get_foot_bbox, get_center_of_mass, infer_virtual_footprint
# ... (이전 스크립트의 함수들을 여기에 복사) ...

# --- 한글 폰트 설정 ---
try:
    font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False
except FileNotFoundError:
    print("⚠️ 경고: Apple SD Gothic Neo 폰트를 찾을 수 없습니다. 텍스트가 깨질 수 있습니다.")
    font_prop = None

def filter_noise(pressure_array, min_size=3):
    binary_mask = pressure_array > 0
    cleaned_mask = binary_opening(binary_mask, structure=np.ones((2,2)), iterations=min_size)
    return pressure_array * cleaned_mask

def get_foot_bbox(foot_array):
    coords = np.argwhere(foot_array > 0)
    if coords.shape[0] == 0: return None
    min_row, _ = coords.min(axis=0)
    max_row, _ = coords.max(axis=0)
    return min_row, max_row

def get_center_of_mass(foot_array):
    total_pressure = np.sum(foot_array)
    if total_pressure == 0: return None
    y_indices, _ = np.indices(foot_array.shape)
    com_y = np.sum(y_indices * foot_array) / total_pressure
    return com_y

def infer_virtual_footprint(foot_array, sensor_total_rows):
    detected_bbox = get_foot_bbox(foot_array)
    if not detected_bbox: return None
    com_y = get_center_of_mass(foot_array)
    if com_y is None: return detected_bbox
    min_r, max_r = detected_bbox
    detected_height = max_r - min_r + 1
    if detected_height >= sensor_total_rows * 0.5: return detected_bbox
    hind_third_line = sensor_total_rows / 3
    fore_third_line = (sensor_total_rows * 2) / 3
    if com_y < hind_third_line:
        inferred_end_r = min_r + (detected_height * 3)
        return min_r, min(inferred_end_r, sensor_total_rows - 1)
    if com_y > fore_third_line:
        inferred_start_r = max_r - int(detected_height * 2.5)
        return max(0, inferred_start_r), max_r
    return detected_bbox

# --- 핵심 분석 로직 (V3.5 - 최종 과학적 기준 적용) ---

def analyze_foot_type(distribution):
    """
    압력 분포(distribution)를 받아 각 발의 유형과 Arch Index 값을 반환합니다.
    
    분류 기준은 Cavanagh & Rodgers (1987)가 제시한 Arch Index(AI)의
    오리지널 과학적 기준을 엄격하게 따릅니다.
    - 요족 (High Arch): AI < 0.21
    - 정상 (Normal): 0.21 <= AI <= 0.26
    - 평발 (Flat Foot): AI > 0.26
    
    [v3.4 수정] Arch Index 계산 시, 개별 발의 총합을 기준으로 중간발의
    비율을 계산하도록 수정하여 문헌의 정의와 일치시킴.
    
    Reference:
    Cavanagh, P. R., & Rodgers, M. M. (1987). The arch index.
    Journal of Biomechanics, 20(5), 547-551.
    """
    foot_types = {}
    
    # 왼쪽 발 분석
    left_total = distribution.get('LH', 0) + distribution.get('LM', 0) + distribution.get('LF', 0)
    if left_total > 0:
        arch_index_left = distribution.get('LM', 0) / left_total
        foot_type_str = ""
        if arch_index_left < 0.21:
            foot_type_str = "요족 (High Arch)"
        elif arch_index_left > 0.26:
            foot_type_str = "평발 (Flat Foot)"
        else:
            foot_type_str = "정상 (Normal)"
        foot_types['left'] = {'type': foot_type_str, 'value': arch_index_left}
    else:
        foot_types['left'] = {'type': "데이터 없음", 'value': 0}

    # 오른쪽 발 분석
    right_total = distribution.get('RH', 0) + distribution.get('RM', 0) + distribution.get('RF', 0)
    if right_total > 0:
        arch_index_right = distribution.get('RM', 0) / right_total
        foot_type_str = ""
        if arch_index_right < 0.21:
            foot_type_str = "요족 (High Arch)"
        elif arch_index_right > 0.26:
            foot_type_str = "평발 (Flat Foot)"
        else:
            foot_type_str = "정상 (Normal)"
        foot_types['right'] = {'type': foot_type_str, 'value': arch_index_right}
    else:
        foot_types['right'] = {'type': "데이터 없음", 'value': 0}
        
    return foot_types

def calculate_pressure_distribution(pressure_array):
    # (기존 V2.2.1의 함수 로직과 동일)
    total_pressure_original = np.sum(pressure_array)
    if total_pressure_original == 0: return {}, None
    cleaned_array_for_inference = filter_noise(pressure_array)
    rows, cols = cleaned_array_for_inference.shape
    mid_col = cols // 2
    left_foot_array = cleaned_array_for_inference[:, :mid_col]
    right_foot_array = cleaned_array_for_inference[:, mid_col:]
    left_vbox = infer_virtual_footprint(left_foot_array, rows)
    right_vbox = infer_virtual_footprint(right_foot_array, rows)
    if not left_vbox and not right_vbox: return {}, None
    all_rows = [r for vbox in (left_vbox, right_vbox) if vbox for r in vbox]
    final_min_r, final_max_r = min(all_rows), max(all_rows)
    final_bbox = (final_min_r, final_max_r)
    final_height = final_max_r - final_min_r + 1
    if final_height < 3: return {}, final_bbox
    hind_end_r = final_min_r + final_height // 3
    mid_end_r = final_min_r + (final_height * 2) // 3
    original_left_foot = pressure_array[:, :mid_col]
    original_right_foot = pressure_array[:, mid_col:]
    raw_distribution = {
        'LH': np.sum(original_left_foot[final_min_r:hind_end_r, :]), 'LM': np.sum(original_left_foot[hind_end_r:mid_end_r, :]), 'LF': np.sum(original_left_foot[mid_end_r:final_max_r + 1, :]),
        'RH': np.sum(original_right_foot[final_min_r:hind_end_r, :]), 'RM': np.sum(original_right_foot[hind_end_r:mid_end_r, :]), 'RF': np.sum(original_right_foot[mid_end_r:final_max_r + 1, :]),
    }
    pressure_threshold = total_pressure_original * 0.01
    for key, value in raw_distribution.items():
        if value < pressure_threshold: raw_distribution[key] = 0
    new_total_pressure = sum(raw_distribution.values())
    if new_total_pressure == 0: return {key: 0 for key in raw_distribution}, final_bbox
    final_distribution = {key: (value / new_total_pressure) * 100 for key, value in raw_distribution.items()}
    return final_distribution, final_bbox

def create_heatmap_from_json(json_path, output_path):
    # ... (파일 읽기, pressure_array 생성 부분은 동일) ...
    try:
        with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
        pressure_rows = data.get('RawPressureByRows')
        if not pressure_rows: return
        sorted_keys = sorted(pressure_rows.keys(), key=lambda x: int(x.split('_')[1]))
        pressure_matrix = [list(map(int, pressure_rows[key].split(', '))) for key in sorted_keys]
        pressure_array = np.array(pressure_matrix)

        distribution, final_bbox = calculate_pressure_distribution(pressure_array)
        foot_types = analyze_foot_type(distribution)

        # --- 시각화 ---
        cleaned_array_for_viz = filter_noise(pressure_array)
        rows, cols = cleaned_array_for_viz.shape
        mid_col = cols // 2
        fig, ax = plt.subplots(figsize=(5, 9))
        fig.set_facecolor('black')
        ax.set_facecolor('black')
        cmap = plt.get_cmap('jet')
        ax.imshow(cleaned_array_for_viz, cmap=cmap, interpolation='nearest')
        
        # ... (영역 구분선 및 가상 발자국 표시는 동일) ...
        if final_bbox:
            min_r, max_r = final_bbox
            height = max_r - min_r + 1
            if height >= 3:
                hind_end_r = min_r + height // 3
                mid_end_r = min_r + (height * 2) // 3
                ax.axhline(y=hind_end_r - 0.5, xmin=0.05, xmax=0.95, color='white', linestyle='--', linewidth=1)
                ax.axhline(y=mid_end_r - 0.5, xmin=0.05, xmax=0.95, color='white', linestyle='--', linewidth=1)
                ax.axhspan(min_r, max_r, facecolor='green', alpha=0.15)
        ax.axis('off')

        # --- 분석 결과 텍스트 표시 (위치 및 내용 수정) ---
        if distribution:
            # 1. 압력 분포 표시 (위치 중앙으로 이동)
            text_props = {'color': 'white', 'fontsize': 11, 'ha': 'center', 'fontproperties': font_prop}
            ax.text(mid_col / 2, rows * 0.25, f"뒤: {distribution.get('LH', 0):.1f}%", **text_props)
            ax.text(mid_col / 2, rows * 0.50, f"중간: {distribution.get('LM', 0):.1f}%", **text_props)
            ax.text(mid_col / 2, rows * 0.75, f"앞: {distribution.get('LF', 0):.1f}%", **text_props)
            
            ax.text(mid_col * 1.5, rows * 0.25, f"뒤: {distribution.get('RH', 0):.1f}%", **text_props)
            ax.text(mid_col * 1.5, rows * 0.50, f"중간: {distribution.get('RM', 0):.1f}%", **text_props)
            ax.text(mid_col * 1.5, rows * 0.75, f"앞: {distribution.get('RF', 0):.1f}%", **text_props)
            
            # 2. 발 유형(Foot Type) 및 Arch Index 값 표시
            type_props = {'color': 'cyan', 'fontsize': 12, 'ha': 'center', 'weight': 'bold', 'fontproperties': font_prop}
            
            left_info = foot_types.get('left')
            if left_info and left_info['type'] != "데이터 없음":
                left_text = f"{left_info['type']}\n(AI: {left_info['value']:.2f})"
                ax.text(mid_col / 2, rows * 0.05, left_text, **type_props)

            right_info = foot_types.get('right')
            if right_info and right_info['type'] != "데이터 없음":
                right_text = f"{right_info['type']}\n(AI: {right_info['value']:.2f})"
                ax.text(mid_col * 1.5, rows * 0.05, right_text, **type_props)
            
            # 터미널 출력
            print(f"  - 왼발: {left_info['type']} (AI: {left_info['value']:.2f}) | 오른발: {right_info['type']} (AI: {right_info['value']:.2f})")

        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, facecolor='black')
        plt.close(fig)
        print(f"✅ 최종 UI 적용 분석 완료: {os.path.basename(output_path)}")

    except Exception as e:
        print(f"❗️ 오류: '{os.path.basename(json_path)}' 처리 중 예상치 못한 오류 발생 - {e}")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    input_dir = os.path.join(project_root, 'data', 'input')
    output_dir = os.path.join(project_root, 'data', 'output', 'v3_5_final_scientific') # 새 버전 폴더
    os.makedirs(output_dir, exist_ok=True)
    
    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    if not json_files:
        print(f"'{input_dir}'에 분석할 파일이 없습니다.")
    else:
        print(f"총 {len(json_files)}개 파일에 대한 최종 분석(V3.5, 과학적 기준)을 시작합니다.")
        for input_path in json_files:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            input_basename = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{input_basename}_{timestamp}_final_sci.png" # 새 파일명
            output_path = os.path.join(output_dir, output_filename)
            print(f"\n▶️ 처리 중: {os.path.basename(input_path)}")
            create_heatmap_from_json(input_path, output_path) 