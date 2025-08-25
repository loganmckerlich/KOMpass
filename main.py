import streamlit as st
from strava_connect import get_athlete

def read_readme(file_path="README.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading README.md: {e}"

st.title("KOMpass README Viewer")
readme_content = read_readme()
st.markdown(readme_content)

# Strava Athlete Info Section
st.header("Strava Athlete Information")
try:
    athlete = get_athlete()
    st.write(f"**Name:** {athlete.get('firstname')} {athlete.get('lastname')}")
    st.write(f"**Username:** {athlete.get('username')}")
    st.write(f"**Country:** {athlete.get('country')}")
    st.write(f"**Sex:** {athlete.get('sex')}")
    st.write(f"**Profile:** {athlete.get('profile')}")
except Exception as e:
    st.error(f"Error fetching athlete info: {e}")