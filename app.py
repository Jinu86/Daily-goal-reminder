# app.py

import streamlit as st
import datetime
import json
import os
import dateparser
import pytz
from dotenv import load_dotenv
import google.generativeai as genai

# --- 환경 변수 불러오기 (로컬과 Streamlit Cloud 모두 지원) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# Streamlit Secrets에서도 API 키 확인 (Streamlit Cloud 배포용)
if not API_KEY and 'GOOGLE_API_KEY' in st.secrets:
    API_KEY = st.secrets['GOOGLE_API_KEY']

# API 키 확인
if not API_KEY:
    st.error("❌ API 키가 설정되지 않았습니다. .env 파일이나 Streamlit Secrets를 확인하세요.")
    st.stop()

# Google Gemini API 설정
genai.configure(api_key=API_KEY)

# 모델 초기화
model = genai.GenerativeModel("models/gemini-1.5-flash")  # 모델명 업데이트됨

# --- 목표 목록 초기화 ---
if "goals" not in st.session_state:
    st.session_state.goals = []

# --- Gemini에 보낼 프롬프트 함수 ---
def parse_goal_with_gemini(user_input):
    prompt = f"""
다음 문장에서 '목표'와 '마감시간'을 추출해서 JSON으로 반환해줘.
형식은 다음과 같아야 해:
{{
  "goal": "목표 내용",
  "deadline": "자연어 시간 표현" (예: "오늘 오후 9시", "내일 오전 10시")
}}

입력: {user_input}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # JSON 파싱
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        json_str = text[json_start:json_end]
        return json.loads(json_str)
    except Exception as e:
        st.error("목표 분석 중 오류 발생: " + str(e))
        return None

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# --- 사용자 입력 ---
st.title("🧠 하루 목표 리마인더")
user_input = st.text_input("오늘의 목표를 입력하세요 (예: 오후 6시까지 보고서 작성)")

if st.button("✅ 목표 등록"):
    if user_input:
        result = parse_goal_with_gemini(user_input)
        if result:
            # 자연어 시간을 간단한 설정으로 파싱
            parsed_time = dateparser.parse(
                result["deadline"], 
                settings={
                    "PREFER_DATES_FROM": "future",
                    "TIMEZONE": "Asia/Seoul",
                    "RETURN_AS_TIMEZONE_AWARE": True,
                    "PREFER_DAY_OF_MONTH": "first",
                    "LANGUAGES": ["ko"]
                }
            )
            
            if parsed_time:
                # 현재 시간 설정
                now = datetime.datetime.now(KST)
                
                # 세션 상태에 저장
                st.session_state.goals.append({
                    "goal": result["goal"],
                    "deadline": parsed_time,
                    "created": now,
                    "done": False
                })
                
                # 날짜가 오늘이면 시간만, 아니면 날짜와 시간 표시
                today = now.date()
                if parsed_time.date() == today:
                    time_str = parsed_time.strftime('%H:%M')
                else:
                    time_str = parsed_time.strftime('%Y-%m-%d %H:%M')
                
                st.success(f"목표 등록: {result['goal']} (마감: {time_str})")
            else:
                # dateparser로 파싱 실패 시 수동으로 시간 추정
                st.warning("시간 형식을 자동으로 인식하지 못했습니다. 현재 시간에서 1시간 후로 설정합니다.")
                
                # 현재 시간 + 1시간으로 설정
                default_time = datetime.datetime.now(KST) + datetime.timedelta(hours=1)
                
                # 세션 상태에 저장
                st.session_state.goals.append({
                    "goal": result["goal"],
                    "deadline": default_time,
                    "created": datetime.datetime.now(KST),
                    "done": False
                })
                
                st.success(f"목표 등록: {result['goal']} (마감: {default_time.strftime('%H:%M')})")
                st.info("다음에는 '오늘 오후 3시', '내일 아침 9시'와 같이 시간을 명확히 입력해주세요.")

# --- 목표 목록 표시 ---
st.subheader("📋 오늘의 목표 목록")
now = datetime.datetime.now(KST)

if st.session_state.goals:
    sorted_goals = sorted(st.session_state.goals, key=lambda x: x["deadline"])
    for i, goal in enumerate(sorted_goals):
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            status = "✅ 완료" if goal["done"] else "🕒 진행 중"
            
            # 날짜가 오늘이면 시간만, 아니면 날짜와 시간 표시
            deadline = goal["deadline"]
            if isinstance(deadline, datetime.datetime):
                today = now.date()
                if deadline.date() == today:
                    time_str = deadline.strftime('%H:%M')
                else:
                    time_str = deadline.strftime('%m월 %d일 %H:%M')
            else:
                time_str = str(deadline)
                
            st.write(f"**{goal['goal']}** ({time_str}) - {status}")
        with col2:
            if not goal["done"] and now >= goal["deadline"]:
                st.warning("⏰ 마감 시간이 지났어요!")
        with col3:
            if st.button("✔️", key=f"done_{i}"):
                st.session_state.goals[i]["done"] = True
else:
    st.info("오늘의 목표를 입력해주세요!")

# --- 전체 리셋 버튼 ---
if st.button("🗑 전체 삭제"):
    st.session_state.goals.clear()
    st.success("모든 목표를 삭제했어요!")
