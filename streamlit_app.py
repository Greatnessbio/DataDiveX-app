import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

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

@st.cache_data(ttl=3600)
def google_trends_search(query, timeframe):
    params = {
        "engine": "google_trends",
        "q": query,
        "data_type": "TIMESERIES",
        "date": timeframe,
        "api_key": SERPAPI_KEY
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        
        data = response.json()
        result = {}
        
        if "interest_over_time" in data:
            timeline_data = data["interest_over_time"].get("timeline_data", [])
            if timeline_data:
                df = pd.DataFrame(timeline_data)
                df['date'] = pd.to_datetime(df['date'].apply(lambda x: x.split('T')[0]))
                df['value'] = df['values'].apply(lambda x: x[0]['value'] if isinstance(x, list) and len(x) > 0 else x)
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df = df.dropna(subset=['value'])
                result['trend_data'] = df[['date', 'value']]
            else:
                st.warning("No timeline data available in the API response.")
        
        # Add related queries
        params["data_type"] = "RELATED_QUERIES"
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        data = response.json()
        if "related_queries" in data:
            result['related_queries'] = data["related_queries"]
        
        return result
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
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

@st.cache_data(ttl=3600)
def exa_get_contents(urls):
    exa_url = "https://api.exa.ai/get_contents"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }
    payload = {
        "urls": urls,
        "text": True,
        "highlights": {
            "num_sentences": 3
        }
    }
    
    try:
        response = requests.post(exa_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching contents from Exa: {str(e)}")
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

        # Debug Information
        st.write("Debug Information:")
        st.write(f"SerpAPI Key: {'Set' if SERPAPI_KEY else 'Not Set'}")
        st.write(f"Serper Key: {'Set' if SERPER_KEY else 'Not Set'}")
        st.write(f"Exa API Key: {'Set' if EXA_API_KEY else 'Not Set'}")

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
            for search_type in selected_search_types:
                st.subheader(f"Results for {search_type}")
                
                if search_type == "Google Trends":
                    trend_results = google_trends_search(search_query, timeframes[selected_timeframe])
                    if trend_results and 'trend_data' in trend_results:
                        fig = px.line(trend_results['trend_data'], x='date', y='value', title=f"Interest over time for '{search_query}'")
                        st.plotly_chart(fig)
                        
                        if 'related_queries' in trend_results:
                            st.subheader("Related Queries")
                            if 'top' in trend_results['related_queries']:
                                st.write("Top Queries:")
                                for query in trend_results['related_queries']['top'][:5]:
                                    st.write(f"- {query['query']}: {query['value']}")
                            if 'rising' in trend_results['related_queries']:
                                st.write("Rising Queries:")
                                for query in trend_results['related_queries']['rising'][:5]:
                                    st.write(f"- {query['query']}: {query['value']}")
                
                elif search_type == "Serper Search":
                    search_results = serper_search(search_query, "search")
                    if search_results and "organic" in search_results:
                        for i, result in enumerate(search_results["organic"]):
                            st.checkbox(f"Select result {i+1}", key=f"serper_search_{i}")
                            st.write(f"**{result['title']}**")
                            st.write(result['snippet'])
                            st.write(f"Full URL: {result['link']}")
                            if 'description' in result:
                                st.write(f"Description: {result['description']}")
                            st.write("---")
                    else:
                        st.warning("No Serper Search results found.")
                        st.write(f"Debug - Serper Search API response: {search_results}")
                
                elif search_type == "Serper Scholar":
                    scholar_results = serper_search(search_query, "scholar")
                    st.write(f"Debug - Serper Scholar results: {scholar_results}")
                    if scholar_results and "organic_results" in scholar_results:
                        for i, result in enumerate(scholar_results["organic_results"]):
                            st.checkbox(f"Select result {i+1}", key=f"serper_scholar_{i}")
                            st.write(f"**{result['title']}**")
                            st.write(f"Authors: {result.get('authors', 'N/A')}")
                            st.write(f"Publication: {result.get('publication', 'N/A')}")
                            st.write(f"Full URL: {result['link']}")
                            if 'snippet' in result:
                                st.write(f"Snippet: {result['snippet']}")
                            st.write("---")
                    else:
                        st.warning("No scholar results found.")
                        st.write(f"Debug - Serper Scholar API response: {scholar_results}")
                
                elif search_type.startswith("Exa"):
                    category = search_type.split(" ")[-1].lower()
                    exa_results = exa_search(search_query, category, start_date_str, end_date_str)
                    st.write(f"Debug - Exa results: {exa_results}")
                    if exa_results and "results" in exa_results:
                        st.write(f"Number of results: {len(exa_results['results'])}")
                        for i, result in enumerate(exa_results['results']):
                            st.checkbox(f"Select result {i+1}", key=f"exa_{category}_{i}")
                            st.write(f"**{result.get('title', 'No title')}**")
                            st.write(f"Full URL: {result.get('url', 'No URL')}")
                            st.write(result.get('text', 'No text')[:1000] + "...")  # Display first 1000 characters
                            if 'highlights' in result:
                                st.write("Highlights:")
                                for highlight in result['highlights']:
                                    st.write(f"- {highlight}")
                            st.write("---")
                    else:
                        st.warning(f"No results found for Exa search in category: {category}")
                        st.write(f"Debug - Exa API response: {exa_results}")

            # Process selected results
            if st.button("Process Selected Results"):
                selected_results = []
                selected_urls = []
                for search_type in selected_search_types:
                    if search_type == "Serper Search":
                        selected_results.extend([result for i, result in enumerate(search_results["organic"]) if st.session_state.get(f"serper_search_{i}", False)])
                        selected_urls.extend([result['link'] for i, result in enumerate(search_results["organic"]) if st.session_state.get(f"serper_search_{i}", False)])
                    elif search_type == "Serper Scholar":
                        selected_results.extend([result for i, result in enumerate(scholar_results["organic_results"]) if st.session_state.get(f"serper_scholar_{i}", False)])
                        selected_urls.extend([result['link'] for i, result in enumerate(scholar_results["organic_results"]) if st.session_state.get(f"serper_scholar_{i}", False)])
                    elif search_type.startswith("Exa"):
                        category = search_type.split(" ")[-1].lower()
                        selected_results.extend([result for i, result in enumerate(exa_results['results']) if st.session_state.get(f"exa_{category}_{i}", False)])
                        selected_urls.extend([result['url'] for i, result in enumerate(exa_results['results']) if st.session_state.get(f"exa_{category}_{i}", False)])
                
                st.subheader("Selected Results for Further Processing")
                st.write(f"Number of selected results: {len(selected_results)}")
                st.write("Fetching detailed content for selected URLs...")
                
                detailed_contents = exa_get_contents(selected_urls)
                
                if detailed_contents:
                    for url, content in detailed_contents.items():
                        st.write(f"**URL: {url}**")
                        st.write(f"Title: {content.get('title', 'No title')}")
                        st.write(f"Text: {content.get('text', 'No text')[:1000]}...")  # Display first 1000 characters
                        if 'highlights' in content:
                            st.write("Highlights:")
                            for highlight in content['highlights']:
                                st.write(f"- {highlight}")
                        st.write("---")
                else:
                    st.warning("Failed to fetch detailed contents for selected URLs.")

if __name__ == "__main__":
    main()
