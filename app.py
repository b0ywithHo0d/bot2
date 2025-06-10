import streamlit as st
from PIL import Image
import pytesseract
import openai

# Tesseract 경로 (Streamlit Cloud용)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# --- 사이드바 ---
st.sidebar.title("🔐 API 키 입력")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")

# --- 제목 및 설명 ---
st.title("💊 다약제 복용 주의점 안내")
st.write("여러 약 사진을 업로드하면, 함께 복용 시 주의사항을 GPT가 알려드립니다.")

# --- 파일 업로드 (여러 개 허용) ---
uploaded_files = st.file_uploader("약 사진을 업로드하세요 (여러 개 가능)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if uploaded_files and openai_key:
    openai.api_key = openai_key
    extracted_names = []

    for i, uploaded_file in enumerate(uploaded_files):
        image = Image.open(uploaded_file)
        st.image(image, caption=f"업로드된 이미지 {i+1}", use_container_width=True)

        # OCR 처리
        text = pytesseract.image_to_string(image, lang="eng+kor")
        st.text_area(f"OCR 결과 {i+1}", text, height=100)

        # 약 이름 추출 (가장 유의미한 단어 1개 또는 첫 줄)
        first_line = text.strip().split('\n')[0]
        drug_name = first_line.split()[0] if first_line else f"약{i+1}"
        extracted_names.append(drug_name)

    # GPT 호출
    if extracted_names:
        joined_drugs = ", ".join(extracted_names)
        st.subheader("🤖 GPT 복용 주의사항 안내")
        prompt = (
            f"다음 약들을 함께 복용하려고 합니다: {joined_drugs}. "
            "이 약들을 함께 복용할 때 주의할 점이나 상호작용, 부작용 가능성이 있다면 알려주세요. "
            "의학 전문가처럼 간단하고 정확하게 설명해 주세요."
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            st.write(response.choices[0].message.content)
        except Exception as e:
            st.error(f"GPT 호출 중 오류 발생:\n{e}")
else:
    st.info("📌 먼저 약 사진 여러 장을 업로드하고 OpenAI API 키를 입력하세요.")
