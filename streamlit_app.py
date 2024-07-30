import streamlit as st
import pandas as pd
import plotly.express as px
from pytrends.request import TrendReq
from datetime import datetime, timedelta
import time
import random

# Set up page config
st.set_page_config(page_title="Google Trends Analyzer", page_icon="📈", layout="wide")

# Load credentials from secrets
try:
  USERNAME = st.secrets["credentials"]["username"]
  PASSWORD = st.secrets["credentials"]["password"]
except KeyError:
  st.error("Please set up 'credentials.username' and 'credentials.password' in your Streamlit secrets.")
  st.stop()

# Initialize PyTrends with a custom backoff_factor
pytrends = TrendReq(hl='en-US', tz=360, timeout=(10,25), retries=2, backoff_factor=0.1)

@st.cache_data(ttl=3600)
def get_google_trends(keyword, timeframe):
  max_retries = 3
  for attempt in range(max_retries):
      try:
          pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo='', gprop='')
          data = pytrends.interest_over_time()
          return data
      except Exception as e:
          if attempt < max_retries - 1:
              st.warning(f"Attempt {attempt + 1} failed. Retrying in {2 ** attempt} seconds...")
              time.sleep(2 ** attempt + random.random())
          else:
              st.error(f"Failed to fetch data after {max_retries} attempts. Please try again later.")
              return None

@st.cache_data(ttl=3600)
def get_related_topics(keyword):
  try:
      pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
      return pytrends.related_topics()[keyword]
  except Exception as e:
      st.error(f"Failed to fetch related topics: {str(e)}")
      return None

@st.cache_data(ttl=3600)
def get_related_queries(keyword):
  try:
      pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
      return pytrends.related_queries()[keyword]
  except Exception as e:
      st.error(f"Failed to fetch related queries: {str(e)}")
      return None

def login():
  st.title("Login to Google Trends Analyzer")
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
      st.title("Google Trends Analyzer")

      # User input
      keyword = st.text_input("Enter a keyword or topic:", "artificial intelligence")
      timeframes = {
          "Past 7 days": "now 7-d",
          "Past 30 days": "today 1-m",
          "Past 90 days": "today 3-m",
          "Past 12 months": "today 12-m",
          "Past 5 years": "today 5-y"
      }
      selected_timeframe = st.selectbox("Select time range", list(timeframes.keys()))

      if st.button("Analyze"):
          with st.spinner("Fetching Google Trends data..."):
              # Get trend data
              trend_data = get_google_trends(keyword, timeframes[selected_timeframe])
              
              if trend_data is not None and not trend_data.empty:
                  # Plot trend data
                  st.subheader(f"Interest Over Time for '{keyword}'")
                  fig = px.line(trend_data, x=trend_data.index, y=keyword, title=f"Interest over time for '{keyword}'")
                  st.plotly_chart(fig)

                  # Calculate and display statistics
                  st.subheader("Trend Statistics")
                  avg_interest = trend_data[keyword].mean()
                  max_interest = trend_data[keyword].max()
                  min_interest = trend_data[keyword].min()
                  
                  col1, col2, col3 = st.columns(3)
                  col1.metric("Average Interest", f"{avg_interest:.2f}")
                  col2.metric("Peak Interest", f"{max_interest:.2f}")
                  col3.metric("Lowest Interest", f"{min_interest:.2f}")

                  # Get related topics
                  related_topics = get_related_topics(keyword)
                  if related_topics:
                      st.subheader("Related Topics")
                      if 'top' in related_topics:
                          st.write("Top Related Topics:")
                          st.dataframe(related_topics['top'].head())
                      if 'rising' in related_topics:
                          st.write("Rising Related Topics:")
                          st.dataframe(related_topics['rising'].head())

                  # Get related queries
                  related_queries = get_related_queries(keyword)
                  if related_queries:
                      st.subheader("Related Queries")
                      if 'top' in related_queries:
                          st.write("Top Related Queries:")
                          st.dataframe(related_queries['top'].head())
                      if 'rising' in related_queries:
                          st.write("Rising Related Queries:")
                          st.dataframe(related_queries['rising'].head())

                  # Insights
                  st.subheader("Insights")
                  recent_trend = trend_data[keyword].iloc[-1] - trend_data[keyword].iloc[-2]
                  if recent_trend > 0:
                      st.write(f"📈 The interest in '{keyword}' is currently trending upwards.")
                  elif recent_trend < 0:
                      st.write(f"📉 The interest in '{keyword}' is currently trending downwards.")
                  else:
                      st.write(f"➡️ The interest in '{keyword}' is currently stable.")

                  if max_interest == 100:
                      peak_date = trend_data[trend_data[keyword] == 100].index[0]
                      st.write(f"🔥 Peak interest was observed on {peak_date.date()}.")

                  if related_queries and 'rising' in related_queries and not related_queries['rising'].empty:
                      st.write("🚀 Consider incorporating these rising related queries in your content:")
                      for query in related_queries['rising']['query'].head().tolist():
                          st.write(f"- {query}")
              else:
                  st.error("Failed to fetch trend data. Please try again later.")

if __name__ == "__main__":
  main()
