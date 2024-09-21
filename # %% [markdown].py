# %% [markdown]
# ## Retrieve Top Gainers Json (Careful, Limited API Usages)

# %%
import requests
import json

def fetch_gainers_and_save_to_json():
    # Define the API endpoint
    url = "https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey=47aF67g8nwXCiKguRSbHRy3WfKuQFPPq"

    # Send a GET request to the API
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response content into JSON
        gainers_data = response.json()
        
        # Save the data into a JSON file
        with open('gainers.json', 'w') as json_file:
            json.dump(gainers_data, json_file, indent=4)
        
        print("Data successfully saved to gainers.json")
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}, Error: {response.text}")

# Fetch gainers and save them to a JSON file
fetch_gainers_and_save_to_json()


# %% [markdown]
# ## OVERALL DASHBOARD CREATION

# %%
import json
import pandas as pd
import yahoo_fin.stock_info as si
from yahoo_fin import news
import yfinance as yf
from pysentimiento import create_analyzer

analyzer = create_analyzer(task="sentiment", lang="en")

# Define the function to fetch and convert news to DataFrame
def get_news_data_from_json(json_file_path: str):
    # Load the JSON file with the symbols
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Initialize lists to store all symbols' news data
    all_titles = []
    all_published_dates = []
    all_links = []
    all_symbols = []
    all_percent_changes = []
    all_current_prices = []
    all_floats = []
    all_avg_volumes = []
    all_current_volumes = []
    
    # Iterate through the data
    for item in data:
        symbol = item['symbol']
        percent_change = item['changesPercentage']
        price = item['price']
        # Fetch the stock data using yfinance
        stock = yf.Ticker(symbol)
        stock_info = stock.info
        
        # Fetch the current price, float, average volume, and current volume
        float_shares = stock_info.get('floatShares')
        average_volume = stock_info.get('averageVolume')
        
        # Fetch the latest trading day's data for the current volume
        stock_data = stock.history(period='1d')
        current_volume = stock_data['Volume'][0] if not stock_data.empty else None

        # Fetch the news using the provided symbol
        news_data = news.get_yf_rss(symbol)
        
        # Process each article in the news list
        for article in news_data:
            # Crop the title if it's too long
            cropped_title = article['title']
            published = article['published'][:25]
            
            # Append data to the respective lists
            all_titles.append(cropped_title)
            all_published_dates.append(published)
            all_links.append(article['link'])
            all_symbols.append(symbol)
            all_percent_changes.append(percent_change)
            all_current_prices.append(price)
            all_floats.append(float_shares)
            all_avg_volumes.append(average_volume)
            all_current_volumes.append(current_volume)
    
    # Create a DataFrame from the lists
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

# Example usage:
# json_file_path = 'path_to_your_json_file.json'
# news_df = get_news_data_from_json(json_file_path)


# %%
big_data1 = get_news_data_from_json('gainers.json')

# %%
from datetime import datetime, timedelta
big_data1['Published'] = pd.to_datetime(big_data1['Published'])
current_date = datetime.now()
two_weeks_ago = current_date - timedelta(weeks=2)
big_data2 = big_data1[big_data1['Published'] >= two_weeks_ago]

# %%
big_data3 = big_data2[(big_data2['Current Volume'] >= 5 * big_data2['Average Volume']) &
                 (big_data2['Float'] <= 10000000) &
                 (big_data2['Current Price'] <= 20)]

# %%
# Create new columns to store the sentiment scores (NEG, NEU, POS)
big_data3['Neg'] = None
big_data3['Neo'] = None
big_data3['Pos'] = None

# Loop through each row in the dataframe and apply the analyzer to the Summary column
for index, row in big_data3.iterrows():
    result = analyzer.predict(row['Summary'])
    # Store the probabilities in the respective columns
    big_data3.at[index, 'Neg'] = result.probas['NEG']
    big_data3.at[index, 'Neo'] = result.probas['NEU']
    big_data3.at[index, 'Pos'] = result.probas['POS']

# %%
## just to get the requirements.txt
import os
os.system('pip freeze > requirements.txt')


# %%



