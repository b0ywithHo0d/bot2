import streamlit as st
from PIL import Image
import pytesseract
import requests
import openai
import urllib.parse
import urllib3
import cv2
import numpy as np

# 경고 무시 (인증서 관련)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Tesseract 경로 (Streamlit Cloud 기준)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# ===== 사이드바 - API 키 입력 =====
st.sidebar.title("🔐 API 키 입력")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
drug_api_key = st.sidebar.text_input("공공데이터 API Key", type="password")

# ===== 이미지 업로드 =====
st.title("💊 약 성분 분석 및 병용 주의")
uploaded_images = st.file_uploader("약 사진 여러 장을 업로드하세요", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

def preprocess_image(pil_image):
    # PIL -> OpenCV 변환
    cv_image = np.array(pil_image.convert('RGB'))
    cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)

    # 그레이스케일 변환
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # 이진화 (임계값 150 조정 가능)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # 노이즈 제거(모폴로지 연산) - 필요 시 주석 해제
    # kernel = np.ones((1,1), np.uint8)
    # thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # OpenCV -> PIL 변환
    processed_pil = Image.fromarray(thresh)
    return processed_pil

if uploaded_images and openai_key:
    extracted_texts = []

    for uploaded_file in uploaded_images:
        image = Image.open(uploaded_file)
        st.image(image, caption="원본 이미지", use_container_width=True)

        # 전처리 후 OCR
        processed_image = preprocess_image(image)
        st.image(processed_image, caption="전처리된 이미지", use_container_width=True)

        # OCR 수행 (한글+영어)
        text = pytesseract.image_to_string(processed_image, lang="eng+kor")
        extracted_texts.append(text)

    combined_text = "\n".join(extracted_texts)
    st.subheader("📄 OCR로 추출한 텍스트")
    st.text_area("추출된 성분 목록", combined_text, height=200)

    # ===== GPT 호출 =====
    openai.api_key = openai_key
    gpt_prompt = f"""아래 성분들을 포함한 약을 동시에 복용할 경우의 주의사항이나 상호작용 가능성이 있다면 알려줘. 

{combined_text}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 약학 전문가입니다."},
                {"role": "user", "content": gpt_prompt}
            ],
            temperature=0.7
        )
        result = response.choices[0].message.content
        st.subheader("🤖 GPT 분석 결과")
        st.write(result)

    except Exception as e:
        st.error(f"GPT 호출 중 오류 발생: {e}")

    # ===== 공공 API로 성분 설명 =====
    def get_drug_info(item_name, api_key):
        try:
            encoded_name = urllib.parse.quote(item_name)
            url = (
                f"https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
                f"?serviceKey={api_key}&itemName={encoded_name}&type=json"
            )
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if 'body' in data['response'] and 'items' in data['response']['body']:
                item = data['response']['body']['items'][0]
                return f"**효능**: {item.get('efcyQesitm', '정보 없음')}\n\n**복용법**: {item.get('useMethodQesitm', '정보 없음')}"
            else:
                return f"`{item_name}`에 대한 정보를 찾을 수 없습니다."
        except Exception as e:
            return f"❗ API 호출 오류: {e}"

    st.subheader("📚 의약품 성분 설명 (공공 데이터)")
    if drug_api_key:
        for line in combined_text.splitlines():
            line = line.strip()
            if line and len(line) < 40:
                with st.expander(f"🔎 {line}"):
                    st.markdown(get_drug_info(line, drug_api_key))
    else:
        st.warning("📌 공공데이터 API 키가 입력되지 않았습니다.")
else:
    st.info("👈 API 키를 입력하고 이미지를 업로드하면 결과가 표시됩니다.")
