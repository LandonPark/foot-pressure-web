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
    # 압력이 0보다 큰 영역에 대한 바이너리 마스크 생성
    binary_mask = pressure_array > 0
    
    # binary_opening 연산을 통해 min_size보다 작은 점들을 제거
    # structure=np.ones((2,2))는 2x2 이웃을 연결된 것으로 간주
    cleaned_mask = binary_opening(binary_mask, structure=np.ones((2,2)), iterations=min_size)
    
    # 원본 배열에 클리닝된 마스크를 적용하여 노이즈가 제거된 배열 반환
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

def calculate_pressure_distribution(pressure_array):
    """
    노이즈가 제거된 전체 압력 배열로부터 6개 구역의 압력 분포를 계산합니다.
    양발을 아우르는 통합 Bounding Box를 기준으로 영역을 대칭적으로 나눕니다.
    """
    # 1. 노이즈 제거 전처리
    # (주의: 분포 계산은 원본(노이즈 제거 전) 데이터로 수행하여 실제 값 반영)
    total_pressure_original = np.sum(pressure_array)
    if total_pressure_original == 0:
        return {}

    cleaned_array_for_bbox = filter_noise(pressure_array)
    
    # 2. 통합 Bounding Box 계산
    global_bbox = get_foot_bbox(cleaned_array_for_bbox)
    if not global_bbox:
        return {}
        
    min_r, max_r = global_bbox
    global_height = max_r - min_r + 1
    
    if global_height < 3: # 전체 높이가 너무 작으면 계산 불가
        return {}

    # 3. 통합 기준선 계산
    hind_end_r = min_r + global_height // 3
    mid_end_r = min_r + (global_height * 2) // 3

    # 4. 각 구역별 압력 계산 (계산은 원본 배열 사용)
    rows, cols = pressure_array.shape
    mid_col = cols // 2
    
    left_foot_array = pressure_array[:, :mid_col]
    right_foot_array = pressure_array[:, mid_col:]

    distribution = {
        'LH': np.sum(left_foot_array[min_r:hind_end_r, :]),
        'LM': np.sum(left_foot_array[hind_end_r:mid_end_r, :]),
        'LF': np.sum(left_foot_array[mid_end_r:max_r + 1, :]),
        'RH': np.sum(right_foot_array[min_r:hind_end_r, :]),
        'RM': np.sum(right_foot_array[hind_end_r:mid_end_r, :]),
        'RF': np.sum(right_foot_array[mid_end_r:max_r + 1, :]),
    }

    # 5. 백분율로 변환
    for key in distribution:
        distribution[key] = (distribution[key] / total_pressure_original) * 100
        
    return distribution


def create_heatmap_from_json(json_path, output_path):
    """
    JSON 파일을 읽어 노이즈가 제거된 히트맵을 생성하고, 압력 분포와 영역 구분선을 표시합니다.
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

        # 노이즈 제거 (시각화용)
        cleaned_array_for_viz = filter_noise(pressure_array)
        
        rows, cols = cleaned_array_for_viz.shape
        mid_col = cols // 2
        
        # --- 시각화 (노이즈 제거된 데이터 사용) ---
        fig, ax = plt.subplots(figsize=(4, 8))
        fig.set_facecolor('black')
        ax.set_facecolor('black')

        cmap = plt.get_cmap('jet') 
        ax.imshow(cleaned_array_for_viz, cmap=cmap, interpolation='nearest')
        
        # --- 영역 구분선 그리기 (통합 BBox 기준) ---
        global_bbox = get_foot_bbox(cleaned_array_for_viz)
        if global_bbox:
            min_r, max_r = global_bbox
            global_height = max_r - min_r + 1
            if global_height >= 3:
                hind_end_r = min_r + global_height // 3
                mid_end_r = min_r + (global_height * 2) // 3
                # 양발에 걸쳐 전체 너비로 선 그리기
                ax.axhline(y=hind_end_r - 0.5, xmin=0.05, xmax=0.95, color='white', linestyle='--', linewidth=1.5)
                ax.axhline(y=mid_end_r - 0.5, xmin=0.05, xmax=0.95, color='white', linestyle='--', linewidth=1.5)

        ax.axis('off')

        # --- 압력 분포 계산 및 표시 (계산은 원본 데이터로 수행) ---
        distribution = calculate_pressure_distribution(pressure_array)
        
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
    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    if not json_files:
        print(f"'{input_dir}' 폴더에 분석할 JSON 파일이 없습니다.")
    else:
        print(f"총 {len(json_files)}개의 파일을 분석합니다.")
        for input_path in json_files:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            input_basename = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{input_basename}_{timestamp}_analysis.png"
            output_path = os.path.join(output_dir, output_filename)
            print(f"\n▶️ 처리 중: {os.path.basename(input_path)}")
            create_heatmap_from_json(input_path, output_path) 