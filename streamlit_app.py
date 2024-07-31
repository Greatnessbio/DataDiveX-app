import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Set up page config
st.set_page_config(page_title="TrendSift+", page_icon="", layout="wide")

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
if 'quick_results' not in st.session_state:
  st.session_state.quick_results = []
if 'selected_results' not in st.session_state:
  st.session_state.selected_results = []
if 'processed_results' not in st.session_state:
  st.session_state.processed_results = []

# Create a retry strategy
retry_strategy = Retry(
  total=3,
  status_forcelist=[429, 500, 502, 503, 504],
  allowed_methods=["HEAD", "GET", "OPTIONS"],
  backoff_factor=1
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

# User agent to mimic a browser
HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

@st.cache_data(ttl=3600)
def google_trends_search(query, timeframe):
  params = {
      "engine": "google_trends",
      "q": query,
      "date": timeframe,
      "api_key": SERPAPI_KEY
  }
  try:
      response = http.get("https://serpapi.com/search", params=params)
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
      response = http.post(url, headers=headers, data=payload)
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
      response = http.post(url, json=payload, headers=headers)
      response.raise_for_status()
      return response.json()
  except requests.exceptions.RequestException as e:
      st.error(f"Error fetching data from Exa: {str(e)}")
      return None

def get_jina_reader_content(url):
  # Prepend the URL with the Jina API base URL
  jina_url = f"https://r.jina.ai/{url}"
  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      'Accept': 'application/json'
  }
  try:
      response = http.get(jina_url, headers=headers)
      response.raise_for_status()
      time.sleep(3)  # 3-second delay between requests
      return response.json()
  except requests.exceptions.RequestException as e:
      return {
          'text': f"Failed to fetch content: {str(e)}",
      }

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
              st.experimental_rerun()  # Refresh the page to show the main content
          else:
              st.error("Invalid username or password")

def main():
  if "logged_in" not in st.session_state:
      st.session_state["logged_in"] = False

  if not st.session_state["logged_in"]:
      login()
  else:
      st.title("TrendSift+: Multi-Source Research Tool")

      with st.form("search_form"):
          st.header("Search Parameters")
          search_query = st.text_input("Enter search term")
          
          search_types = ["Google Trends", "Serper Search", "Serper Scholar", "Exa Company", "Exa Research Paper", "Exa News", "Exa Tweet"]
          selected_search_types = st.multiselect("Select search types", search_types, default=["Serper Search", "Exa News"])
          
          timeframes = {
              "Past 7 days": "now 7-d",
              "Past 30 days": "today 1-m",
              "Past 90 days": "today 3-m",
              "Past 12 months": "today 12-m",
              "Past 5 years": "today 5-y"
          }
          selected_timeframe = st.selectbox("Select time range", list(timeframes.keys()))

          search_button = st.form_submit_button("Search")

      if search_button and search_query:
          st.session_state.search_results = {} 
          st.session_state.quick_results = []
          
          # Perform initial search and display quick results
          with st.spinner("Searching..."):
              for search_type in selected_search_types:
                  if search_type == "Google Trends":
                      results = google_trends_search(search_query, timeframes[selected_timeframe])
                      if results and "interest_over_time" in results:
                          df = pd.DataFrame(results["interest_over_time"]["timeline_data"])
                          df['date'] = pd.to_datetime(df['date'])
                          df['value'] = df['values'].apply(lambda x: x[0]['value'])
                          fig = px.line(df, x='date', y='value', title=f"Interest over time for '{search_query}'")
                          st.plotly_chart(fig)
                  elif search_type in ("Serper Search", "Serper Scholar"):
                      results = serper_search(search_query, search_type.split()[-1].lower())
                      if results and 'organic' in results:
                          st.session_state.quick_results.extend([{'Source': search_type, 'Title': r['title'], 'Link': r['link']} for r in results['organic'][:5]])
                  elif search_type.startswith("Exa"):
                      category = search_type.split()[-1].lower()
                      results = exa_search(search_query, category, 
                                           (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                           datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                      if results and 'results' in results:
                          st.session_state.quick_results.extend([{'Source': search_type, 'Title': r['title'], 'Link': r['url']} for r in results['results'][:5]])
                  
                  st.session_state.search_results[search_type] = results

      if st.session_state.quick_results:
          st.subheader("Quick Results")
          df = pd.DataFrame(st.session_state.quick_results)
          df['Get Content'] = False
          edited_df = st.data_editor(df, column_config={
              "Get Content": st.column_config.CheckboxColumn(default=False),
              "Source": st.column_config.TextColumn(width="medium"),
              "Title": st.column_config.TextColumn(width="large"),
              "Link": st.column_config.TextColumn(width="large")
          }, hide_index=True, use_container_width=True, num_rows="dynamic")
          st.session_state.selected_results = edited_df[edited_df['Get Content']].to_dict('records')

      if st.button("Process Selected Results"):
          # Process and scrape selected results
          with st.spinner("Processing selected results..."):
              st.session_state.processed_results = []
              for result in st.session_state.selected_results:
                  jina_content = get_jina_reader_content(result['Link']) 
                  if isinstance(jina_content, dict):
                      result['full_content'] = jina_content.get('text', 'No content available')
                  else:
                      result['full_content'] = jina_content
                  st.session_state.processed_results.append(result)

      # Display detailed results for selected items
      if st.session_state.processed_results:
          st.subheader("Detailed Results for Selected Items")
          for i, result in enumerate(st.session_state.processed_results):
              st.write(f"**Title:** {result['Title']}")
              st.write(f"**Source:** {result['Source']}")
              st.write(f"**Link:** [{result['Link']}]({result['Link']})")
              st.write("**Full Content:**")
              st.text_area(f"Content_{i}", result['full_content'], height=300)
              st.write("---")

if __name__ == "__main__":
  main()
