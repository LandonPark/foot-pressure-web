import json
import numpy as np
import os

def create_json_data(pressure_matrix, filename, output_dir):
    """Numpy 배열을 받아 족저압 데이터 JSON 형식으로 저장합니다."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    data = {"FrameCounter": 1, "RawPressureByRows": {}}
    rows, _ = pressure_matrix.shape
    for i in range(rows):
        row_str = ", ".join(map(str, pressure_matrix[i].astype(int)))
        data["RawPressureByRows"][f"Row_{i}"] = row_str
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"✅ 평발 테스트 데이터 생성: {filename}")

def create_pressure_blob(rows, cols, center_y, center_x, max_pressure=255, size_y=5, size_x=5):
    """지정된 위치에 가우시안 블롭을 생성합니다."""
    y, x = np.ogrid[:rows, :cols]
    gauss = np.exp(-(((y - center_y)**2 / (2 * size_y**2)) + ((x - center_x)**2 / (2 * size_x**2))))
    blob = gauss * max_pressure
    return blob.astype(int)

def create_flat_foot_shape(is_left=True, severity='mild'):
    """
    평발 형태의 압력 데이터를 생성합니다.
    severity: 'mild' 또는 'severe'
    """
    matrix = np.zeros((SENSOR_ROWS, FOOT_COLS))
    heel_x = 10
    
    # 1. 뒤꿈치
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=7, center_x=heel_x, max_pressure=180, size_y=5, size_x=5)
    
    # 2. 중간발 (평발의 핵심)
    midfoot_pressure = 200 if severity == 'severe' else 150
    midfoot_size_x = 6 if severity == 'severe' else 5
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=heel_x, max_pressure=midfoot_pressure, size_y=8, size_x=midfoot_size_x)

    # 3. 앞꿈치/발가락
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=34, center_x=heel_x, max_pressure=150, size_y=4, size_x=6)
    
    return matrix

if __name__ == '__main__':
    # --- 설정 ---
    SENSOR_ROWS = 40
    SENSOR_COLS_TOTAL = 40
    FOOT_COLS = SENSOR_COLS_TOTAL // 2
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    output_dir = os.path.join(project_root, 'data', 'input')

    # --- '평발' 테스트 케이스 생성 ---

    # Case 1: Mild Flat Foot (가벼운 평발)
    left_foot = create_flat_foot_shape(is_left=True, severity='mild')
    right_foot = create_flat_foot_shape(is_left=False, severity='mild')
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "flat_foot_test_01_mild.json", output_dir)
    
    # Case 2: Severe Flat Foot (심한 평발)
    left_foot = create_flat_foot_shape(is_left=True, severity='severe')
    right_foot = create_flat_foot_shape(is_left=False, severity='severe')
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "flat_foot_test_02_severe.json", output_dir)

    print("\n모든 '평발' 테스트 데이터 생성이 완료되었습니다.") 