// API 기본 URL 설정
const API_BASE_URL = 'http://localhost:8000';

// 탭 전환 기능
document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');

            // 모든 탭 버튼과 컨텐츠에서 active 클래스 제거
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // 선택된 탭 활성화
            button.classList.add('active');
            document.getElementById(`${targetTab}-tab`).classList.add('active');

            // 결과 초기화
            clearResults();
        });
    });

    // 제품 분석 버튼
    document.getElementById('analyze-btn').addEventListener('click', handleAnalyze);

    // 제품 비교 버튼
    document.getElementById('compare-btn').addEventListener('click', handleCompare);
});

// 결과 초기화
function clearResults() {
    document.getElementById('analyze-result').style.display = 'none';
    document.getElementById('compare-result').style.display = 'none';
    document.getElementById('error-message').style.display = 'none';
}

// 로딩 표시
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// 에러 메시지 표시
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// 제품 분석 처리
async function handleAnalyze() {
    const productName = document.getElementById('product-name').value.trim();
    const analysisType = document.getElementById('analysis-type').value;
    const analyzeBtn = document.getElementById('analyze-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const btnLoader = analyzeBtn.querySelector('.btn-loader');

    if (!productName) {
        showError('제품명을 입력해주세요.');
        return;
    }

    // 버튼 비활성화 및 로딩 표시
    analyzeBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-block';
    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/analyze-product`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_name: productName,
                analysis_type: analysisType
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '분석 중 오류가 발생했습니다.');
        }

        // 결과 표시
        displayAnalyzeResult(data);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || '제품 분석 중 오류가 발생했습니다.');
    } finally {
        // 버튼 활성화 및 로딩 숨김
        analyzeBtn.disabled = false;
        btnText.style.display = 'inline-block';
        btnLoader.style.display = 'none';
        hideLoading();
    }
}

// 제품 분석 결과 표시
function displayAnalyzeResult(data) {
    document.getElementById('result-product-name').textContent = data.product_name;
    document.getElementById('result-model-name').textContent = data.model_name;
    document.getElementById('result-url').textContent = data.url;
    document.getElementById('result-url').href = data.url;

    // 분석 내용 표시 (마크다운 형식 지원)
    const analysisDiv = document.getElementById('analyze-analysis');
    analysisDiv.innerHTML = formatAnalysisText(data.analysis);
    
    // JSON 파일 정보 표시
    if (data.json_file) {
        const jsonInfo = document.createElement('div');
        jsonInfo.className = 'json-file-info';
        jsonInfo.innerHTML = `
            <p><strong>📄 JSON 파일 저장됨:</strong> <code>${data.json_file}</code></p>
            <p class="json-file-note">분석 결과가 JSON 파일로 저장되었습니다. 나중에 다시 확인할 수 있습니다.</p>
        `;
        analysisDiv.appendChild(jsonInfo);
    }
    
    // JSON 데이터 표시 (디버깅/확인용)
    const jsonDataDiv = document.getElementById('analyze-json-data');
    if (jsonDataDiv) {
        jsonDataDiv.textContent = JSON.stringify(data, null, 2);
    }

    document.getElementById('analyze-result').style.display = 'block';
    document.getElementById('analyze-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 제품 비교 처리
async function handleCompare() {
    const productNamesText = document.getElementById('product-names').value.trim();
    const compareBtn = document.getElementById('compare-btn');
    const btnText = compareBtn.querySelector('.btn-text');
    const btnLoader = compareBtn.querySelector('.btn-loader');

    if (!productNamesText) {
        showError('제품명을 입력해주세요.');
        return;
    }

    // 쉼표로 구분된 제품명 파싱
    const productNames = productNamesText
        .split(',')
        .map(name => name.trim())
        .filter(name => name.length > 0);

    if (productNames.length < 2) {
        showError('최소 2개 이상의 제품명을 입력해주세요.');
        return;
    }

    // 버튼 비활성화 및 로딩 표시
    compareBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-block';
    showLoading();

    try {
        const response = await fetch(`${API_BASE_URL}/compare-with-ai`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_names: productNames
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '비교 중 오류가 발생했습니다.');
        }

        // 결과 표시
        displayCompareResult(data);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || '제품 비교 중 오류가 발생했습니다.');
    } finally {
        // 버튼 활성화 및 로딩 숨김
        compareBtn.disabled = false;
        btnText.style.display = 'inline-block';
        btnLoader.style.display = 'none';
        hideLoading();
    }
}

// 제품 비교 결과 표시
function displayCompareResult(data) {
    const productsGrid = document.getElementById('compare-products');
    productsGrid.innerHTML = '';

    // 각 제품 정보 카드 생성
    data.products.forEach((product, index) => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';
        productCard.innerHTML = `
            <h4>제품 ${index + 1}: ${product.product_name}</h4>
            <div class="info-item">
                <span class="info-label">모델명:</span>
                <span class="info-value">${product.model_name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">이미지:</span>
                <span class="info-value">${product.image_count}개</span>
            </div>
            <div class="info-item">
                <span class="info-label">상세 페이지:</span>
                <a href="${product.url}" target="_blank" class="info-link">링크</a>
            </div>
        `;
        productsGrid.appendChild(productCard);
    });

    // 비교 분석 내용 표시
    const analysisDiv = document.getElementById('compare-analysis');
    analysisDiv.innerHTML = formatAnalysisText(data.comparison_analysis);
    
    // JSON 파일 정보 표시
    if (data.json_file) {
        const jsonInfo = document.createElement('div');
        jsonInfo.className = 'json-file-info';
        jsonInfo.innerHTML = `
            <p><strong>📄 JSON 파일 저장됨:</strong> <code>${data.json_file}</code></p>
            <p class="json-file-note">비교 분석 결과가 JSON 파일로 저장되었습니다. 나중에 다시 확인할 수 있습니다.</p>
        `;
        analysisDiv.appendChild(jsonInfo);
    }
    
    // JSON 데이터 표시 (디버깅/확인용)
    const jsonDataDiv = document.getElementById('compare-json-data');
    if (jsonDataDiv) {
        jsonDataDiv.textContent = JSON.stringify(data, null, 2);
    }

    document.getElementById('compare-result').style.display = 'block';
    document.getElementById('compare-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 분석 텍스트 포맷팅 (섹션 카드 형태)
function formatAnalysisText(text) {
    if (!text) return '';

    const normalized = text.replace(/\r\n/g, '\n').trim();
    if (!normalized) return '';

    const rawBlocks = normalized.split(/\n\s*\n/).filter(block => block.trim().length > 0);
    const mergedBlocks = mergeHeadingBlocks(rawBlocks);

    const sections = mergedBlocks.map((block, index) => {
        const { title, body } = extractSection(block, index);
        return `
            <section class="analysis-section">
                <div class="analysis-section-header">
                    <span class="analysis-section-index">${String(index + 1).padStart(2, '0')}</span>
                    <h4>${title}</h4>
                </div>
                <div class="analysis-section-body">
                    ${convertMarkdown(body)}
                </div>
            </section>
        `;
    });

    return `<div class="analysis-grid">${sections.join('')}</div>`;
}

function mergeHeadingBlocks(blocks) {
    const merged = [];
    for (let i = 0; i < blocks.length; i++) {
        const current = blocks[i].trim();
        const next = blocks[i + 1] ? blocks[i + 1].trim() : '';
        const isHeadingOnly = current.split('\n').length === 1 && !/^[-*•\d]/.test(current);

        if (isHeadingOnly && next) {
            merged.push(`${current}\n${next}`.trim());
            i++; // skip next because merged
        } else {
            merged.push(current);
        }
    }
    return merged;
}

function extractSection(block, index) {
    const lines = block.split('\n').map(line => line.trim()).filter(Boolean);
    if (!lines.length) {
        return {
            title: `섹션 ${String(index + 1).padStart(2, '0')}`,
            body: block
        };
    }

    const firstLine = lines[0];
    let title = '';
    let bodyLines = lines.slice(1);

    const headingMatch = firstLine.match(/^#{1,6}\s*(.+)$/);
    const boldMatch = firstLine.match(/^\*\*(.+)\*\*$/);
    const colonMatch = firstLine.match(/^(.+?)[：:]\s*$/);
    const simpleTitle = /^[^\-\*\d]{2,20}$/u.test(firstLine);

    if (headingMatch) {
        title = headingMatch[1].trim();
    } else if (boldMatch) {
        title = boldMatch[1].trim();
    } else if (colonMatch) {
        title = colonMatch[1].trim();
    } else if (simpleTitle && lines.length > 1) {
        title = firstLine.trim();
    }

    if (!title) {
        title = `섹션 ${String(index + 1).padStart(2, '0')}`;
        bodyLines = lines;
    } else if (!bodyLines.length) {
        bodyLines = lines;
    }

    return {
        title,
        body: bodyLines.join('\n').trim()
    };
}

function convertMarkdown(text) {
    if (!text) return '';

    let content = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    const lines = content.split('\n');
    let html = '';
    let inList = false;

    lines.forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) {
            if (inList) return;
            html += '';
            return;
        }

        const isListItem = /^[-*•]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed);
        if (isListItem) {
            if (!inList) {
                inList = true;
                html += '<ul>';
            }
            const itemText = trimmed.replace(/^[-*•]\s+/, '').replace(/^\d+\.\s+/, '');
            html += `<li>${itemText}</li>`;
        } else {
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            html += `<p>${trimmed}</p>`;
        }
    });

    if (inList) {
        html += '</ul>';
    }

    return html || `<p>${text}</p>`;
}
