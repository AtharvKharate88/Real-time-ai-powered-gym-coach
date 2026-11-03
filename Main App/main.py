import streamlit as st
import os
import time
from services.auth.login_wall import render_login_wall
from services.state.session_default import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.ui.style_loader import (
    load_css,
    inject_local_font,
    inject_webrtc_styles,
)
import pandas as pd
from dotenv import load_dotenv
from services.vision.excercise_video_processor import VideoProcessorClass
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio
from groq import Groq


@st.fragment(run_every=0.25)
def render_progress_sidebar():
    st.divider()
    st.subheader("Progress")
    exercise = st.session_state.get("exercise_type")
    st.metric("Total Reps", f"{st.session_state.get('reps')}")
    st.metric(
        "Current Set Reps",
        f"{st.session_state.get('current_set_reps')} / "
        f"{st.session_state.get('reps_per_set')}",
    )
    st.metric(
        "Sets Completed",
        f"{st.session_state.get('sets_completed')} / "
        f"{st.session_state.get('target_sets')}",
    )
    st.divider()
    if exercise == "Squats":
        st.subheader("Squat Metrics")
        st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
        st.metric("Back Angle", f"{st.session_state.back_angle}°")
        st.metric("Depth Status", st.session_state.depth_status)
    elif exercise == "Push-ups":
        st.subheader("Push-up Metrics")
        st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
        st.metric("Body Alignment", st.session_state.body_alignment)
        st.metric("Hip Position", st.session_state.hip_status)
    elif exercise == "Biceps Curls (Dumbbell)":
        st.subheader("Curl Metrics")
        st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
        st.metric("Shoulder Stability", st.session_state.shoulder_status)
        st.metric("Swing Detection", st.session_state.swing_status)
    elif exercise == "Shoulder Press":
        st.subheader("Shoulder Press Metrics")
        st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
        st.metric("Arm Extension", st.session_state.extension_status)
        st.metric("Back Arch", st.session_state.back_arch_status)
    elif exercise == "Lunges":
        st.subheader("Lunge Metrics")
        st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
        st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
        st.metric("Balance Status", st.session_state.balance_status)


def render_voice_updates():
    pipeline = st.session_state.get("voice_pipeline")
    if not pipeline:
        return
    result = pipeline.get_result()
    if result:
        st.session_state.audio_to_play, st.session_state.coach_feedback = result
    voice_error = pipeline.get_error()
    if voice_error:
        st.warning(f"Voice coaching error: {voice_error}")
    if st.session_state.get("audio_to_play"):
        autoplay_audio(st.session_state.audio_to_play)
        st.session_state.audio_to_play = None
    if st.session_state.get("coach_feedback"):
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")


def render_live_workout():
    ice_servers = [
        {
            "urls": [
                "stun:stun.l.google.com:19302",
                "stun:stun1.l.google.com:19302",
                "stun:stun.cloudflare.com:3478",
            ]
        }
    ]
    turn_url = os.environ.get("TURN_URL")
    turn_username = os.environ.get("TURN_USERNAME")
    turn_credential = os.environ.get("TURN_CREDENTIAL")
    if turn_url and turn_username and turn_credential:
        ice_servers.append(
            {
                "urls": [turn_url],
                "username": turn_username,
                "credential": turn_credential,
            }
        )

    context = webrtc_streamer(
        key="exercise-analysis",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=VideoProcessorClass,
        rtc_configuration={"iceServers": ice_servers},
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )
    st.session_state.live_context = context


@st.fragment(run_every=0.25)
def render_live_updates():
    context = st.session_state.get("live_context")
    sync_metrics_update(context)
    render_voice_updates()


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",#Initial sidebar visibility
        layout="centered"
    )
    load_css(os.path.join(os.getcwd(),"static","style.css"))
    inject_local_font(os.path.join(os.getcwd(),"static","Adobeclean.otf"),"AdobeClean")
    if not render_login_wall():
        return 
    initial_session_defaults()
    #voice pipeline
    if "voice_pipeline" not in st.session_state:
        try:
            api_key = os.environ.get("GROQ_API_KEY", "")

            if not api_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]
            
            groq_client = Groq(api_key=api_key)
            llm_coach = LLMCoach(groq_client)
            tts = TextToSpeech()
            st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
        except Exception as e:
            st.session_state.voice_pipeline = None
            st.warning(f"Voice coaching is unavailable: {e}")

    # Read workout status
    workout_started=st.session_state.get("workout_started",False)
    #.get() retrieves the value of workout_started.
    with st.sidebar:
        st.title("🏋️‍♂️ AI Coach")
        if(st.session_state.username):
            st.caption(f"👤 Login as {st.session_state.username}")
            st.divider()
            st.subheader("Workout Plan")
        if not workout_started:
            plan_exercise = st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")

            plan_sets = st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)

            plan_reps = st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)

            st.markdown("")
            start_session_button = st.button("Start Session", width="stretch", key="start_session_button")
            if start_session_button:
                st.session_state.exercise_type = plan_exercise
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.reps = 0
                st.session_state.workout_started = True
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0
                if st.session_state.voice_pipeline:
                    st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=plan_exercise,
                        metrics={}
                    )

                
                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                st.rerun()
        else:
            exercise = st.session_state.get("plan_exercise")
            sets = st.session_state.get("plan_sets")
            reps = st.session_state.get("plan_reps")

            st.info(f"**{exercise}** -- {sets} Sets / {reps} Reps")
            end_session_button=st.button("End Session",key="end_session_button")
            if(end_session_button):
                st.session_state["workout_started"]=False
                st.rerun()
        if workout_started:
            render_progress_sidebar()
    st.title("AI Real-time GYM Coach")
    st.markdown("#### Real-time pose detection with proactive AI voice coaching")            
    if not workout_started:
        render_voice_updates()
        st.markdown(
            """
            <div style="
                border: 10px dashed #444;
                border-radius: 0px;
                padding: 48px 32px;
                text-align: center;
                color: #888;
                margin-top: 32px;
            ">
                <h2 style="color:#ccc; margin-bottom:8px;">👈 Set your workout plan</h2>
                <p style="font-size:1.05rem;">
                    Choose your exercise, sets and reps in the sidebar,<br>
                    then click <strong>Start Workout</strong> to activate the camera and AI coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_live_workout()
        render_live_updates()
    st.divider()
    st.markdown("#### Workout History")
    user_id=st.session_state.get("user_id",0)
    if(isinstance(user_id,int)):
        history_rows=get_users_exercises(user_id)
        arr=[
            {
                "Exercise":row['exercise_name'],
                "Reps":row['reps'],
                "Sets":row['sets'],
                "Time(sec)":row['time'],
                "Date":row['created_at']
            }
            for row in history_rows
        ]
        df=pd.DataFrame(arr)
        if not df.empty:
            df["Date"]=pd.to_datetime(df["Date"]).dt.date
            agg_df=df.groupby(["Exercise","Date"]).agg({
                "Reps":'sum',
                "Sets":"sum",
                "Time(sec)":"sum",
            }).reset_index()
            agg_df.index+=1
            st.table(agg_df,border="horizontal")
        else:
            st.info("No workout history found")    
    inject_webrtc_styles()
if __name__ == "__main__":
    main()