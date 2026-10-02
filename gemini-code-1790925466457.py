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
    
    if password == "6460": 
        st.success("관리자 모드에 접속되었습니다.")
        st.info("소설 본문이나 참고할 만한 학습 자료를 업로드해 주세요.")
        
        uploaded_file = st.file_uploader("학습 자료 및 소설 본문 업로드 (PDF, TXT, DOCX)", type=["txt", "pdf", "docx"])
        if uploaded_file is not None:
            st.write("✅ 파일이 성공적으로 업로드되었습니다:", uploaded_file.name)
            
        # 디버깅용: 서버에서 확인된 사용 가능한 모델 리스트 출력
        st.write("---")
        st.write("🔍 **현재 사용 가능한 모델 목록 (자동 감지됨)**")
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write(models)
        except Exception as e:
            st.write("목록을 불러올 수 없습니다.")
            
    elif password:
        st.error("비밀번호가 일치하지 않습니다.")

else:
    st.subheader("💬 인물과 대화하기")
    character = st.selectbox("대화할 인물을 선택하세요:", ["점순이", "나(주인공)"])
    
    if "messages" not in st.session_state or st.session_state.get("current_character") != character:
        st.session_state.messages = []
        st.session_state.current_character = character
        
        # --- 🌟 핵심: 하드코딩된 이름 대신, 사용 가능한 최적의 모델을 자동 탐색 ---
        target_model = 'gemini-1.0-pro' # 최후의 안전망(기본값)
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if available_models:
                target_model = available_models[0] # 첫 번째로 감지된 모델 강제 선택
                # 1.5 flash나 1.0 pro가 목록에 있으면 우선권 부여
                for m in available_models:
                    if 'gemini-1.5-flash' in m:
                        target_model = m
                        break
                    elif 'gemini-1.0-pro' in m:
                        target_model = m
            
            # API 호출 오류 방지를 위해 'models/' 접두사 제거
            target_model = target_model.replace('models/', '')
        except Exception:
            pass # 탐색 실패 시 기본값(gemini-1.0-pro) 유지
        
        # 자동 감지된 모델로 챗봇 엔진 시작
        model = genai.GenerativeModel(target_model)
        st.session_state.chat_session = model.start_chat(history=[])
        
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
