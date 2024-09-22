from flask import Flask, render_template, jsonify
import requests
import json
import pandas as pd
import yahoo_fin.stock_info as si
import yfinance as yf
from yahoo_fin import news
from pysentimiento import create_analyzer
from datetime import datetime, timedelta
import threading
import time
import pytz  # Import pytz for timezone handling
import holidays

app = Flask(__name__)
analyzer = create_analyzer(task="sentiment", lang="en")

# Define the country holidays (for example, US holidays)
us_holidays = holidays.US()
# Mountain Time Zone
MTN_TZ = pytz.timezone('America/Denver')

# Function to fetch stock gainers and save to JSON
def fetch_gainers_and_save_to_json():
    url = "https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey=47aF67g8nwXCiKguRSbHRy3WfKuQFPPq"
    response = requests.get(url)
    if response.status_code == 200:
        gainers_data = response.json()
        with open('gainers.json', 'w') as json_file:
            json.dump(gainers_data, json_file, indent=4)
        print("Data successfully saved to gainers.json")
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}, Error: {response.text}")

# Function to get news data and process it
def get_news_data_from_json(json_file_path: str):
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    all_titles = []
    all_published_dates = []
    all_links = []
    all_symbols = []
    all_percent_changes = []
    all_current_prices = []
    all_floats = []
    all_avg_volumes = []
    all_current_volumes = []

    for item in data:
        symbol = item['symbol']
        percent_change = item['changesPercentage']
        price = item['price']
        stock = yf.Ticker(symbol)
        stock_info = stock.info
        
        float_shares = stock_info.get('floatShares')
        average_volume = stock_info.get('averageVolume')
        stock_data = stock.history(period='1d')
        current_volume = stock_data['Volume'][0] if not stock_data.empty else None

        news_data = news.get_yf_rss(symbol)
        
        for article in news_data:
            cropped_title = article['title']
            published = article['published'][:25]
            
            all_titles.append(cropped_title)
            all_published_dates.append(published)
            all_links.append(article['link'])
            all_symbols.append(symbol)
            all_percent_changes.append(percent_change)
            all_current_prices.append(price)
            all_floats.append(float_shares)
            all_avg_volumes.append(average_volume)
            all_current_volumes.append(current_volume)
    
    df = pd.DataFrame({
        'Symbol': all_symbols,
        'Percent Change': all_percent_changes,
        'Summary': all_titles,
        'Published': all_published_dates,
        'Link': all_links,
        'Current Price': all_current_prices,
        'Float': all_floats,
        'Average Volume': all_avg_volumes,
        'Current Volume': all_current_volumes
    })
    return df

# Function to filter data based on the strategy
def filter_strategy(big_data2):
    return big_data2[(big_data2['Current Volume'] >= 5 * big_data2['Average Volume']) &
                     (big_data2['Float'] <= 10000000) &
                     (big_data2['Current Price'] <= 20)]

def filter_time(big_data1):
    # Convert the 'Published' column to datetime format if it's not already in datetime format
    big_data1['Published'] = pd.to_datetime(big_data1['Published'], errors='coerce')

    current_date = datetime.now()
    two_weeks_ago = current_date - timedelta(weeks=2)

    # Filter data based on the 'Published' column
    big_data2 = big_data1[big_data1['Published'] >= two_weeks_ago]
    return big_data2

# Function to apply sentiment analysis
def sentiment(big_data3): 
    big_data3['Neg'] = None
    big_data3['Neo'] = None
    big_data3['Pos'] = None
    for index, row in big_data3.iterrows():
        result = analyzer.predict(row['Summary'])
        big_data3.at[index, 'Neg'] = result.probas['NEG']
        big_data3.at[index, 'Neo'] = result.probas['NEU']
        big_data3.at[index, 'Pos'] = result.probas['POS']
    return big_data3

# Function to check if the current time meets the conditions
def is_valid_time():
    current_mtn_time = datetime.now()
    
    # Check if it's a weekday (Monday to Friday) and not a holiday
    if current_mtn_time.weekday() >= 5 or current_mtn_time.date() in us_holidays:
        return False
    
    # Check if the current time is between 7:30 AM and 2:00 PM
    start_time = current_mtn_time.replace(hour=7, minute=30, second=0, microsecond=0)
    end_time = current_mtn_time.replace(hour=14, minute=0, second=0, microsecond=0)
    
    return start_time <= current_mtn_time <= end_time

# Background thread function to periodically fetch and process data on Mountain Time
def fetch_data_periodically_mtn():
    while True:
        # Get the current time in Mountain Time
        current_mtn_time = datetime.now(MTN_TZ)
        
        # Check if the time is at the start of a specific hour (e.g., 0 minutes past the hour)
        if is_valid_time():
            # Fetch and process data if it's on the hour
            fetch_gainers_and_save_to_json()
            big_data01 = get_news_data_from_json('gainers.json')
            big_data02 = filter_time(big_data01)  # Apply time filtering here
            big_data03 = filter_strategy(big_data02)
            big_data03 = sentiment(big_data03)

            # Add current time as a new column to the DataFrame
            big_data03['Timestamp'] = current_mtn_time.strftime('%Y-%m-%d %H:%M:%S %Z')
            # Save the data along with the timestamp to the JSON file
            big_data03.to_json('filtered_gainers.json', orient='records')

            print(f"Data updated at {current_mtn_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Format the current Mountain Time
        formatted_time = current_mtn_time.strftime('%Y-%m-%d %H:%M:%S %Z')

# Create a dictionary with the formatted time
        time_data = {
            "current_mtn_time": formatted_time
        }

        # Export the dictionary to a JSON file
        with open('current_mtn_time.json', 'w') as json_file:
            json.dump(time_data, json_file, indent=4)
        print(f"Market Closed: {current_mtn_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        time.sleep(120)

# Start the data-fetching thread
threading.Thread(target=fetch_data_periodically_mtn, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current_mtn_time', methods=['GET'])
def get_current_mtn_time():
    with open('current_mtn_time.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/gainers')
def gainers_data():
    with open('filtered_gainers.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
