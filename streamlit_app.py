import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="SearchSift", page_icon="🔍", layout="wide")

# Load credentials from secrets
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]
SERPER_API_KEY = st.secrets["serper"]["api_key"]

@st.cache_data(ttl=3600)
def serper_search(query, num_results, start_date, end_date):
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": num_results,
        "tbs": f"cdr:1,cd_min:{start_date},cd_max:{end_date}"
    }
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def login():
    st.title("Login to SearchSift")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            if username == USERNAME and password == PASSWORD:
                st.session_state["logged_in"] = True
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        login()
    else:
        st.title("SearchSift: Advanced Search App")

        st.sidebar.header("Search Parameters")
        search_query = st.sidebar.text_input("Enter search term")
        num_results = st.sidebar.slider("Number of results", 5, 50, 15)
        start_date = st.sidebar.date_input("Start date", datetime.now() - timedelta(days=30))
        end_date = st.sidebar.date_input("End date", datetime.now())

        search_button = st.sidebar.button("Search")

        if search_button and search_query:
            with st.spinner("Searching..."):
                formatted_start_date = start_date.strftime("%Y-%m-%d")
                formatted_end_date = end_date.strftime("%Y-%m-%d")

                serper_results = serper_search(search_query, num_results, formatted_start_date, formatted_end_date)

                st.subheader("Search Results")
                if isinstance(serper_results, dict) and "organic" in serper_results:
                    for i, result in enumerate(serper_results["organic"][:num_results]):
                        col1, col2 = st.columns([0.1, 0.9])
                        with col1:
                            st.checkbox(f"Select {i+1}", key=f"checkbox_{i}")
                        with col2:
                            st.write(f"**{result['title']}**")
                            st.write(result['snippet'])
                            st.write(f"[Link]({result['link']})")
                            st.write("---")
                else:
                    st.warning("No organic results found in Serper search.")

            if st.button("Process Selected Results"):
                selected_results = [
                    result for i, result in enumerate(serper_results["organic"][:num_results])
                    if st.session_state[f"checkbox_{i}"]
                ]
                st.subheader("Selected Results for Further Processing")
                for result in selected_results:
                    st.write(f"**{result['title']}**")
                    st.write(result['snippet'])
                    st.write(f"[Link]({result['link']})")
                    st.write("---")
                
                # Here you can add further processing steps for the selected results

if __name__ == "__main__":
    main()
