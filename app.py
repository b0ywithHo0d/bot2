import streamlit as st
from PIL import Image
import requests
import openai
import urllib.parse
import json
import os
import io

# ===== 인증 처리 (Google Cloud Vision) =====
from google.cloud import vision
from google.oauth2 import service_account

if "google_cloud" in st.secrets:
    google_creds = dict(st.secrets["google_cloud"])
    google_creds["private_key"] = google_creds["private_key"].replace("\\\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(google_creds)
    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
else:
    st.warning("Google Cloud Vision API 인증 정보가 설정되어 있지 않습니다.")
    vision_client = None  # 오류 방지용

# ===== 사이드바 - API 키 입력 =====
st.sidebar.title("🔐 API 키 입력")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
drug_api_key = st.sidebar.text_input("공공데이터 API Key", type="password")

# ===== 이미지 업로드 =====
st.title("💊 약 성분 분석 및 병용 주의")
uploaded_images = st.file_uploader("약 사진 여러 장을 업로드하세요", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_images and openai_key and vision_client:
    extracted_texts = []

    for uploaded_file in uploaded_images:
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드한 이미지", use_container_width=True)

        # Vision API로 텍스트 추출
        content = uploaded_file.read()
        image_bytes = vision.Image(content=content)
        response = vision_client.text_detection(image=image_bytes)
        texts = response.text_annotations

        if texts:
            text = texts[0].description
            extracted_texts.append(text)
        else:
            extracted_texts.append("(텍스트 인식 실패)")

    combined_text = "\n".join(extracted_texts)
    st.subheader("📄 추출된 텍스트")
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

            if 'body' in data.get('response', {}) and 'items' in data['response']['body']:
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
