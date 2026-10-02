import os
import requests

def ingest_video_to_cloudflare_stream(video_url):
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    api_token = os.getenv('CLOUDFLARE_STREAM_API_TOKEN') or os.getenv('CLOUDFLARE_API_TOKEN')
    
    if not account_id or not api_token:
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/stream/copy"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    data = {
        "url": video_url,
        "meta": {"name": "Apheenx Video Upload"}
    }
    
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()['result']['uid']
    
    return None