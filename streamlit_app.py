import streamlit as st
import pandas as pd
import plotly.express as px
from pytrends.request import TrendReq
from datetime import datetime, timedelta

# Set up page config
st.set_page_config(page_title="Google Trends Analyzer", page_icon="📈", layout="wide")

# Initialize PyTrends
pytrends = TrendReq(hl='en-US', tz=360)

def get_google_trends(keyword, timeframe):
  pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo='', gprop='')
  data = pytrends.interest_over_time()
  return data

def get_related_topics(keyword):
  pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
  return pytrends.related_topics()[keyword]

def get_related_queries(keyword):
  pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='')
  return pytrends.related_queries()[keyword]

def main():
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
          st.subheader("Related Topics")
          if 'top' in related_topics:
              st.write("Top Related Topics:")
              st.dataframe(related_topics['top'].head())
          if 'rising' in related_topics:
              st.write("Rising Related Topics:")
              st.dataframe(related_topics['rising'].head())

          # Get related queries
          related_queries = get_related_queries(keyword)
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

          if 'rising' in related_queries and not related_queries['rising'].empty:
              st.write("🚀 Consider incorporating these rising related queries in your content:")
              for query in related_queries['rising']['query'].head().tolist():
                  st.write(f"- {query}")

if __name__ == "__main__":
  main()
