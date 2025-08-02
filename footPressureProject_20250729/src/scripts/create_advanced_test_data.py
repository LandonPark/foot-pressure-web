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
        # Numpy 배열의 행을 ", "로 구분된 문자열로 변환
        row_str = ", ".join(map(str, pressure_matrix[i].astype(int)))
        data["RawPressureByRows"][f"Row_{i}"] = row_str
        
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"✅ 테스트 데이터 생성: {filename}")


if __name__ == '__main__':
    # --- 설정 ---
    SENSOR_ROWS = 40
    SENSOR_COLS_TOTAL = 40
    FOOT_COLS = SENSOR_COLS_TOTAL // 2
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    # 모든 테스트 케이스는 기본 input 폴더에 저장
    output_dir = os.path.join(project_root, 'data', 'input')

    # --- 10가지 테스트 케이스 정의 및 생성 ---

    # Case 1: Forefoot Only
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[30:39, 5:15] = 100 # Left
    matrix[30:39, 25:35] = 100 # Right
    create_json_data(matrix, "adv_test_01_forefoot_only.json", output_dir)

    # Case 2: Hindfoot Only
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[1:10, 5:15] = 100 # Left
    matrix[1:10, 25:35] = 100 # Right
    create_json_data(matrix, "adv_test_02_hindfoot_only.json", output_dir)
    
    # Case 3: Midfoot Only
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[15:25, 5:15] = 100 # Left
    matrix[15:25, 25:35] = 100 # Right
    create_json_data(matrix, "adv_test_03_midfoot_only.json", output_dir)

    # Case 4: Pes Cavus (Extreme)
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[2:7, 5:15] = 80 # Left Hind
    matrix[33:38, 5:15] = 120 # Left Fore
    matrix[2:7, 25:35] = 80 # Right Hind
    matrix[33:38, 25:35] = 120 # Right Fore
    create_json_data(matrix, "adv_test_04_pes_cavus_extreme.json", output_dir)

    # Case 5: Flat Foot
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[5:35, 5:15] = np.random.randint(50, 150, size=(30,10)) # Left
    matrix[5:35, 25:35] = np.random.randint(50, 150, size=(30,10)) # Right
    create_json_data(matrix, "adv_test_05_flat_foot.json", output_dir)

    # Case 6: Diagonal Pressure
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    for i in range(20):
        matrix[i+5, i] = 150 # Left Diagonal
    matrix[10:30, 25:35] = 100 # Right Normal
    create_json_data(matrix, "adv_test_06_diagonal_pressure.json", output_dir)

    # Case 7: Single Large Blob
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[10:30, 25:35] = 200 # Right blob
    create_json_data(matrix, "adv_test_07_single_large_blob.json", output_dir)

    # Case 8: Tiny Speck Noise
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[10, 10] = 5 # Left single point
    create_json_data(matrix, "adv_test_08_tiny_speck_noise.json", output_dir)

    # Case 9: Asymmetric (Left Hind, Right Fore)
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[1:10, 5:15] = 100 # Left Hind
    matrix[30:39, 25:35] = 100 # Right Fore
    create_json_data(matrix, "adv_test_09_asymmetric.json", output_dir)

    # Case 10: Edge of Sensor
    matrix = np.zeros((SENSOR_ROWS, SENSOR_COLS_TOTAL))
    matrix[0, 5:15] = 100 # Left Top Edge
    matrix[39, 25:35] = 100 # Right Bottom Edge
    create_json_data(matrix, "adv_test_10_edge_of_sensor.json", output_dir)

    print("\n모든 고급 테스트 데이터 생성이 완료되었습니다.") 