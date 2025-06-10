import streamlit as st
from PIL import Image
import pytesseract
from openai import OpenAI

# Tesseract 경로 설정 (Streamlit Cloud 환경이라면 무시해도 됨)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# 사이드바에서 API 키 입력
st.sidebar.title("🔐 API 키 입력")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")

# 제목
st.title("💊 약사봇: 복용 주의 도우미")
st.markdown("복용 중인 약 사진을 **여러 개 업로드**하면, GPT가 함께 먹어도 되는지 알려드려요.")

# 이미지 업로드
uploaded_files = st.file_uploader("약 사진을 업로드하세요 (여러 장 가능)", accept_multiple_files=True, type=["png", "jpg", "jpeg"])

# 약 성분 추출 함수 (OCR)
def extract_text_from_image(image):
    img = Image.open(image)
    text = pytesseract.image_to_string(img, lang='eng+kor')
    return text.strip()

# GPT 응답 생성
def ask_gpt(prompt, api_key):
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❗ GPT 호출 오류: {e}"

# 처리
if openai_key and uploaded_files:
    st.info("🔍 약 성분을 분석 중입니다...")
    all_texts = []
    for file in uploaded_files:
        text = extract_text_from_image(file)
        all_texts.append(text)

    combined_text = "\n\n".join(all_texts)
    st.subheader("📄 OCR 추출된 약 성분 정보")
    st.text(combined_text)

    # GPT 프롬프트
    gpt_prompt = (
        "아래 약 성분들을 기반으로, 이 약들을 함께 복용할 때 주의할 점이나 함께 복용하면 안 되는 경우를 알려줘.\n\n"
        f"{combined_text}"
    )

    st.subheader("🤖 GPT 분석 결과")
    result = ask_gpt(gpt_prompt, openai_key)
    st.write(result)
else:
    st.warning("📥 먼저 OpenAI API 키를 입력하고 약 사진을 업로드하세요.")
