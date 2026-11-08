import streamlit as st
from services.persistence.exercise_repository import get_or_create_user

def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True
    st.title("🏋️‍♂️ AI Real-time GYM Trainer")
    st.markdown("### Welcome! Please enter a username to start.")
    with st.form("login_form",clear_on_submit=False):
        username = st.text_input("Name (unique)", placeholder="unique name e.g. Atharv")
        submit_button = st.form_submit_button("Start Session", width="stretch")
    if submit_button:
        if not username:
            st.error("Name cannot be empty.")
            return False
        #Saving the login session
        user = get_or_create_user(username)
        st.session_state["username"] = username
        st.session_state["user_id"] = user["id"]
        st.rerun()#tells Streamlit to immediately rerun the application script.
    return False