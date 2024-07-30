import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# Set up page config
st.set_page_config(page_title="TrendSift", page_icon="📊", layout="wide")

# Load credentials from secrets
try:
  USERNAME = st.secrets["credentials"]["username"]
  PASSWORD = st.secrets["credentials"]["password"]
  SERP_API_KEY = st.secrets["serpapi"]["api_key"]
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
      "api_key": SERP_API_KEY
  }
  
  try:
      response = requests.get("https://serpapi.com/search", params=params)
      response.raise_for_status()
      
      data = response.json()
      if "interest_over_time" in data:
          df = pd.DataFrame(data["interest_over_time"]["timeline_data"])
          df['date'] = pd.to_datetime(df['date'].apply(lambda x: x.split('T')[0]))
          df['value'] = df['values'].apply(lambda x: x[0]['value'])
          df['value'] = pd.to_numeric(df['value'], errors='coerce')  # Convert to numeric, replacing errors with NaN
          df = df.dropna(subset=['value'])  # Remove any rows where 'value' is NaN
          return df[['date', 'value']]
      else:
          st.warning("No trend data available for the given query and time range.")
          return None
  except requests.exceptions.RequestException as e:
      st.error(f"Error fetching data: {e}")
      return None

@st.cache_data(ttl=3600)
def get_related_queries(query, timeframe):
  params = {
      "engine": "google_trends",
      "q": query,
      "data_type": "RELATED_QUERIES",
      "date": timeframe,
      "api_key": SERP_API_KEY
  }
  
  try:
      response = requests.get("https://serpapi.com/search", params=params)
      response.raise_for_status()
      
      data = response.json()
      if "related_queries" in data:
          return data["related_queries"]
      else:
          st.warning("No related queries available for the given query and time range.")
          return None
  except requests.exceptions.RequestException as e:
      st.error(f"Error fetching related queries: {e}")
      return None

def login():
  st.title("Login to TrendSift")
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
      st.title("TrendSift: Google Trends Analysis")

      st.sidebar.header("Search Parameters")
      search_query = st.sidebar.text_input("Enter search term")
      
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
          with st.spinner("Fetching trend data..."):
              trend_data = google_trends_search(search_query, timeframes[selected_timeframe])
              related_queries = get_related_queries(search_query, timeframes[selected_timeframe])

              if trend_data is not None and not trend_data.empty:
                  st.subheader(f"Google Trends for '{search_query}'")
                  
                  # Create a line chart
                  fig = px.line(trend_data, x='date', y='value', title=f"Interest over time for '{search_query}'")
                  st.plotly_chart(fig)

                  # Calculate and display statistics
                  st.subheader("Trend Statistics")
                  if not trend_data['value'].empty:
                      avg_interest = trend_data['value'].mean()
                      max_interest = trend_data['value'].max()
                      min_interest = trend_data['value'].min()
                      
                      col1, col2, col3 = st.columns(3)
                      col1.metric("Average Interest", f"{avg_interest:.2f}")
                      col2.metric("Peak Interest", f"{max_interest:.2f}")
                      col3.metric("Lowest Interest", f"{min_interest:.2f}")
                  else:
                      st.warning("No numeric data available for statistics calculation.")

                  # Display the data
                  st.subheader("Trend Data")
                  st.dataframe(trend_data)

                  # Display related queries
                  if related_queries:
                      st.subheader("Related Queries")
                      if 'top' in related_queries:
                          st.write("Top Related Queries:")
                          st.dataframe(pd.DataFrame(related_queries['top']))
                      if 'rising' in related_queries:
                          st.write("Rising Related Queries:")
                          st.dataframe(pd.DataFrame(related_queries['rising']))

                  # Allow user to download the data
                  csv = trend_data.to_csv(index=False)
                  st.download_button(
                      label="Download data as CSV",
                      data=csv,
                      file_name=f"{search_query}_trend_data.csv",
                      mime="text/csv",
                  )
              elif trend_data is not None:
                  st.warning("No data available for the given query and time range.")
              else:
                  st.error("Failed to fetch trend data. Please check the error message above.")

if __name__ == "__main__":
  main()
