import os
from datetime import datetime

# --- 경로 설정 ---
# 프로젝트의 루트 디렉토리를 기준으로 경로를 설정합니다.
# 이 스크립트(config.py)는 src 폴더 안에 있다고 가정합니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
# 출력 폴더가 없으면 생성
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- 분석 파라미터 ---
ANALYSIS_PARAMS = {
    'noise_threshold': 5,  # 노이즈 제거를 위한 압력 임계값
    'min_foot_area': 100,  # 유효한 발 영역으로 인정하기 위한 최소 픽셀 수
}


# --- 발 유형 분류 기준 ---
# Arch Index (AI) 값을 기준으로 발 유형을 분류합니다.
FOOT_TYPE_CRITERIA = {
    'high_arch': 0.21,  # AI <= 0.21 이면 High Arch (요족)
    'normal': 0.26,     # 0.21 < AI <= 0.26 이면 Normal (정상)
    # 'flat_foot'       # AI > 0.26 이면 Flat Foot (평발)
}


# --- 시각화 설정 ---
def find_font():
    """
    프로젝트에 포함된 NanumGothic.ttf 폰트 파일의 경로를 반환합니다.
    """
    # 프로젝트 내 'fonts' 폴더에 있는 NanumGothic.ttf 경로를 직접 지정
    font_path = os.path.join(BASE_DIR, 'fonts', 'NanumGothic.ttf')
    if os.path.exists(font_path):
        return font_path
    
    # 폰트를 찾지 못하면 None을 반환하고, matplotlib의 기본 폰트를 사용
    return None

# 시각화에 사용할 폰트 경로를 찾습니다.
KOR_FONT_PATH = find_font()

VISUALIZATION = {
    'dpi': 150,                     # 이미지 해상도
    'figsize': (8, 10),             # 이미지 크기 (인치)
    'cmap': 'plasma',              # 압력 분포에 사용할 컬러맵
    'interpolation': 'bilinear',    # 이미지 보간법
    'gaussian_sigma': 0.5,          # 가우시안 필터의 시그마 값
    'font_path': KOR_FONT_PATH,     # 한글 폰트 경로
    'title_fontsize': 16,           # 제목 폰트 크기
    'label_fontsize': 12,           # 축 레이블 폰트 크기
    'regions': {                    # 발 영역 나누기 (전체 세로 길이 기준)
        'hindfoot_ratio': 0.3,      # 뒷꿈치 (30%)
        'midfoot_ratio': 0.4,       # 중간발 (40%)
        'forefoot_ratio': 0.3,      # 앞꿈치 (30%)
    },
    'COP_MARKER': 'x',              # 압력 중심점 마커 모양
    'COP_COLOR': 'red',             # 압력 중심점 마커 색상
    'COP_MARKER_SIZE': 12,          # 압력 중심점 마커 크기
    'CENTER_LINE_COLOR': 'white',   # 중심선 색상
    'CENTER_LINE_STYLE': ':',       # 중심선 스타일
    'CENTER_LINE_WIDTH': 1.5,       # 중심선 두께
}

# --- 로깅 설정 ---
def get_log_filename():
    """ 현재 날짜로 로그 파일 이름을 생성합니다. (예: 20250729_analysis.log) """
    return f"{datetime.now().strftime('%Y%m%d')}_analysis.log"

LOGGING_CONFIG = {
    'log_dir': os.path.join(BASE_DIR, 'logs'),
    'log_filename': get_log_filename(),
    'level': 'INFO', # 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    'format': '[%(asctime)s] [%(levelname)s] %(message)s',
    'datefmt': '%Y-%m-%d %H:%M:%S'
}
# 로그 폴더가 없으면 생성
os.makedirs(LOGGING_CONFIG['log_dir'], exist_ok=True)
