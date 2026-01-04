import streamlit as st
from google import genai
import datetime
import pandas as pd
import json
from ics import Calendar, Event

# ==========================================
# 1. 설정 및 디자인
# ==========================================
st.set_page_config(page_title="AI 루틴 마스터", page_icon="🗓️")

# API 키 설정
try:
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        st.error("🚨 API 키가 없습니다. secrets.toml을 확인해주세요.")
        st.stop()
except:
    st.error("secrets.toml 파일을 찾을 수 없습니다.")
    st.stop()

client = genai.Client(api_key=api_key)

# ==========================================
# 2. [수정] 모델 고정 (Lite 버전 사용)
# ==========================================
def get_fixed_model():
    """
    민정우님 계정에서 확인된 '가장 가볍고 최신인' 모델을 사용합니다.
    (429 리소스 부족 에러 방지용 Lite 모델)
    """
    # 1순위: 가장 추천하는 라이트 모델 별명
    return "models/gemini-flash-lite-latest"

# ==========================================
# 3. AI 로직
# ==========================================
def get_ai_schedule(condition, s_time, e_time, w_rule, we_rule, model_name):
    now = datetime.datetime.now()
    prompt = f"""
    [상황] {now.strftime("%Y-%m-%d %A")}, 컨디션:{condition}, 시간:{s_time}~{e_time}
    [규칙] 평일:{w_rule} / 주말:{we_rule}
    [요청] 위 조건에 맞춰 스케줄 생성.
    **반드시 아래 JSON 형식으로만 응답.**
    ```json
    [
      {{
        "activity": "활동명",
        "start_time": "HH:MM",
        "end_time": "HH:MM",
        "description": "세부내용"
      }}
    ]
    ```
    """
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return response.text
    except Exception as e:
        # 혹시라도 모델 이름 에러가 나면 2순위(2.5 Lite)로 재시도
        print(f"1순위 모델 실패, 2순위 시도: {e}")
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return response.text

def create_ics(schedule_data):
    c = Calendar()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    for item in schedule_data:
        e = Event()
        e.name = f"[루틴] {item['activity']}"
        s = datetime.datetime.strptime(f"{today} {item['start_time']}", "%Y-%m-%d %H:%M")
        e.begin = s.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        e.end = s + datetime.timedelta(hours=1)
        c.events.add(e)
    return c.serialize()

# ==========================================
# 4. 화면 구성
# ==========================================
st.title("🗓️ AI 루틴 마스터")

# 모델 설정
target_model = get_fixed_model()
st.caption(f"🚀 적용된 모델: `{target_model}` (Lite 버전)")

with st.container(border=True):
    c1, c2 = st.columns(2)
    s_time = c1.time_input("시작", datetime.time(18, 0))
    e_time = c2.time_input("종료", datetime.time(23, 0))
    cond = st.text_input("컨디션", "💪 최고!")

with st.expander("규칙 설정"):
    w_rule = st.text_area("평일", "1일 1업로드, 운동 1시간")
    we_rule = st.text_area("주말", "밀린 영상 편집")

if st.button("스케줄 생성 ✨", type="primary"):
    with st.spinner("가볍고 빠른 AI가 스케줄 짜는 중..."):
        try:
            str_s = s_time.strftime("%H:%M")
            str_e = e_time.strftime("%H:%M")
            
            res = get_ai_schedule(cond, str_s, str_e, w_rule, we_rule, target_model)
            data = json.loads(res)
            
            st.info("완료! 아래 리스트를 확인하세요.")
            st.data_editor(pd.DataFrame(data), hide_index=True)
            st.download_button("📅 캘린더 저장", create_ics(data), "schedule.ics")
            
        except Exception as e:
            st.error(f"에러 발생: {e}")
            st.warning("⚠️ 혹시 'Quota' 관련 에러라면 내일 다시 시도해야 합니다.")