import streamlit as st
import json
import os
import random
import re
import html
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# ==================================================
# 1. 기본 설정
# ==================================================

load_dotenv()

st.set_page_config(
    page_title="AI 문학 인터뷰",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "works.json"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "6460")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

st.markdown("""
<style>
.stApp {
    background-color: #F7F8FA;
}
.block-container {
    max-width: 1000px;
    padding-top: 2rem;
}
.chat-question {
    background: #E8F0FE;
    padding: 18px;
    border-radius: 15px;
    margin: 12px 0;
    color: #222;
}
.chat-answer {
    background: white;
    border: 1px solid #E5E7EB;
    padding: 18px;
    border-radius: 15px;
    margin: 12px 0 22px 0;
    color: #222;
}
.result-card {
    background: white;
    border: 1px solid #DDD;
    padding: 22px;
    border-radius: 15px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)


# ==================================================
# 2. 데이터 관리
# ==================================================

def load_works():
    if not DATA_FILE.exists():
        return {}

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_works(works):
    DATA_FILE.write_text(
        json.dumps(works, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            ".env 파일을 확인해 주세요."
        )

    return OpenAI(api_key=api_key)


def ask_ai(instructions, question):
    client = get_client()

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=instructions,
        input=question
    )

    answer = response.output_text.strip()

    if not answer:
        raise ValueError("AI가 빈 답변을 반환했습니다.")

    return answer


# ==================================================
# 3. 세션 상태 관리
# ==================================================

def initialize_session():

    defaults = {
        "page": "student",
        "admin_ok": False,
        "work_id": None,
        "character": None,
        "current_turn": 0,
        "total_turns": 5,
        "mistake_turn": None,
        "mistake_used": False,
        "messages": [],
        "finished": False
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()


def start_interview(work_id, character):

    st.session_state.work_id = work_id
    st.session_state.character = character

    st.session_state.current_turn = 0
    st.session_state.total_turns = 5

    # 오답 위치를 무작위로 한 번 선정
    st.session_state.mistake_turn = random.randint(1, 5)

    st.session_state.mistake_used = False
    st.session_state.messages = []
    st.session_state.finished = False


# ==================================================
# 4. AI 기본 프롬프트
# ==================================================

def make_normal_prompt(work, character):

    return f"""
너는 소설 속 등장인물 {character['name']}이다.

학생과 대화할 때 반드시 등장인물의 입장에서 답변한다.
소설 해설자처럼 설명하지 않는다.

[작품 정보]

제목: {work['title']}
작가: {work.get('author', '')}

[등장인물 정보]

이름: {character['name']}
성격: {character.get('personality', '')}
말투: {character.get('speech', '')}
특징: {character.get('traits', '')}

[소설 본문]

{work.get('text', '')}

[참고 학습 자료]

{work.get('reference', '')}

[답변 원칙]

1. 소설 본문을 가장 중요한 근거로 사용한다.
2. 참고 학습 자료는 두 번째 근거로 사용한다.
3. 본문에 없는 사실을 만들어내지 않는다.
4. 본문과 일반 상식이 충돌하면 본문을 따른다.
5. 작품에서 확인할 수 없는 내용은 확정적으로 말하지 않는다.
6. 등장인물의 관점에서 자연스럽게 답한다.
7. 중학생이 이해할 수 있는 쉬운 한국어를 사용한다.
8. 답변은 기본적으로 2~5문장으로 작성한다.
9. 학생에게 정답이나 교사의 해설을 직접 알려주지 않는다.
10. 욕설, 비속어, 성적 표현, 혐오 표현을 사용하지 않는다.
11. 작품과 관계없는 질문에는 자연스럽게 대응하고 작품으로 돌아온다.
12. 질문이 지나치게 짧으면 자연스럽게 추가 질문을 유도한다.

반드시 등장인물의 말투와 성격을 유지하라.
"""


# ==================================================
# 5. 의도된 오답 생성 프롬프트
# ==================================================

def make_mistake_prompt(work, character, history):

    return f"""
너는 소설 속 등장인물 {character['name']}이다.

이번 답변에서는 학생이 발견해야 할
'의도된 문학적 오답'을 정확히 하나 포함해야 한다.

[작품]

제목: {work['title']}

[등장인물]

이름: {character['name']}
성격: {character.get('personality', '')}
말투: {character.get('speech', '')}

[소설 본문]

{work.get('text', '')}

[참고 자료]

{work.get('reference', '')}

[이전 대화]

{json.dumps(history, ensure_ascii=False)}

[오답 생성 규칙]

1. 학생의 질문과 직접 관련된 답변을 작성한다.
2. 등장인물의 관점과 말투를 유지한다.
3. 본문의 사건이나 인물 관계를 활용한다.
4. 답변 중 핵심 사실 하나를 교묘하게 왜곡한다.
5. 원인과 결과를 뒤집을 수 있다.
6. 사건의 선후 관계를 바꿀 수 있다.
7. 인물의 행동 동기를 왜곡할 수 있다.
8. 실제 발언의 의미를 바꿀 수 있다.
9. 다른 인물의 행동을 바꾸어 서술할 수 있다.
10. 본문에 없는 인과관계를 그럴듯하게 삽입할 수 있다.

[금지 사항]

- 황당한 거짓말
- 오타를 이용한 오류
- 작품과 무관한 오류
- 너무 쉽게 발견되는 오류
- 학생에게 오류라고 알려주는 표현
- 오류를 스스로 인정하는 표현

학생이 본문을 꼼꼼하게 읽어야만
반박할 수 있는 수준의 답변을 작성하라.

답변은 2~5문장으로 작성한다.
"""


# ==================================================
# 6. 오답 품질 검수
# ==================================================

def validate_mistake(work, question, answer):

    prompt = f"""
다음 답변이 교육용으로 적절한 의도된 오답인지 검수하라.

[소설 본문]

{work.get('text', '')}

[참고 자료]

{work.get('reference', '')}

[학생 질문]

{question}

[AI 답변]

{answer}

다음 조건을 모두 만족해야 valid=true이다.

1. 학생의 질문과 직접 관련되어야 한다.
2. 답변의 구체적인 내용이 본문과 실제로 충돌해야 한다.
3. 학생이 본문에서 반박할 근거를 찾을 수 있어야 한다.
4. 단순한 표현 차이가 아니어야 한다.
5. 너무 황당하거나 쉽게 발견되는 오류가 아니어야 한다.

반드시 아래 JSON 형식으로만 출력하라.

{{"valid": true, "reason": "검수 이유"}}

또는

{{"valid": false, "reason": "검수 이유"}}
"""

    result = ask_ai(
        "너는 문학 교육용 오답 검수자이다. JSON만 출력하라.",
        prompt
    )

    try:
        result = json.loads(result)
        return result.get("valid") is True
    except Exception:
        return False


# ==================================================
# 7. 답변 생성
# ==================================================

def generate_answer(work, character, question):

    next_turn = st.session_state.current_turn + 1

    is_mistake_turn = (
        next_turn == st.session_state.mistake_turn
        and not st.session_state.mistake_used
    )

    if is_mistake_turn:

        # 최대 5회 재생성 및 검수
        for attempt in range(5):

            answer = ask_ai(
                make_mistake_prompt(
                    work,
                    character,
                    st.session_state.messages
                ),
                question
            )

            valid = validate_mistake(
                work,
                question,
                answer
            )

            if valid:
                st.session_state.mistake_used = True
                return answer

        # 검수에 실패하면 해당 질문을 완료하지 않는다.
        # 같은 회차를 다시 시도할 수 있도록 오류 처리한다.
        raise RuntimeError(
            "본문과 충돌하는 적절한 오답을 검증하지 못했습니다. "
            "다시 질문을 제출해 주세요."
        )

    # 정상 답변
    return ask_ai(
        make_normal_prompt(work, character),
        question
    )


# ==================================================
# 8. 학생 화면
# ==================================================

def student_page():

    works = load_works()

    st.title("📚 AI 문학 인터뷰")
    st.caption("등장인물과 대화하며 소설의 내용을 탐구해 보세요.")

    if not works:
        st.info("등록된 작품이 없습니다. 교사 관리자에서 작품을 등록해 주세요.")
        return

    # 인터뷰 시작 전
    if st.session_state.work_id is None:

        work_id = st.selectbox(
            "소설 선택",
            list(works.keys()),
            format_func=lambda x: works[x]["title"]
        )

        work = works[work_id]

        characters = work.get("characters", [])

        if not characters:
            st.warning("등록된 등장인물이 없습니다.")
            return

        character_name = st.selectbox(
            "등장인물 선택",
            [c["name"] for c in characters]
        )

        character = next(
            c for c in characters
            if c["name"] == character_name
        )

        st.divider()

        st.write("선택한 인물에게 궁금한 것을 질문해 보세요.")
        st.write("총 5번의 질문 기회가 있습니다.")

        if st.button(
            "인터뷰 시작하기",
            type="primary",
            use_container_width=True
        ):

            start_interview(work_id, character)
            st.rerun()

        return

    # 현재 인터뷰 정보
    work = works[st.session_state.work_id]
    character = st.session_state.character

    col1, col2 = st.columns([4, 1])

    with col1:
        st.subheader(work["title"])
        st.caption(f"인터뷰 인물: {character['name']}")

    with col2:
        st.metric(
            "진행 상황",
            f"{st.session_state.current_turn} / 5"
        )

    st.progress(st.session_state.current_turn / 5)

    # 질문 진행 단계
    progress_text = "　".join([
        f"{'●' if i <= st.session_state.current_turn else '○'} {i}"
        for i in range(1, 6)
    ])

    st.markdown(
        f"<div style='text-align:center;font-size:18px;'>"
        f"{progress_text}</div>",
        unsafe_allow_html=True
    )

    st.divider()

    # 이전 대화 출력
    for i, message in enumerate(st.session_state.messages, 1):

        st.markdown(
            f"""
            <div class="chat-question">
            <b>나 · 질문 {i}</b><br><br>
            {html.escape(message['question'])}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div class="chat-answer">
            <b>{html.escape(character['name'])}</b><br><br>
            {html.escape(message['answer'])}
            </div>
            """,
            unsafe_allow_html=True
        )

    # 질문 입력
    if st.session_state.current_turn < 5:

        with st.form("question_form", clear_on_submit=True):

            question = st.text_area(
                "질문 입력",
                placeholder="등장인물에게 한 가지 질문을 해 보세요.",
                height=100,
                max_chars=500,
                label_visibility="collapsed"
            )

            submitted = st.form_submit_button(
                "질문하기",
                type="primary",
                use_container_width=True
            )

        if submitted:

            question = question.strip()

            if not question:
                st.warning("질문을 입력해 주세요.")
                return

            with st.spinner("인물이 답변을 생각하고 있습니다..."):

                try:

                    answer = generate_answer(
                        work,
                        character,
                        question
                    )

                    st.session_state.messages.append({
                        "question": question,
                        "answer": answer
                    })

                    st.session_state.current_turn += 1

                    if st.session_state.current_turn == 5:
                        st.session_state.finished = True

                    st.rerun()

                except Exception as e:
                    st.error(str(e))

    # 5회 완료
    if st.session_state.finished:

        st.success("인터뷰가 끝났습니다!")

        st.write(
            "5개의 답변 중 소설 내용과 맞지 않는 답변을 찾아보세요."
        )

        if st.button(
            "결과 확인하기",
            type="primary",
            use_container_width=True
        ):
            st.session_state.page = "result"
            st.rerun()


# ==================================================
# 9. 결과 화면
# ==================================================

def result_page():

    works = load_works()

    work = works[st.session_state.work_id]
    character = st.session_state.character

    st.title("🎉 인터뷰가 끝났습니다!")

    st.info(
        "5개의 답변 중 소설 내용과 맞지 않는 답변을 찾아보세요. "
        "본문에서 근거를 찾아 왜 잘못되었는지 설명해 보세요."
    )
