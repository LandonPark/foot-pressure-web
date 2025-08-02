import json
import numpy as np
import os

def create_json_data(pressure_matrix, filename, output_dir):
    """
    Numpy 배열을 받아 족저압 데이터 JSON 형식으로 저장합니다.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    data = {
        "FrameCounter": 1,
        "RawPressureByRows": {}
    }
    
    rows, _ = pressure_matrix.shape
    for i in range(rows):
        row_str = ", ".join(map(str, pressure_matrix[i].astype(int)))
        data["RawPressureByRows"][f"Row_{i}"] = row_str
        
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"✅ 현실적인 테스트 데이터 생성: {filename}")

def create_pressure_blob(rows, cols, center_y, center_x, max_pressure=255, size_y=5, size_x=5):
    """
    지정된 위치에 중심이 강하고 주변으로 갈수록 약해지는 
    현실적인 압력 덩어리(가우시안 블롭)를 생성합니다.
    """
    y, x = np.ogrid[:rows, :cols]
    
    # 가우시안 함수를 사용하여 블롭 생성
    gauss = np.exp(-(((y - center_y)**2 / (2 * size_y**2)) + ((x - center_x)**2 / (2 * size_x**2))))
    
    # 최대 압력 값을 적용하고 정수형으로 변환
    blob = gauss * max_pressure
    return blob.astype(int)

if __name__ == '__main__':
    # --- 설정 ---
    SENSOR_ROWS = 40
    SENSOR_COLS_TOTAL = 40
    FOOT_COLS = SENSOR_COLS_TOTAL // 2
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    output_dir = os.path.join(project_root, 'data', 'input')

    # --- 10가지 '현실적인' 테스트 케이스 정의 및 생성 ---

    # Case 1: Forefoot Only
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=35, center_x=10, size_y=4, size_x=6)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=35, center_x=30, size_y=4, size_x=6)
    create_json_data(matrix, "realistic_test_01_forefoot_only.json", output_dir)

    # Case 2: Hindfoot Only
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=5, center_x=10, size_y=4, size_x=7)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=5, center_x=30, size_y=4, size_x=7)
    create_json_data(matrix, "realistic_test_02_hindfoot_only.json", output_dir)
    
    # Case 3: Midfoot Only
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=10, size_y=5)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=30, size_y=5)
    create_json_data(matrix, "realistic_test_03_midfoot_only.json", output_dir)

    # Case 4: Pes Cavus (Extreme)
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=5, center_x=10, max_pressure=150, size_y=3) # Left Hind
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=35, center_x=10, max_pressure=200, size_y=3) # Left Fore
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=5, center_x=30, max_pressure=150, size_y=3) # Right Hind
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=35, center_x=30, max_pressure=200, size_y=3) # Right Fore
    create_json_data(matrix, "realistic_test_04_pes_cavus_extreme.json", output_dir)

    # Case 5: Flat Foot
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=10, size_y=15, size_x=4)
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=30, size_y=15, size_x=4)
    create_json_data(matrix, "realistic_test_05_flat_foot.json", output_dir)

    # Case 6: Diagonal Pressure (Left Foot)
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=10, size_y=15, size_x=2) # Left
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=30, size_y=10, size_x=5) # Right
    create_json_data(matrix, "realistic_test_06_diagonal_pressure.json", output_dir)

    # Case 7: Single Large Blob (Right Foot)
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=20, center_x=30, size_y=12, size_x=6)
    create_json_data(matrix, "realistic_test_07_single_large_blob.json", output_dir)

    # Case 8: Tiny Speck Noise
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[10, 10] = 5 # Left single point noise
    create_json_data(matrix, "realistic_test_08_tiny_speck_noise.json", output_dir)

    # Case 9: Asymmetric (Left Hind, Right Fore)
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=5, center_x=10, size_y=4, size_x=7) # Left Hind
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=35, center_x=30, size_y=4, size_x=6) # Right Fore
    create_json_data(matrix, "realistic_test_09_asymmetric.json", output_dir)

    # Case 10: Edge of Sensor
    matrix = create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=0, center_x=10, size_y=2) # Left Top Edge
    matrix += create_pressure_blob(SENSOR_ROWS, FOOT_COLS, center_y=39, center_x=30, size_y=2) # Right Bottom Edge
    create_json_data(matrix, "realistic_test_10_edge_of_sensor.json", output_dir)
    
    print("\n모든 '현실적인' 테스트 데이터 생성이 완료되었습니다.") 