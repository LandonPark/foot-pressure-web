import os
import glob
import argparse
from datetime import datetime
import numpy as np # Numpy import 추가
from config import INPUT_DIR as DEFAULT_INPUT_DIR, OUTPUT_DIR as DEFAULT_OUTPUT_DIR
from analyzer_engine import FootPressureAnalyzer

def main():
    """
    프로젝트의 메인 실행 함수.
    명령줄 인수로 입력/출력 디렉토리를 지정할 수 있습니다.
    """
    parser = argparse.ArgumentParser(description="족부 압력 데이터 분석 및 시각화 스크립트")
    parser.add_argument('-i', '--input', type=str, default=DEFAULT_INPUT_DIR,
                        help=f"분석할 JSON 파일들이 있는 입력 디렉토리. 기본값: {DEFAULT_INPUT_DIR}")
    parser.add_argument('-o', '--output', type=str, default=DEFAULT_OUTPUT_DIR,
                        help=f"분석 결과 이미지를 저장할 출력 디렉토리. 기본값: {DEFAULT_OUTPUT_DIR}")
    
    args = parser.parse_args()
    
    input_dir = args.input
    output_dir = args.output

    os.makedirs(output_dir, exist_ok=True)
    
    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    
    if not json_files:
        print(f"'{input_dir}'에서 분석할 파일을 찾을 수 없습니다.")
        return

    print(f"총 {len(json_files)}개의 파일에 대한 리팩토링된 분석을 시작합니다.")
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    
    for input_path in json_files:
        print(f"\n▶️ 처리 중: {os.path.basename(input_path)}")
        
        try:
            # 1. 분석기 인스턴스 생성 (터미널 실행이므로 ui_logger는 None)
            analyzer = FootPressureAnalyzer(input_path)
            
            # 2. 분석 실행
            success = analyzer.run_analysis()
            
            if success:
                # 3. 시각화 데이터 가져오기
                vis_data = analyzer.get_visualization_data()
                if not vis_data:
                    print(f"❗️'{os.path.basename(input_path)}'에 대한 시각화 데이터 생성에 실패했습니다.")
                    continue

                # 4. 데이터 타입을 시각화에 맞게 변환 (List -> Numpy Array)
                vis_data['pressure_data'] = np.array(vis_data['pressure_data'])

                # 5. 시각화 결과 저장
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                input_basename = os.path.splitext(os.path.basename(input_path))[0]
                output_filename = f"{input_basename}_{timestamp}_report.png"
                output_path = os.path.join(output_dir, output_filename)
                
                analyzer.save_visualization(output_path, vis_data)
        
        except Exception as e:
            print(f"❗️ 치명적 오류: '{os.path.basename(input_path)}' 처리 중 예외 발생 - {e}")

if __name__ == '__main__':
    main() 