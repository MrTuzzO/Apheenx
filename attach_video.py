import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Apheenx.settings')
django.setup()

from video.models import Video
from django.core.files import File

def attach():
    video_id = 14
    file_path = '/home/apheenx/Apheenx/media/video_trailers/img-7040-1_xfpHjWen.mp4'

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    try:
        video = Video.objects.get(id=video_id)
        print(f"Found Video: {video.title}")
        
        # Attach the file to main_video
        with open(file_path, 'rb') as f:
            # We clear the stream UID so it re-ingests
            video.cf_stream_uid = None
            video.main_video.save('img-7040-1_xfpHjWen.mp4', File(f))
            
        print("Success! The video has been uploaded to R2 and linked to Cloudflare Stream.")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    attach()
