# Podo-Analyzer Web: 족저압 분석 웹 애플리케이션

본 프로젝트는 기존 데스크톱으로 구현되었던 족저압 분석 애플리케이션(`PodoAnalyzer.app`)을 웹 환경에서 누구나 쉽게 사용할 수 있도록 전환한 것입니다. 사용자가 족저압 데이터(.json)를 업로드하면, 서버에서 데이터를 분석하고 시각화된 결과 이미지를 웹페이지에 보여줍니다.

## ✨ Live Demo

*   **Frontend (웹사이트 접속 주소):** [https://foot-pressure-frontend.onrender.com](https://foot-pressure-frontend.onrender.com)
*   **Backend (API 서버 주소):** [https://foot-pressure-web.onrender.com](https://foot-pressure-web.onrender.com)

## 🚀 주요 기능

*   JSON 형식의 족저압 데이터 파일 업로드
*   데이터 노이즈 필터링 및 압력 중심(COP) 계산
*   족저압 분포, 발 유형(평발, 요족 등) 상세 분석
*   분석 결과를 포함한 시각화 이미지 생성 및 제공
*   분석 결과 텍스트 데이터 제공

## 🛠️ 기술 스택

*   **Backend**: Python, FastAPI, Uvicorn, Gunicorn
*   **Analysis**: Numpy, Matplotlib, SciPy
*   **Frontend**: HTML, CSS, JavaScript
*   **Deployment**: Render.com (Web Service & Static Site), Git & GitHub

## 📂 프로젝트 구조

```
Cusor_AI_Project_20250729/
│
├── foot_pressure_web/
│   ├── backend/         # FastAPI 백엔드 서버
│   │   ├── main.py        # API 엔드포인트 및 서버 실행
│   │   ├── analyzer_engine.py # 핵심 분석 로직
│   │   └── fonts/         # 시각화에 사용될 폰트
│   │
│   ├── frontend/        # HTML/CSS/JS 프론트엔드
│   │   ├── index.html     # 메인 페이지
│   │   ├── script.js      # 파일 업로드 및 API 통신
│   │   └── style.css      # 스타일시트
│   │
│   └── requirements.txt # Python 라이브러리 의존성
│
└── README.md            # 프로젝트 안내 문서
```

## ⚙️ 로컬 환경에서 실행하기

### 사전 준비

*   Python 3.9 이상
*   Git

### 실행 순서

1.  **저장소 복제**
    ```bash
    git clone https://github.com/LandonPark/foot-pressure-web.git
    cd Cusor_AI_Project_20250729
    ```

2.  **가상 환경 생성 및 활성화**
    ```bash
    # 가상 환경 생성 (최초 1회)
    python3 -m venv foot_pressure_web/venv

    # 가상 환경 활성화 (macOS/Linux)
    source foot_pressure_web/venv/bin/activate
    ```

3.  **의존성 라이브러리 설치**
    ```bash
    pip install -r foot_pressure_web/requirements.txt
    ```

4.  **백엔드 서버 실행**
    ```bash
    cd foot_pressure_web/backend
    uvicorn main:app --host 127.0.0.1 --port 8000 --reload
    ```
    서버가 `http://127.0.0.1:8000` 에서 실행됩니다.

5.  **프론트엔드 실행**
    *   웹 브라우저에서 `foot_pressure_web/frontend/index.html` 파일을 직접 엽니다.
    *   **주의**: 로컬 테스트 시에는 `script.js` 파일의 `API_ENDPOINT` 변수를 로컬 서버 주소(`http://127.0.0.1:8000/analyze`)로 변경해야 합니다.

## ☁️ Render.com 배포 가이드

본 프로젝트는 백엔드와 프론트엔드를 별개의 서비스로 배포합니다.

### 1. 백엔드 배포 (Web Service)

1.  Render 대시보드에서 **[New +] > [Web Service]** 를 선택합니다.
2.  GitHub 저장소 `LandonPark/foot-pressure-web`를 연결합니다.
3.  다음과 같이 설정합니다.
    *   **Name**: `foot-pressure-web` (또는 원하는 이름)
    *   **Root Directory**: `foot_pressure_web`
    *   **Environment**: `Python`
    *   **Build Command**: `pip install -r requirements.txt`
    *   **Start Command**: `cd backend && gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
4.  **[Create Web Service]** 버튼을 눌러 배포를 시작합니다.

### 2. 프론트엔드 배포 (Static Site)

1.  Render 대시보드에서 **[New +] > [Static Site]** 를 선택합니다.
2.  GitHub 저장소 `LandonPark/foot-pressure-web`를 연결합니다.
3.  다음과 같이 설정합니다.
    *   **Name**: `foot-pressure-frontend` (또는 원하는 이름)
    *   **Branch**: `main`
    *   **Publish Directory**: `foot_pressure_web/frontend`
    *   **Build Command**: (공란으로 비워두기)
4.  **[Create Static Site]** 버튼을 눌러 배포를 시작합니다.

### 3. 프론트엔드와 백엔드 연결

배포된 프론트엔드가 백엔드 서버와 통신할 수 있도록, `foot_pressure_web/frontend/script.js` 파일의 `API_ENDPOINT` 변수를 배포된 백엔드 서비스의 주소로 수정해야 합니다.

```javascript
// 예시: foot_pressure_web/frontend/script.js
const API_ENDPOINT = "https://foot-pressure-web.onrender.com/analyze";
```

이 변경사항을 `git push` 하면 Render가 자동으로 프론트엔드를 재배포하여 반영합니다.
