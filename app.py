# app.py

import streamlit as st
import datetime
import json
import os
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
예시 형식:
{{
  "goal": "블로그 글 작성",
  "deadline": "2025-05-13T19:00:00"
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

# --- 사용자 입력 ---
st.title("🧠 하루 목표 리마인더")
user_input = st.text_input("오늘의 목표를 입력하세요 (예: 오후 6시까지 보고서 작성)")

if st.button("✅ 목표 등록"):
    if user_input:
        result = parse_goal_with_gemini(user_input)
        if result:
            try:
                deadline_dt = datetime.datetime.fromisoformat(result["deadline"])
                st.session_state.goals.append({
                    "goal": result["goal"],
                    "deadline": deadline_dt,
                    "created": datetime.datetime.now(),
                    "done": False
                })
                st.success(f"목표 등록: {result['goal']} (마감: {deadline_dt.strftime('%H:%M')})")
            except Exception as e:
                st.error("마감 시간 형식이 잘못됐어요: " + str(e))

# --- 목표 목록 표시 ---
st.subheader("📋 오늘의 목표 목록")
now = datetime.datetime.now()

if st.session_state.goals:
    sorted_goals = sorted(st.session_state.goals, key=lambda x: x["deadline"])
    for i, goal in enumerate(sorted_goals):
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            status = "✅ 완료" if goal["done"] else "🕒 진행 중"
            st.write(f"**{goal['goal']}** ({goal['deadline'].strftime('%H:%M')}) - {status}")
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
