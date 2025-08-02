import uvicorn
import json
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler  # (추가) 파일 로깅을 위해 import
import time
import os
from contextlib import asynccontextmanager

from analyzer_engine import (
    FootPressureAnalyzer, 
    setup_matplotlib_font,
    convert_numpy_to_native
)

# --- (수정) 파일 로거 설정 ---
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, 'backend.log')

# 기본 로거를 가져옵니다.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 로그 레벨 설정

# 모든 이전 핸들러를 제거합니다 (uvicorn의 기본 핸들러 등).
for handler in logger.handlers[:]:
    logger.removeHandler(handler)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# 파일 핸들러 생성 (5MB 크기로 로테이션, 3개 백업)
# 'a' (append) 모드로 파일을 열어 로그를 누적합니다.
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# 로그 포맷 설정
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 핸들러를 로거에 추가
logger.addHandler(file_handler)

# FastAPI와 uvicorn 로거에도 핸들러를 추가하여 모든 로그를 파일로 보냅니다.
logging.getLogger("fastapi").addHandler(file_handler)
logging.getLogger("uvicorn").addHandler(file_handler)
logging.getLogger("uvicorn.access").addHandler(file_handler)
logging.getLogger("uvicorn.error").addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server is starting up...")
    setup_matplotlib_font()
    yield
    logger.info("Server is shutting down...")

app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    logger.info("Root endpoint was called.")
    return {"message": "Podo-Analyzer Web API is running."}

@app.post("/analyze")
async def analyze_pressure_data(file: UploadFile = File(...)):
    request_id = f"req_{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] Analysis request received for file: {file.filename}")

    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="잘못된 파일 타입입니다. .json 파일을 업로드해주세요.")

        try:
            contents = await file.read()
            json_data = json.loads(contents.decode('utf-8'))
        finally:
            await file.close()

        analyzer = FootPressureAnalyzer(json_data=json_data, filename=file.filename)
        
        if not analyzer.run_analysis():
            error_msg = analyzer.error_message or "알 수 없는 분석 오류가 발생했습니다."
            raise HTTPException(status_code=500, detail=error_msg)

        vis_data = analyzer.get_visualization_data()
        if not vis_data:
            raise HTTPException(status_code=500, detail="시각화 데이터 생성에 실패했습니다.")
        
        image_base64 = analyzer.get_visualization_as_base64(vis_data)
        if not image_base64:
            raise HTTPException(status_code=500, detail="시각화 이미지 생성에 실패했습니다.")

        logger.info(f"[{request_id}] Sending successful response.")
        return convert_numpy_to_native({
            "analysis_results": vis_data.get('analysis_results'),
            "image_base64": image_base64
        })
    except HTTPException as http_exc:
        logger.warning(f"[{request_id}] HTTP exception occurred: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.critical(f"[{request_id}] An unexpected error occurred: {e}")
        logger.critical(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"서버 내부에서 예상치 못한 오류가 발생했습니다.")


if __name__ == "__main__":
    logger.info("Starting Podo-Analyzer Web API server from __main__...")
    # uvicorn.run의 log_config를 None으로 설정하여 저희가 커스텀한 로거만 사용되도록 합니다.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_config=None)
