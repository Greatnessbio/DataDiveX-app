import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
import time

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
if 'last_request_time' not in st.session_state:
  st.session_state.last_request_time = 0

# Simple rate limiting function
def rate_limited(max_per_minute):
  min_interval = 60.0 / max_per_minute
  def decorator(func):
      def wrapper(*args, **kwargs):
          now = time.time()
          elapsed = now - st.session_state.last_request_time
          left_to_wait = min_interval - elapsed
          if left_to_wait > 0:
              time.sleep(left_to_wait)
          st.session_state.last_request_time = time.time()
          return func(*args, **kwargs)
      return wrapper
  return decorator

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

@rate_limited(20)
def jina_reader(url):
  jina_url = f'https://r.jina.ai/{url}'
  headers = {
      'Accept': 'application/json',
      'X-With-Links-Summary': 'true'
  }
  try:
      response = requests.get(jina_url, headers=headers)
      response.raise_for_status()
      return response.json()
  except requests.exceptions.RequestException as e:
      st.error(f"Error fetching content from Jina AI: {e}")
      return None

def process_search_results(search_type, results):
  processed_results = []
  if search_type in ("Serper Search", "Serper Scholar"):
      for result in results.get("organic", []):
          url = result.get('link')
          if url:
              jina_content = jina_reader(url)
              if jina_content:
                  result['full_content'] = jina_content.get('text', '')
                  result['summary'] = jina_content.get('summary', '')
          processed_results.append(result)
  elif search_type.startswith("Exa"):
      for result in results.get('results', []):
          url = result.get('url')
          if url:
              jina_content = jina_reader(url)
              if jina_content:
                  result['full_content'] = jina_content.get('text', '')
                  result['summary'] = jina_content.get('summary', '')
          processed_results.append(result)
  return processed_results

def login():
  st.title("Login to TrendSift+")
  with st.form("login_form"):
      username = st.text_input("Username")
      password = st.text_input("Password", type="password")
      submit_button = st.form_submit_button("Login")

      if submit_button:
          if username == USERNAME and password == PASSWORD:
              st.session_state["logged_in"] = True
              st.empty()
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
      selected_search_types = st.sidebar.multiselect("Select search types", search_types, default=["Serper Search", "Exa News"])
      
      timeframes = {
          "Past 7 days": "now 7-d",
          "Past 30 days": "today 1-m",
          "Past 90 days": "today 3-m",
          "Past 12 months": "today 12-m",
          "Past 5 years": "today 5-y"
      }
      selected_timeframe = st.sidebar.selectbox("Select time range", list(timeframes.keys()))

      search_button = st.sidebar.button("Search")

      if search_button and search_query:
          st.session_state.search_results = {} 
          
          # Perform initial search and display quick results
          with st.spinner("Searching..."):
              quick_results = []
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
                          quick_results.extend([{'Source': search_type, 'Title': r['title'], 'Link': r['link']} for r in results['organic'][:5]])
                  elif search_type.startswith("Exa"):
                      category = search_type.split()[-1].lower()
                      results = exa_search(search_query, category, 
                                           (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                                           datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                      if results and 'results' in results:
                          quick_results.extend([{'Source': search_type, 'Title': r['title'], 'Link': r['url']} for r in results['results'][:5]])
                  
                  st.session_state.search_results[search_type] = results

              if quick_results:
                  st.subheader("Quick Results")
                  st.table(pd.DataFrame(quick_results))

          # Process and scrape results
          with st.spinner("Processing and summarizing results..."):
              for search_type in selected_search_types:
                  if search_type != "Google Trends":
                      st.session_state.search_results[search_type] = process_search_results(search_type, st.session_state.search_results[search_type])

          # Display detailed results
          st.subheader("Detailed Results")
          for search_type, results in st.session_state.search_results.items():
              if search_type != "Google Trends":
                  st.write(f"**{search_type}**")
                  for result in results:
                      st.write(f"**Title:** {result.get('title', 'N/A')}")
                      st.write(f"**Summary:** {result.get('summary', 'N/A')}")
                      st.write(f"**Link:** [{result.get('link', result.get('url', '#'))}]({result.get('link', result.get('url', '#'))})")
                      st.write(f"**Full Content:** {result.get('full_content', 'No full content available')[:500]}...")
                      st.write("---")

if __name__ == "__main__":
  main()
