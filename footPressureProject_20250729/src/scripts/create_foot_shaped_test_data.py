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
    print(f"✅ 발 모양 테스트 데이터 생성: {filename}")

def create_pressure_blob(rows, cols, center_y, center_x, max_pressure=255, size_y=5, size_x=5):
    """지정된 위치에 가우시안 블롭을 생성합니다."""
    y, x = np.ogrid[:rows, :cols]
    gauss = np.exp(-(((y - center_y)**2 / (2 * size_y**2)) + ((x - center_x)**2 / (2 * size_x**2))))
    blob = gauss * max_pressure
    return blob.astype(int)

def create_foot_shape(is_left=True):
    """
    여러 개의 블롭을 조합하여 실제 발과 유사한 모양의 압력 데이터를 생성합니다.
    """
    matrix = np.zeros((SENSOR_ROWS, FOOT_COLS))
    
    # 1. 뒤꿈치 (Heel)
    heel_x = 10 if is_left else 10 # 좌우 대칭 위치
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=7, center_x=heel_x, max_pressure=200, size_y=5, size_x=5)
    
    # 2. 중족부 아치 (Metatarsal Arch)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=heel_x+2, max_pressure=100, size_y=7, size_x=3)

    # 3. 발가락 부분 (Toes)
    # 엄지 발가락 (Hallux)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=34, center_x=heel_x-2, max_pressure=180, size_y=3, size_x=3)
    # 나머지 발가락들
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=32, center_x=heel_x+2, max_pressure=120, size_y=2, size_x=2)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=31, center_x=heel_x+5, max_pressure=110, size_y=2, size_x=2)
    
    return matrix

if __name__ == '__main__':
    # --- 설정 ---
    SENSOR_ROWS = 40
    SENSOR_COLS_TOTAL = 40
    FOOT_COLS = SENSOR_COLS_TOTAL // 2
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    output_dir = os.path.join(project_root, 'data', 'input')

    # --- '발 모양' 테스트 케이스 생성 ---

    # Case 1: Normal Full Footprint
    left_foot = create_foot_shape(is_left=True)
    right_foot = create_foot_shape(is_left=False)
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "foot_shape_test_01_normal.json", output_dir)
    
    # Case 2: Forefoot Only (까치발)
    left_foot = create_foot_shape(is_left=True)
    right_foot = create_foot_shape(is_left=False)
    left_foot[:25, :] = 0 # 뒤꿈치, 중간 부분 제거
    right_foot[:25, :] = 0
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "foot_shape_test_02_forefoot_only.json", output_dir)

    # Case 3: Hindfoot Only (발끝 들기)
    left_foot = create_foot_shape(is_left=True)
    right_foot = create_foot_shape(is_left=False)
    left_foot[15:, :] = 0 # 중간, 앞꿈치 부분 제거
    right_foot[15:, :] = 0
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "foot_shape_test_03_hindfoot_only.json", output_dir)

    # Case 4: Asymmetric (Left Full, Right Forefoot)
    left_foot = create_foot_shape(is_left=True)
    right_foot = create_foot_shape(is_left=False)
    right_foot[:25, :] = 0 # 오른쪽만 까치발
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "foot_shape_test_04_asymmetric.json", output_dir)
    
    # Case 5: Single Foot Only (Left)
    left_foot = create_foot_shape(is_left=True)
    right_foot = np.zeros_like(left_foot) # 오른쪽 발 없음
    full_matrix = np.concatenate((left_foot, right_foot), axis=1)
    create_json_data(full_matrix, "foot_shape_test_05_single_foot.json", output_dir)

    print("\n모든 '발 모양' 테스트 데이터 생성이 완료되었습니다.") 