import streamlit as st

def read_readme(file_path="README.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading README.md: {e}"

st.title("KOMpass README Viewer")
readme_content = read_readme()
st.markdown(readme_content)