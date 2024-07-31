import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json

# Set up page config
st.set_page_config(page_title="TrendSift+", page_icon="🔍", layout="wide")

# Load credentials from secrets
try:
    USERNAME = st.secrets["credentials"]["username"]
    PASSWORD = st.secrets["credentials"]["password"]
    SERPAPI_KEY = st.secrets["serpapi"]["api_key"]
    SERPER_KEY = st.secrets["serper"]["api_key"]
    EXA_API_KEY = st.secrets["exa"]["api_key"]
except KeyError as e:
    st.error(f"Missing secret: {e}. Please check your Streamlit secrets configuration.")
    st.stop()

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = {}
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'selected_results' not in st.session_state:
    st.session_state.selected_results = {}

@st.cache_data(ttl=3600)
def google_trends_search(query, timeframe):
    params = {
        "engine": "google_trends",
        "q": query,
        "date": timeframe,
        "api_key": SERPAPI_KEY
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching Google Trends data: {e}")
        return None

@st.cache_data(ttl=3600)
def serper_search(query, search_type="search"):
    url = f"https://google.serper.dev/{search_type}"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERPER_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Serper: {e}")
        return None

@st.cache_data(ttl=3600)
def exa_search(query, category, start_date, end_date):
    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }
    payload = {
        "query": query,
        "useAutoprompt": True,
        "type": "neural",
        "category": category,
        "numResults": 10,
        "startPublishedDate": start_date,
        "endPublishedDate": end_date
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from Exa: {str(e)}")
        return None

def login():
    st.title("Login to TrendSift+")
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
        st.title("TrendSift+: Multi-Source Research Tool")

        st.sidebar.header("Search Parameters")
        search_query = st.sidebar.text_input("Enter search term")
        
        search_types = ["Google Trends", "Serper Search", "Serper Scholar", "Exa Company", "Exa Research Paper", "Exa News", "Exa Tweet"]
        selected_search_types = st.sidebar.multiselect("Select search types", search_types, default=["Google Trends"])
        
        timeframes = {
            "Past 7 days": "now 7-d",
            "Past 30 days": "today 1-m",
            "Past 90 days": "today 3-m",
            "Past 12 months": "today 12-m",
            "Past 5 years": "today 5-y"
        }
        selected_timeframe = st.sidebar.selectbox("Select time range", list(timeframes.keys()))

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        search_button = st.sidebar.button("Search")

        if search_button and search_query:
            st.session_state.search_results = {}  # Reset search results
            st.session_state.search_performed = True
            
            for search_type in selected_search_types:
                st.subheader(f"Results for {search_type}")
                
                if search_type == "Google Trends":
                    trends_data = google_trends_search(search_query, timeframes[selected_timeframe])
                    if trends_data and "interest_over_time" in trends_data:
                        df = pd.DataFrame(trends_data["interest_over_time"]["timeline_data"])
                        df['date'] = pd.to_datetime(df['date'])
                        df['value'] = df['values'].apply(lambda x: x[0]['value'])
                        fig = px.line(df, x='date', y='value', title=f"Interest over time for '{search_query}'")
                        st.plotly_chart(fig)

                        if "related_topics" in trends_data:
                            st.write("Related Topics:")
                            for topic_type in ["top", "rising"]:
                                if topic_type in trends_data["related_topics"]:
                                    st.write(f"{topic_type.capitalize()}:")
                                    for topic in trends_data["related_topics"][topic_type]:
                                        st.write(f"- {topic['topic']['title']}: {topic['value']}")

                        if "related_queries" in trends_data:
                            st.write("Related Queries:")
                            for query_type in ["top", "rising"]:
                                if query_type in trends_data["related_queries"]:
                                    st.write(f"{query_type.capitalize()}:")
                                    for query in trends_data["related_queries"][query_type]:
                                        st.write(f"- {query['query']}: {query['value']}")
                    else:
                        st.warning("No Google Trends data available for the given query and time range.")
                
                elif search_type == "Serper Search":
                    search_results = serper_search(search_query, "search")
                    if search_results and "organic" in search_results:
                        st.session_state.search_results[search_type] = search_results["organic"]
                        for i, result in enumerate(search_results["organic"]):
                            key = f"serper_search_{i}"
                            st.session_state.selected_results[key] = st.session_state.get(key, False)
                            col1, col2 = st.columns([0.1, 0.9])
                            with col1:
                                st.checkbox("Select", key=key, value=st.session_state.selected_results[key])
                            with col2:
                                st.write(f"**Title:** {result['title']}")
                                st.write(f"**Snippet:** {result['snippet']}")
                                st.write(f"**Link:** [{result['link']}]({result['link']})")
                                if 'position' in result:
                                    st.write(f"**Position:** {result['position']}")
                                if 'date' in result:
                                    st.write(f"**Date:** {result['date']}")
                            st.write("---")
                    else:
                        st.warning("No Serper Search results found.")
                
                elif search_type == "Serper Scholar":
                    scholar_results = serper_search(search_query, "scholar")
                    if scholar_results and "organic" in scholar_results:
                        st.session_state.search_results[search_type] = scholar_results["organic"]
                        for i, result in enumerate(scholar_results["organic"]):
                            key = f"serper_scholar_{i}"
                            st.session_state.selected_results[key] = st.session_state.get(key, False)
                            col1, col2 = st.columns([0.1, 0.9])
                            with col1:
                                st.checkbox("Select", key=key, value=st.session_state.selected_results[key])
                            with col2:
                                st.write(f"**Title:** {result['title']}")
                                st.write(f"**Authors:** {result.get('authors', 'N/A')}")
                                st.write(f"**Publication:** {result.get('publication', 'N/A')}")
                                st.write(f"**Snippet:** {result.get('snippet', 'N/A')}")
                                st.write(f"**Cited By:** {result.get('citedBy', 'N/A')}")
                                st.write(f"**Year:** {result.get('year', 'N/A')}")
                                st.write(f"**Link:** [{result['link']}]({result['link']})")
                            st.write("---")
                    else:
                        st.warning("No Serper Scholar results found.")
                
                elif search_type.startswith("Exa"):
                    category = search_type.split(" ")[-1].lower()
                    exa_results = exa_search(search_query, category, start_date_str, end_date_str)
                    if exa_results and "results" in exa_results:
                        st.session_state.search_results[search_type] = exa_results['results']
                        for i, result in enumerate(exa_results['results']):
                            key = f"exa_{category}_{i}"
                            st.session_state.selected_results[key] = st.session_state.get(key, False)
                            col1, col2 = st.columns([0.1, 0.9])
                            with col1:
                                st.checkbox("Select", key=key, value=st.session_state.selected_results[key])
                            with col2:
                                st.write(f"**Title:** {result.get('title', 'No title')}")
                                st.write(f"**URL:** [{result.get('url', 'No URL')}]({result.get('url', 'No URL')})")
                                st.write(f"**Published Date:** {result.get('publishedDate', 'N/A')}")
                                st.write(f"**Author:** {result.get('author', 'N/A')}")
                                st.write(f"**Text:** {result.get('text', 'No text')[:1000]}...")
                                if 'highlights' in result:
                                    st.write("**Highlights:**")
                                    for highlight in result['highlights']:
                                        st.write(f"- {highlight}")
                            st.write("---")
                    else:
                        st.warning(f"No results found for Exa search in category: {category}")

        # Process selected results
        if st.session_state.search_performed:
            if st.button("Process Selected Results"):
                selected_results = []
                for search_type, results in st.session_state.search_results.items():
                    if search_type == "Serper Search" or search_type == "Serper Scholar":
                        selected_results.extend([result for i, result in enumerate(results) if st.session_state.selected_results.get(f"{search_type.lower().replace(' ', '_')}_{i}", False)])
                    elif search_type.startswith("Exa"):
                        category = search_type.split(" ")[-1].lower()
                        selected_results.extend([result for i, result in enumerate(results) if st.session_state.selected_results.get(f"exa_{category}_{i}", False)])
                
                if selected_results:
                    st.subheader("Selected Results for Further Processing")
                    for result in selected_results:
                        st.write(f"**{result.get('title', 'No title')}**")
                        st.write(result.get('snippet', result.get('text', 'No content'))[:1000] + "...")
                        st.write(f"[Source]({result.get('link', result.get('url', '#'))})")
                        st.write("---")
                else:
                    st.warning("No results selected. Please select at least one result to process.")

if __name__ == "__main__":
    main()
