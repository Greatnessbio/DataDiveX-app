import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="TrendSift", page_icon="📊", layout="wide")

# Load credentials from secrets
USERNAME = st.secrets["credentials"]["username"]
PASSWORD = st.secrets["credentials"]["password"]
SERP_API_KEY = st.secrets["serpapi"]["api_key"]

@st.cache_data(ttl=3600)
def google_trends_search(query, start_date, end_date):
    params = {
        "engine": "google_trends",
        "q": query,
        "data_type": "TIMESERIES",
        "date": f"{start_date} {end_date}",
        "api_key": SERP_API_KEY
    }
    
    response = requests.get("https://serpapi.com/search", params=params)
    
    if response.status_code == 200:
        data = response.json()
        if "interest_over_time" in data:
            df = pd.DataFrame(data["interest_over_time"]["timeline_data"])
            df['date'] = pd.to_datetime(df['date'].apply(lambda x: x.split('–')[0].strip()))
            df['value'] = df['values'].apply(lambda x: x[0]['extracted_value'])
            return df[['date', 'value']]
        else:
            st.warning("No trend data available for the given query and time range.")
            return None
    else:
        st.error(f"Error fetching data: {response.status_code}")
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
        start_date = st.sidebar.date_input("Start date", datetime.now() - timedelta(days=30))
        end_date = st.sidebar.date_input("End date", datetime.now())

        search_button = st.sidebar.button("Search")

        if search_button and search_query:
            with st.spinner("Fetching trend data..."):
                formatted_start_date = start_date.strftime("%Y-%m-%d")
                formatted_end_date = end_date.strftime("%Y-%m-%d")

                trend_data = google_trends_search(search_query, formatted_start_date, formatted_end_date)

                if trend_data is not None and not trend_data.empty:
                    st.subheader(f"Google Trends for '{search_query}'")
                    
                    # Create a line chart
                    fig = px.line(trend_data, x='date', y='value', title=f"Interest over time for '{search_query}'")
                    st.plotly_chart(fig)

                    # Display the data
                    st.subheader("Trend Data")
                    st.dataframe(trend_data)

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
                    st.error("Failed to fetch trend data. Please try again.")

if __name__ == "__main__":
    main()
