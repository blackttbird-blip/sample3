import streamlit as st
import google.generativeai as genai

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("Gemini API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
    st.stop()

st.title("📖 '동백꽃' 인물과의 인터뷰")
st.caption("작가: 김유정")
character = st.selectbox("대화할 인물을 선택하세요:", ["점순이", "나(주인공)"])

# 인물이 바뀔 때마다 세션(캐시) 강제 초기화
if "messages" not in st.session_state or st.session_state.get("current_character") != character:
    st.session_state.messages = []
    st.session_state.question_count = 5
    st.session_state.current_character = character
    
    # 구버전 환경에서도 무조건 작동하는 gemini-pro 모델 사용
    model = genai.GenerativeModel('gemini-pro')
    
    # 시스템 프롬프트(system_instruction) 기능이 없는 서버에서도 
    # 역할극이 완벽히 되도록 대화 기록(history)의 첫 내용으로 설정 강제 주입
    setup_prompt = f"지금부터 너는 김유정의 소설 '동백꽃'의 '{character}'야. 독자의 질문에 소설 속 인물의 성격과 말투로 대답해. 가끔은 능청스럽게 거짓말도 섞어봐. 알겠지?"
    
    st.session_state.chat_session = model.start_chat(history=[
        {"role": "user", "parts": [setup_prompt]},
        {"role": "model", "parts": ["네, 알겠습니다. 지금부터 소설 속 인물이 되어 답변하겠습니다."]}
    ])

st.write(f"**남은 질문: {st.session_state.question_count}회**")
st.info("인물에게 궁금한 점을 질문해보세요! 총 5회의 기회가 주어지며, 인물이 거짓말을 섞어 말할 수도 있으니 주의 깊게 들어보세요.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("인물에게 궁금한 점을 물어보세요..."):
    if st.session_state.question_count <= 0:
        st.warning("더 이상 질문할 수 없습니다. 5회의 기회를 모두 사용하셨습니다.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.question_count -= 1

        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"답변 생성 중 오류가 발생했습니다: {e}")
