
# 코드 설명서: Podo Analyzer

본 문서는 macOS용 족저압 분석 애플리케이션의 소스 코드 구조와 각 파일의 역할을 설명합니다.

## 1. 프로젝트 구조

```
footPressureProject_20250729/
├── src/
│   ├── analyzer_engine.py       # (핵심) 분석 로직 엔진
│   ├── analyzer_main.py         # (CLI) 터미널 기반 분석 실행기
│   ├── config.py                # 전역 설정 (경로, 파라미터 등)
│   ├── gui_app.py               # (GUI) Tkinter 기반 고급 GUI 앱
│   ├── podo_analyzer_pyside.py  # (GUI) PySide6 기반 GUI 앱
│   ├── podo_analyzer_gui.py     # (GUI) Tkinter 기반 기본 GUI 앱 (이미지 로더)
│   ├── new_gui_app.py           # (GUI) podo_analyzer_gui.py의 디버그 버전
│   ├── test_gui.py              # (Test) Tkinter 동작 테스트 스크립트
│   ├── archive/                 # 이전 버전 또는 실험용 코드 보관
│   │   ├── main.py
│   │   ├── virtual_footprint_analyzer.py
│   │   └── foot_type_analyzer.py
│   └── scripts/                 # 테스트 데이터 생성용 스크립트
│       ├── create_advanced_test_data.py
│       ├── create_flat_foot_test_data.py
│       ├── create_foot_shaped_test_data.py
│       └── create_realistic_test_data.py
└── ... (data, venv 등)
```

## 2. `src` 디렉토리 주요 파일 상세 설명

### 2.1. `analyzer_engine.py`

-   **역할**: **핵심 분석 엔진**
-   **상세 내용**:
    -   `FootPressureAnalyzer` 클래스를 통해 족저압 분석의 모든 과정을 캡슐화합니다.
    -   JSON 데이터 로딩, 노이즈 필터링, 압력 중심(CoP) 계산, 좌우 발 분리, 압력 분포 계산, 발 유형(요족, 정상, 평발) 분석 등 핵심 로직을 수행합니다.
    -   분석 결과를 시각화하기 위한 데이터와 실제 이미지 파일(.png) 생성을 담당합니다.
    -   GUI 앱과 CLI 실행기 모두 이 엔진을 가져와 사용합니다.

### 2.2. `config.py`

-   **역할**: **전역 설정 파일**
-   **상세 내용**:
    -   프로젝트의 모든 설정 값을 중앙에서 관리합니다.
    -   데이터 입출력 경로, 로그 파일 경로 등 **경로 설정**.
    -   노이즈 제거 임계값 등 **분석 파라미터**.
    -   발 유형을 분류하는 기준이 되는 Arch Index(AI) 값 등 **분류 기준**.
    -   결과 이미지의 DPI, 크기, 색상, 폰트 등 **시각화 설정**.
    -   코드를 수정하지 않고 이 파일의 값만 변경하여 프로그램의 동작을 쉽게 변경할 수 있습니다.

### 2.3. `analyzer_main.py`

-   **역할**: **명령줄 인터페이스 (CLI) 실행기**
-   **상세 내용**:
    -   터미널 환경에서 `analyzer_engine.py`를 사용하여 분석을 실행합니다.
    -   `-i` (input), `-o` (output) 인자를 받아 특정 폴더에 있는 모든 `.json` 파일을 일괄적으로 분석하고 결과를 저장합니다.
    -   GUI 없이 백엔드 분석 로직만 테스트하거나, 여러 파일을 한 번에 처리할 때 유용합니다.

### 2.4. GUI 관련 파일

#### `gui_app.py` (Tkinter, 고급)

-   **역할**: **메인 GUI 애플리케이션 (추천)**
-   **상세 내용**:
    -   `tkinter`와 `matplotlib`을 결합하여 제작된 가장 기능이 많은 GUI 앱입니다.
    -   분석 실행 시 UI가 멈추는 것을 방지하기 위해 **백그라운드 스레드**에서 `analyzer_engine`을 실행합니다.
    -   분석 결과를 실시간으로 로그 창에 표시하고, 분석이 완료되면 `matplotlib` 그래프를 창 내부에 직접 그려줍니다.

#### `podo_analyzer_pyside.py` (PySide6)

-   **역할**: **PySide6 기반 GUI 애플리케이션**
-   **상세 내용**:
    -   `tkinter` 대신 `PySide6`(Qt) 프레임워크를 사용하여 만든 GUI 앱입니다.
    -   파일 선택 후 분석을 실행하면 실시간으로 `analyzer_engine`을 호출하여 결과를 생성합니다.
    -   분석된 이미지를 보여주는 것과 더불어, 주요 결과(발 유형, 압력 분포 등)를 **테이블 형태**로 깔끔하게 정리하여 보여주는 특징이 있습니다.

#### `podo_analyzer_gui.py` (Tkinter, 기본)

-   **역할**: **기본적인 GUI 뷰어**
-   **상세 내용**:
    -   `tkinter`로 만든 간단한 GUI입니다.
    -   `Analyze Podo` 버튼을 누르면 실시간 분석을 수행하는 것이 아니라, **미리 생성된 결과 이미지 파일**(`analysis_reports` 폴더 내)을 찾아 화면에 보여주는 **뷰어** 역할을 합니다.
    -   `analyzer_engine`을 직접 사용하지 않습니다.

#### `new_gui_app.py` & `test_gui.py`

-   `new_gui_app.py`는 `podo_analyzer_gui.py`에 디버깅용 `print` 구문이 추가된 버전으로 보입니다.
-   `test_gui.py`는 `tkinter` 라이브러리가 정상적으로 동작하는지 확인하기 위한 간단한 테스트 스크립트입니다.

## 3. `src/archive` 디렉토리

-   **역할**: **과거 버전 및 실험용 코드 보관**
-   **상세 내용**:
    -   현재의 `analyzer_engine.py`가 만들어지기까지의 개발 과정을 보여주는 이전 버전의 코드들이 저장되어 있습니다.
    -   `main.py`: 초창기 버전의 분석 스크립트입니다.
    -   `virtual_footprint_analyzer.py`: 발의 일부만 감지되었을 때 전체 발자국을 추론하는 '가상 발자국' 로직이 구현되어 있습니다. 이 기능은 현재 `analyzer_engine`에 통합되었습니다.
    -   `foot_type_analyzer.py`: 발 유형을 분석하는 로직이 집중적으로 구현되어 있습니다. 이 또한 `analyzer_engine`에 통합되었습니다.

## 4. `src/scripts` 디렉토리

-   **역할**: **테스트 데이터 생성기**
-   **상세 내용**:
    -   분석 알고리즘을 검증하기 위한 다양한 종류의 `.json` 테스트 데이터를 생성하는 스크립트 모음입니다.
    -   `create_flat_foot_test_data.py`: 평발(경증/중증) 테스트 데이터를 생성합니다.
    -   `create_foot_shaped_test_data.py`: 일반적인 발 모양, 까치발, 한 발 데이터 등 다양한 발 모양을 시뮬레이션합니다.
    -   `create_realistic_test_data.py`: 가우시안 블롭을 이용해 좀 더 실제와 유사한 압력 분포 데이터를 생성합니다.
    -   `create_advanced_test_data.py`: 간단한 사각형 형태로 특정 영역에만 압력이 가해지는 등 엣지 케이스 테스트 데이터를 생성합니다.

