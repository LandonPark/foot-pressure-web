import json
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from datetime import datetime
import matplotlib.font_manager as fm
from scipy.ndimage import binary_opening # 노이즈 제거를 위해 임포트

# --- 한글 폰트 설정 ---
try:
    font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False
except FileNotFoundError:
    print("⚠️ 경고: Apple SD Gothic Neo 폰트를 찾을 수 없습니다. 텍스트가 깨질 수 있습니다.")
    font_prop = None # 폰트가 없으면 None으로 설정

# --- 분석 함수 ---

def filter_noise(pressure_array, min_size=3):
    """
    압력 배열에서 지정된 크기(min_size)보다 작은 연결된 점들을 노이즈로 간주하고 제거합니다.
    """
    binary_mask = pressure_array > 0
    cleaned_mask = binary_opening(binary_mask, structure=np.ones((2,2)), iterations=min_size)
    return pressure_array * cleaned_mask

def get_foot_bbox(foot_array):
    """
    단일 발 압력 배열로부터 압력이 감지된 영역의 세로 Bounding Box (min_row, max_row)를 반환합니다.
    압력이 없으면 None을 반환합니다.
    """
    coords = np.argwhere(foot_array > 0)
    if coords.shape[0] == 0:
        return None
    min_row, _ = coords.min(axis=0)
    max_row, _ = coords.max(axis=0)
    return min_row, max_row

def get_center_of_mass(foot_array):
    """
    압력 배열의 세로 무게 중심(y-coordinate)을 계산합니다.
    """
    total_pressure = np.sum(foot_array)
    if total_pressure == 0:
        return None
    
    y_indices, _ = np.indices(foot_array.shape)
    
    com_y = np.sum(y_indices * foot_array) / total_pressure
    
    return com_y

def infer_virtual_footprint(foot_array, sensor_total_rows):
    """
    [V2.1] 감지된 압력의 '무게 중심'을 기반으로 '가상 발자국' BBox를 추론합니다.
    """
    detected_bbox = get_foot_bbox(foot_array)
    if not detected_bbox:
        return None

    com_y = get_center_of_mass(foot_array)
    # 무게 중심 계산이 불가능하면 (압력이 없으면) 추론하지 않음
    if com_y is None:
        return detected_bbox

    min_r, max_r = detected_bbox
    detected_height = max_r - min_r + 1

    # 안전 장치: 감지된 발자국이 이미 매우 크면(센서의 50% 이상) 추론하지 않음
    # 이는 요족(pes cavus)처럼 앞뒤가 떨어져 있지만 전체 길이가 긴 경우를 보호하기 위함
    if detected_height >= sensor_total_rows * 0.5:
        return detected_bbox

    # 위치 기준선
    hind_third_line = sensor_total_rows / 3
    fore_third_line = (sensor_total_rows * 2) / 3

    # 새로운 규칙: 무게 중심이 뒤쪽에 치우쳐 있으면 '뒤꿈치 패턴'으로 간주
    if com_y < hind_third_line:
        print("  - 패턴 감지: 무게중심 기반 '뒤꿈치' 패턴으로 추론")
        # 시작점은 고정, 감지된 높이를 기반으로 전체 길이 추론
        inferred_end_r = min_r + (detected_height * 3)
        return min_r, min(inferred_end_r, sensor_total_rows - 1)

    # 새로운 규칙: 무게 중심이 앞쪽에 치우쳐 있으면 '앞꿈치 패턴'으로 간주
    if com_y > fore_third_line:
        print("  - 패턴 감지: 무게중심 기반 '앞꿈치' 패턴으로 추론")
        # 끝점은 고정, 감지된 높이를 기반으로 전체 길이 추론
        inferred_start_r = max_r - int(detected_height * 2.5)
        return max(0, inferred_start_r), max_r

    # 그 외: 명확한 패턴이 없으면 원래 감지된 Bbox 사용
    return detected_bbox


def calculate_pressure_distribution(pressure_array):
    """
    [V2.2.1] 가상 발자국 추론, 최소 압력 임계값(Threshold) 적용, 100% 재조정
    """
    total_pressure_original = np.sum(pressure_array)
    if total_pressure_original == 0:
        return {}, None

    # 노이즈 제거는 추론 및 시각화에만 사용
    cleaned_array_for_inference = filter_noise(pressure_array)
    
    rows, cols = cleaned_array_for_inference.shape
    mid_col = cols // 2
    
    left_foot_array = cleaned_array_for_inference[:, :mid_col]
    right_foot_array = cleaned_array_for_inference[:, mid_col:]

    # 각 발에 대해 가상 발자국 추론
    left_vbox = infer_virtual_footprint(left_foot_array, rows)
    right_vbox = infer_virtual_footprint(right_foot_array, rows)

    # 두 발의 가상 발자국을 통합하여 최종 분석 기준 Box 생성
    if not left_vbox and not right_vbox:
        return {}, None
    
    all_rows = []
    if left_vbox: all_rows.extend(left_vbox)
    if right_vbox: all_rows.extend(right_vbox)
    
    final_min_r = min(all_rows)
    final_max_r = max(all_rows)
    final_bbox = (final_min_r, final_max_r)
    
    final_height = final_max_r - final_min_r + 1
    if final_height < 3:
        return {}, final_bbox

    # 통합 기준선 계산
    hind_end_r = final_min_r + final_height // 3
    mid_end_r = final_min_r + (final_height * 2) // 3

    # 1. 각 구역별 'raw' 압력 계산
    original_left_foot = pressure_array[:, :mid_col]
    original_right_foot = pressure_array[:, mid_col:]

    raw_distribution = {
        'LH': np.sum(original_left_foot[final_min_r:hind_end_r, :]),
        'LM': np.sum(original_left_foot[hind_end_r:mid_end_r, :]),
        'LF': np.sum(original_left_foot[mid_end_r:final_max_r + 1, :]),
        'RH': np.sum(original_right_foot[final_min_r:hind_end_r, :]),
        'RM': np.sum(original_right_foot[hind_end_r:mid_end_r, :]),
        'RF': np.sum(original_right_foot[mid_end_r:final_max_r + 1, :]),
    }

    # 2. '최소 압력 임계값' 적용 (수정된 로직)
    # 전체 압력의 1% 미만인 구역은 노이즈로 간주하여 0으로 처리
    pressure_threshold = total_pressure_original * 0.01
    
    # 임계값보다 작은 raw 압력 값을 0으로 변경
    for key, value in raw_distribution.items():
        if value < pressure_threshold:
            raw_distribution[key] = 0

    # 3. 100% 기준으로 재조정 (Re-normalization)
    new_total_pressure = sum(raw_distribution.values())
    if new_total_pressure == 0:
        return {key: 0 for key in raw_distribution}, final_bbox

    final_distribution = {
        key: (value / new_total_pressure) * 100
        for key, value in raw_distribution.items()
    }
        
    return final_distribution, final_bbox


def create_heatmap_from_json(json_path, output_path):
    """
    [V2.2.1] JSON 파일을 읽어 최종 완성본 히트맵과 분석 결과를 생성합니다.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pressure_rows = data.get('RawPressureByRows')
        if not pressure_rows:
            print(f"⚠️ 경고: '{os.path.basename(json_path)}' 파일에 'RawPressureByRows' 데이터가 없습니다.")
            return

        sorted_keys = sorted(pressure_rows.keys(), key=lambda x: int(x.split('_')[1]))
        pressure_matrix = []
        for key in sorted_keys:
            row_data = [int(p) for p in pressure_rows[key].split(', ')]
            pressure_matrix.append(row_data)
        pressure_array = np.array(pressure_matrix)

        # 압력 분포 계산 및 가상 발자국 정보 얻기
        distribution, final_bbox = calculate_pressure_distribution(pressure_array)

        # 시각화용 노이즈 제거
        cleaned_array_for_viz = filter_noise(pressure_array)
        rows, cols = cleaned_array_for_viz.shape
        mid_col = cols // 2
        
        # --- 시각화 ---
        fig, ax = plt.subplots(figsize=(4, 8))
        fig.set_facecolor('black')
        ax.set_facecolor('black')

        cmap = plt.get_cmap('jet') 
        ax.imshow(cleaned_array_for_viz, cmap=cmap, interpolation='nearest')
        
        # --- 영역 구분선 그리기 (추론된 최종 BBox 기준) ---
        if final_bbox:
            min_r, max_r = final_bbox
            height = max_r - min_r + 1
            if height >= 3:
                hind_end_r = min_r + height // 3
                mid_end_r = min_r + (height * 2) // 3
                ax.axhline(y=hind_end_r - 0.5, xmin=0.05, xmax=0.95, color='white', linestyle='--', linewidth=1.5)
                ax.axhline(y=mid_end_r - 0.5, xmin=0.05, xmax=0.95, color='white', linestyle='--', linewidth=1.5)
                # 가상 발자국 영역 표시 (디버깅용)
                ax.axhspan(min_r, max_r, facecolor='green', alpha=0.15)


        ax.axis('off')

        # --- 압력 분포 텍스트 표시 ---
        if distribution:
            text_y_center = rows / 2
            text_x_left = mid_col / 2
            text_x_right = mid_col + (mid_col / 2)
            text_props = {'color': 'white', 'fontsize': 10, 'ha': 'center', 'fontproperties': font_prop}
            ax.text(text_x_left, text_y_center - (rows * 0.25), f"뒤: {distribution.get('LH', 0):.1f}%", **text_props)
            ax.text(text_x_left, text_y_center, f"중간: {distribution.get('LM', 0):.1f}%", **text_props)
            ax.text(text_x_left, text_y_center + (rows * 0.25), f"앞: {distribution.get('LF', 0):.1f}%", **text_props)
            ax.text(text_x_right, text_y_center - (rows * 0.25), f"뒤: {distribution.get('RH', 0):.1f}%", **text_props)
            ax.text(text_x_right, text_y_center, f"중간: {distribution.get('RM', 0):.1f}%", **text_props)
            ax.text(text_x_right, text_y_center + (rows * 0.25), f"앞: {distribution.get('RF', 0):.1f}%", **text_props)

            dist_str = ", ".join([f"{k}({v:.1f}%)" for k, v in distribution.items()])
            print(f"  - 압력 분포: {dist_str}")
            total_percent = sum(distribution.values())
            print(f"  - 총합: {total_percent:.1f}%")

        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, facecolor='black')
        plt.close(fig)
        
        print(f"✅ 분석 이미지 생성 완료: {os.path.basename(output_path)}")

    except FileNotFoundError:
        print(f"❗️ 오류: 파일을 찾을 수 없습니다 - {json_path}")
    except Exception as e:
        print(f"❗️ 오류: '{os.path.basename(json_path)}' 처리 중 예상치 못한 오류 발생 - {e}")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    input_dir = os.path.join(project_root, 'data', 'input')
    output_dir = os.path.join(project_root, 'data', 'output')
    
    # 출력 폴더를 버전별로 관리 (버그 수정 버전)
    output_dir_final = os.path.join(output_dir, 'v2.2.1_final_corrected')
    os.makedirs(output_dir_final, exist_ok=True)
    
    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    if not json_files:
        print(f"'{input_dir}' 폴더에 분석할 JSON 파일이 없습니다.")
    else:
        print(f"총 {len(json_files)}개의 파일을 '가상 발자국' 분석기 V2.2.1(최종 수정본)로 분석합니다.")
        for input_path in json_files:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            input_basename = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{input_basename}_{timestamp}_analysis_v2.2.1_final.png"
            output_path = os.path.join(output_dir_final, output_filename)
            print(f"\n▶️ 처리 중: {os.path.basename(input_path)}")
            create_heatmap_from_json(input_path, output_path) 