import streamlit as st
import google.generativeai as genai

# 1. API 키 설정
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("Gemini API 키가 설정되지 않았습니다. 관리자에게 문의하세요.")
    st.stop()

# 2. 화면 UI 및 인물 선택
st.title("📖 '동백꽃' 인물과의 인터뷰")
st.caption("작가: 김유정")
character = st.selectbox("대화할 인물을 선택하세요:", ["점순이", "나(주인공)"])

# 3. 세션 상태 초기화 (인물이 바뀌면 대화도 초기화)
if "messages" not in st.session_state or st.session_state.get("current_character") != character:
    st.session_state.messages = []
    st.session_state.question_count = 5
    st.session_state.current_character = character
    
    # 최신 1.5 Flash 모델 적용 및 인물 설정(System Instruction) 부여
    system_instruction = f"너는 김유정의 소설 '동백꽃'의 '{character}'야. 독자의 질문에 소설 속 인물의 성격과 말투로 대답해. 가끔은 능청스럽게 거짓말도 섞어봐."
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
    
    # 이전 대화를 기억하는 진짜 챗 세션 시작
    st.session_state.chat_session = model.start_chat(history=[])

st.write(f"**남은 질문: {st.session_state.question_count}회**")
st.info("인물에게 궁금한 점을 질문해보세요! 총 5회의 기회가 주어지며, 인물이 거짓말을 섞어 말할 수도 있으니 주의 깊게 들어보세요.")

# 기존 대화 내용 화면에 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 사용자 입력 및 제미나이 응답 처리
if prompt := st.chat_input("인물에게 궁금한 점을 물어보세요..."):
    if st.session_state.question_count <= 0:
        st.warning("더 이상 질문할 수 없습니다. 5회의 기회를 모두 사용하셨습니다.")
    else:
        # 사용자 질문 저장 및 출력
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 남은 횟수 1회 차감
        st.session_state.question_count -= 1

        # API 호출 및 응답 출력 (chat_session 사용)
        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"답변 생성 중 오류가 발생했습니다: {e}")
