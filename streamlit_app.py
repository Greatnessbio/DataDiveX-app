import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import json
from ratelimit import limits, sleep_and_retry

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

@sleep_and_retry
@limits(calls=20, period=60)
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
          st.session_state.search_results = {} 
          with st.spinner("Searching and processing results..."):
              for search_type in selected_search_types:
                  if search_type == "Google Trends":
                      st.session_state.search_results[search_type] = google_trends_search(search_query, timeframes[selected_timeframe])
                  elif search_type == "Serper Search":
                      results = serper_search(search_query, "search")
                      st.session_state.search_results[search_type] = process_search_results(search_type, results)
                  elif search_type == "Serper Scholar":
                      results = serper_search(search_query, "scholar")
                      st.session_state.search_results[search_type] = process_search_results(search_type, results)
                  elif search_type.startswith("Exa"):
                      category = search_type.split(" ")[-1].lower()
                      results = exa_search(search_query, category, start_date_str, end_date_str)
                      st.session_state.search_results[search_type] = process_search_results(search_type, results)

      if st.session_state.search_results:
          for search_type, results in st.session_state.search_results.items():
              st.subheader(f"Results for {search_type}")
              if search_type == "Google Trends":
                  if results and "interest_over_time" in results:
                      df = pd.DataFrame(results["interest_over_time"]["timeline_data"])
                      df['date'] = pd.to_datetime(df['date'])
                      df['value'] = df['values'].apply(lambda x: x[0]['value'])
                      fig = px.line(df, x='date', y='value', title=f"Interest over time for '{search_query}'")
                      st.plotly_chart(fig)
                  else:
                      st.warning("No Google Trends data available for the given query and time range.")
              elif search_type in ("Serper Search", "Serper Scholar", "Exa Company", "Exa Research Paper", "Exa News", "Exa Tweet"):
                  for i, result in enumerate(results):
                      key = f"{search_type.lower().replace(' ', '_')}_{i}"
                      st.session_state.selected_results[key] = st.session_state.get(key, False)
                      col1, col2 = st.columns([0.1, 0.9])
                      with col1:
                          st.checkbox("Select", key=key, value=st.session_state.selected_results.get(key, False))
                      with col2:
                          st.write(f"**Title:** {result.get('title', 'N/A')}")
                          st.write(f"**Summary:** {result.get('summary', 'N/A')}")
                          st.write(f"**Link:** [{result.get('link', result.get('url', '#'))}]({result.get('link', result.get('url', '#'))})")
                          with st.expander("Full Content"):
                              st.write(result.get('full_content', 'No full content available'))
                          st.write("---")

      if st.session_state.search_results:
          if st.button("Process Selected Results"):
              selected_results = []
              for search_type, results in st.session_state.search_results.items():
                  if search_type != "Google Trends":
                      selected_results.extend([result for i, result in enumerate(results) if st.session_state.selected_results.get(f"{search_type.lower().replace(' ', '_')}_{i}", False)])
              
              if selected_results:
                  st.subheader("Selected Results for Further Processing")
                  for result in selected_results:
                      st.write(f"**{result.get('title', 'No title')}**")
                      st.write(result.get('summary', 'No summary available'))
                      st.write(f"[Source]({result.get('link', result.get('url', '#'))})")
                      st.write("---")
              else:
                  st.warning("No results selected. Please select at least one result to process.")

if __name__ == "__main__":
  main()
