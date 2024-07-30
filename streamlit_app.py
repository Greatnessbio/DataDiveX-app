import streamlit as st
import requests
from datetime import datetime, timedelta
import json

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
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error occurred while fetching results: {str(e)}")
        return None

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
                if serper_results:
                    if "organic" in serper_results and serper_results["organic"]:
                        for i, result in enumerate(serper_results["organic"][:num_results]):
                            col1, col2 = st.columns([0.1, 0.9])
                            with col1:
                                st.checkbox(f"Select {i+1}", key=f"checkbox_{i}")
                            with col2:
                                st.write(f"**{result['title']}**")
                                st.write(result.get('snippet', 'No snippet available'))
                                st.write(f"[Link]({result['link']})")
                                st.write("---")
                    else:
                        st.warning("No organic results found in Serper search.")
                    
                    # Debug information
                    st.subheader("Debug Information")
                    st.json(serper_results)
                else:
                    st.error("Failed to fetch search results. Please check your API key and try again.")

            if st.button("Process Selected Results"):
                if serper_results and "organic" in serper_results:
                    selected_results = [
                        result for i, result in enumerate(serper_results["organic"][:num_results])
                        if st.session_state.get(f"checkbox_{i}", False)
                    ]
                    st.subheader("Selected Results for Further Processing")
                    if selected_results:
                        for result in selected_results:
                            st.write(f"**{result['title']}**")
                            st.write(result.get('snippet', 'No snippet available'))
                            st.write(f"[Link]({result['link']})")
                            st.write("---")
                    else:
                        st.warning("No results selected. Please select at least one result to process.")
                else:
                    st.warning("No results available to process. Please perform a search first.")

if __name__ == "__main__":
    main()
