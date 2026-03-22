import re
import pandas as pd
import matplotlib.pyplot as plt
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# REPLACE THIS WITH YOUR ACTUAL API KEY
API_KEY = ''
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

def parse_duration(duration_str):
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    return hours * 3600 + minutes * 60 + seconds

def fetch_youtube_data(query, max_results=50):
    """Searches for videos and fetches their durations."""
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)
    
    try:
        # Search for the top videos matching the query
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video'
        ).execute()
        
        video_ids = []
        titles = []
        for item in search_response.get('items', []):
            video_ids.append(item['id']['videoId'])
            titles.append(item['snippet']['title'])
            
        if not video_ids:
            print("No videos found for this query.")
            return pd.DataFrame()

        # The API allows querying up to 50 IDs at once
        video_response = youtube.videos().list(
            id=','.join(video_ids),
            part='contentDetails'
        ).execute()
        
        durations = []
        for item in video_response.get('items', []):
            duration_iso = item['contentDetails']['duration']
            durations.append(parse_duration(duration_iso))
            
        df = pd.DataFrame({
            'Video Title': titles,
            'Video ID': video_ids,
            'Duration (Seconds)': durations,
            'Duration (Minutes)': [d / 60 for d in durations]
        })
        
        return df

    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return pd.DataFrame()

def analyze_and_plot(df, query):
    """Removes outliers, calculates statistics, and plots the data."""
    if df.empty:
        return
        
    # Outlier Removal
    Q1 = df['Duration (Seconds)'].quantile(0.25)
    Q3 = df['Duration (Seconds)'].quantile(0.75)
    IQR = Q3 - Q1
    
    # Define what constitutes an outlier
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    # Filter the dataframe to only include standard values
    initial_count = len(df)
    df_clean = df[(df['Duration (Seconds)'] >= lower_bound) & (df['Duration (Seconds)'] <= upper_bound)]
    removed_count = initial_count - len(df_clean)
    
    print(f"\n--- Outlier Filtering ---")
    print(f"Removed {removed_count} outlier(s) that fell outside the standard range.")
    print(f"Analyzing remaining {len(df_clean)} videos...")

    print(f"\n--- Statistical Analysis for '{query}' ---")
    stats = df_clean['Duration (Seconds)'].describe()
    print(stats.to_string())
    
    print("\nTop 5 Longest Videos (After filtering outliers):")
    longest = df_clean.nlargest(5, 'Duration (Seconds)')[['Video Title', 'Duration (Seconds)']]
    print(longest.to_string(index=False))

    plt.figure(figsize=(10, 6))
    
    # Sort the clean dataframe by duration
    df_sorted = df_clean.sort_values(by='Duration (Seconds)').reset_index(drop=True)
    
    plt.scatter(df_sorted['Duration (Seconds)'], df_sorted.index, 
                color='#4C72B0', s=60, edgecolor='black', alpha=0.8, zorder=3)
    
    plt.title(f'Dot Plot of Video Lengths (Outliers Removed): "{query}"', fontsize=14, pad=15)
    plt.xlabel('Video Length (Seconds)', fontsize=12)
    plt.ylabel('Video (Sorted by Length)', fontsize=12)
    
    median_length = df_clean['Duration (Seconds)'].median()
    plt.axvline(median_length, color='red', linestyle='dashed', linewidth=2, 
                label=f'Median: {median_length:.1f} sec', zorder=2)
    
    plt.yticks([]) 
    plt.legend()
    plt.grid(axis='x', linestyle='--', alpha=0.7, zorder=1)
    plt.tight_layout()
    
    plt.show()

if __name__ == '__main__':
    search_query = "debarb a hook"
    print(f"Connecting to YouTube API to fetch top videos for: '{search_query}'...")
    
    video_data_df = fetch_youtube_data(search_query, max_results=50)
    analyze_and_plot(video_data_df, search_query)