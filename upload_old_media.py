import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Apheenx.settings')
django.setup()

from django.core.files.storage import default_storage
from django.conf import settings

local_media_root = settings.MEDIA_ROOT

def sync_media():
    if not os.path.exists(local_media_root):
        print(f"Local media directory not found at {local_media_root}")
        return

    print("Starting sync to Cloudflare R2...")
    
    success_count = 0
    skip_count = 0
    error_count = 0

    for root, dirs, files in os.walk(local_media_root):
        for file in files:
            local_path = os.path.join(root, file)
            # Get relative path (e.g., 'videos/my_video.mp4')
            relative_path = os.path.relpath(local_path, local_media_root)
            # Fix windows slashes to forward slashes just in case
            relative_path = relative_path.replace('\\', '/')

            print(f"Checking {relative_path}...")

            if default_storage.exists(relative_path):
                print(f"  -> Already exists in R2. Skipping.")
                skip_count += 1
                continue

            print(f"  -> Uploading to R2...")
            try:
                with open(local_path, 'rb') as f:
                    default_storage.save(relative_path, f)
                print(f"  -> Upload successful!")
                success_count += 1
            except Exception as e:
                print(f"  -> ERROR uploading: {e}")
                error_count += 1

    print("\n--- Sync Summary ---")
    print(f"Successfully Uploaded: {success_count}")
    print(f"Skipped (Already in R2): {skip_count}")
    print(f"Failed: {error_count}")
    print("--------------------")

if __name__ == '__main__':
    sync_media()
