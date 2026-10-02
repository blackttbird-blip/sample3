import streamlit as st
import google.generativeai as genai

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("Gemini API 키가 설정되지 않았습니다.")
    st.stop()

st.title("📖 '동백꽃' 역할극 챗봇")

# 사이드바에서 교사/학생 모드 선택
mode = st.sidebar.radio("모드를 선택하세요:", ["학생 화면", "교사 관리 화면"])

if mode == "교사 관리 화면":
    st.subheader("👨‍🏫 교사 설정 및 자료 업로드")
    password = st.text_input("교사 비밀번호를 입력하세요:", type="password")
    
    if password == "1234": # 원하는 비밀번호로 수정해서 사용해!
        st.success("관리자 모드에 접속되었습니다.")
        st.info("이곳에 소설 본문이나 참고할 만한 학습 자료를 업로드하는 창을 추가할 수 있어.")
        # 추가적인 프롬프트 설정이나 자료 업로드 코드 작성 위치
    elif password:
        st.error("비밀번호가 일치하지 않습니다.")

else:
    st.subheader("💬 인물과 대화하기")
    character = st.selectbox("대화할 인물을 선택하세요:", ["점순이", "나(주인공)"])
    
    if "messages" not in st.session_state or st.session_state.get("current_character") != character:
        st.session_state.messages = []
        st.session_state.current_character = character
        
        # 모델 및 시스템 설정 (버전 충돌을 피하기 위해 가장 기본 형태 사용)
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.session_state.chat_session = model.start_chat(history=[])
        
        # 역할 부여 프롬프트 강제 주입
        setup_prompt = f"너는 김유정의 소설 '동백꽃'의 '{character}'야. 독자의 질문에 소설 속 인물의 성격과 말투로 대답해."
        st.session_state.chat_session.send_message(setup_prompt)

    # 기존 대화 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 채팅 입력
    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")
