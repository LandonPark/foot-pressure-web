// 백엔드 API 주소
const API_ENDPOINT = "https://foot-pressure-web.onrender.com/analyze";

// --- DOM 요소 가져오기 ---
const fileInput = document.getElementById("fileInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const fileNameDisplay = document.getElementById("fileName");

const resultsContainer = document.getElementById("results");
const resultImage = document.getElementById("resultImage");
const resultTableBody = document.querySelector("#resultTable tbody");

const imageSpinner = document.getElementById("imageSpinner");
const errorMessage = document.getElementById("error-message");

// 선택된 파일 객체를 저장할 변수
let selectedFile = null;

// --- 초기화 ---
// 분석 버튼은 파일이 선택되기 전까지 비활성화
analyzeBtn.disabled = true;

// --- 이벤트 리스너 등록 ---

// 파일 입력(input)이 변경되었을 때
fileInput.addEventListener("change", (event) => {
    selectedFile = event.target.files[0];
    if (selectedFile) {
        // 파일 이름 표시 및 분석 버튼 활성화
        fileNameDisplay.textContent = `선택된 파일: ${selectedFile.name}`;
        analyzeBtn.disabled = false;
        // 이전 결과 숨기기
        hideResults();
    } else {
        fileNameDisplay.textContent = "";
        analyzeBtn.disabled = true;
    }
});

// 분석 시작 버튼 클릭 시
analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) {
        showError("분석할 파일을 먼저 선택해주세요.");
        return;
    }

    // UI를 분석 중 상태로 변경
    setLoadingState(true);

    // FormData 객체를 사용하여 파일을 감쌈
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        // 백엔드 API 호출
        const response = await fetch(API_ENDPOINT, {
            method: "POST",
            body: formData,
        });

        // 응답 상태 코드 확인
        if (!response.ok) {
            // 서버에서 보낸 에러 메시지를 추출
            const errorData = await response.json();
            throw new Error(errorData.detail || `서버 오류 발생: ${response.status}`);
        }

        // 성공적인 응답 처리
        const data = await response.json();
        displayResults(data);

    } catch (error) {
        // 네트워크 오류 또는 위에서 throw한 에러 처리
        showError(`분석 중 오류가 발생했습니다: ${error.message}`);
    } finally {
        // 분석이 끝나면 로딩 상태 해제
        setLoadingState(false);
    }
});


// --- UI 제어 함수 ---

/**
 * 분석 결과를 화면에 표시하는 함수
 * @param {object} data - 백엔드에서 받은 분석 결과 데이터
 */
function displayResults(data) {
    // 1. 결과 컨테이너 보이기
    resultsContainer.classList.remove("hidden");

    // 2. Base64 이미지를 이미지 태그에 설정
    if (data.image_base64) {
        resultImage.src = `data:image/png;base64,${data.image_base64}`;
        resultImage.classList.remove("hidden");
    }

    // 3. 테이블 데이터 채우기
    updateTable(data.analysis_results);
}

/**
 * 분석 결과를 테이블에 채워 넣는 함수
 * @param {object} results - 분석 결과 중 수치 데이터 객체
 */
function updateTable(results) {
    // 테이블 내용 초기화
    resultTableBody.innerHTML = "";
    
    const footTypes = results.foot_types || {};
    const distribution = results.distribution || {};
    
    const leftData = {
        type: footTypes['왼쪽']?.type || 'N/A',
        ai: footTypes['왼쪽']?.value || 0,
        hind: distribution['LH'] || 0,
        mid: distribution['LM'] || 0,
        fore: distribution['LF'] || 0,
    };
    
    const rightData = {
        type: footTypes['오른쪽']?.type || 'N/A',
        ai: footTypes['오른쪽']?.value || 0,
        hind: distribution['RH'] || 0,
        mid: distribution['RM'] || 0,
        fore: distribution['RF'] || 0,
    };

    // 테이블 행 데이터 정의
    const tableRows = [
        { item: "발 유형", left: leftData.type.split(' ')[0], right: rightData.type.split(' ')[0] },
        { item: "아치 지수 (AI)", left: leftData.ai.toFixed(3), right: rightData.ai.toFixed(3) },
        { item: "뒤꿈치 압력 (%)", left: leftData.hind.toFixed(1), right: rightData.hind.toFixed(1) },
        { item: "중간 압력 (%)", left: leftData.mid.toFixed(1), right: rightData.mid.toFixed(1) },
        { item: "앞꿈치 압력 (%)", left: leftData.fore.toFixed(1), right: rightData.fore.toFixed(1) },
    ];

    // 각 행을 테이블에 추가
    tableRows.forEach(rowData => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${rowData.item}</td>
            <td>${rowData.left}</td>
            <td>${rowData.right}</td>
        `;
        resultTableBody.appendChild(row);
    });
}

/**
 * 로딩 상태를 설정하는 함수
 * @param {boolean} isLoading - 로딩 중인지 여부
 */
function setLoadingState(isLoading) {
    if (isLoading) {
        imageSpinner.classList.remove("hidden");
        resultImage.classList.add("hidden");
        resultsContainer.classList.remove("hidden"); // 스피너를 보여주기 위해 결과 컨테이너는 보이게 함
        errorMessage.classList.add("hidden"); // 에러 메시지는 숨김
        analyzeBtn.disabled = true; // 분석 중에는 버튼 비활성화
    } else {
        imageSpinner.classList.add("hidden");
        analyzeBtn.disabled = false; // 분석 완료 후 버튼 다시 활성화
    }
}

/**
 * 에러 메시지를 화면에 표시하는 함수
 * @param {string} message - 표시할 에러 메시지
 */
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove("hidden");
    resultsContainer.classList.add("hidden"); // 에러 발생 시 결과창 숨김
}

/**
 * 결과 및 에러 메시지를 숨기는 함수
 */
function hideResults() {
    resultsContainer.classList.add("hidden");
    errorMessage.classList.add("hidden");
    resultImage.classList.add("hidden");
    resultTableBody.innerHTML = "";
}
