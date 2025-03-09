import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageChops
from io import BytesIO
import pandas as pd
import hashlib
import time

categories = ['person', 'bicycle', 'car', 'motorbike', 'aeroplane']
target_images_per_category = 500

# Define image size requirements
size_requirements = {
    '1:1': [(640, 640), (416, 416)],
    '4:3': [(1024, 768)],
    '16:9': [(1280, 720)]
}

# Create directories for each category
for category in categories:
    os.makedirs(f'images/{category}', exist_ok=True)

# Function to check if an image is black
def is_black_image(img):
    extrema = img.convert("L").getextrema()
    return extrema[0] == extrema[1]

# Function to check if an image has a watermark
def has_watermark(img):
    # Simple heuristic: check for transparency or large uniform areas
    if img.mode in ('RGBA', 'LA'):
        return True
    return False

# Function to download and save images
def download_image(url, category):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img_format = img.format.lower()
        if img_format not in ['png', 'jpg', 'jpeg']:
            return None

        # Check image size
        width, height = img.size
        if (width, height) not in size_requirements['1:1'] and \
           (width, height) not in size_requirements['4:3'] and \
           (width, height) not in size_requirements['16:9']:
            return None

        # Data cleaning
        if is_black_image(img) or has_watermark(img):
            return None

        # Save image
        img_hash = hashlib.md5(response.content).hexdigest()
        img_path = f'images/{category}/{img_hash}.{img_format}'
        img.save(img_path)

        # Return metadata
        return {
            'image_url': url,
            'source': 'web',
            'download_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'file_path': img_path
        }
    except Exception as e:
        print(f"Failed to download image from {url}: {e}")
        return None

# Function to scrape images from a website
def scrape_images(category):
    url = f'https://www.pexels.com/search/{category}/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    img_tags = soup.find_all('img')

    metadata = []
    for img_tag in img_tags:
        img_url = img_tag.get('src')
        if img_url:
            data = download_image(img_url, category)
            if data:
                metadata.append(data)
                if len(metadata) >= target_images_per_category:
                    break
    return metadata

# Main function to scrape images for all categories
def main():
    all_metadata = []
    for category in categories:
        print(f"Scraping images for category: {category}")
        metadata = scrape_images(category)
        all_metadata.extend(metadata)

    # Save metadata to CSV
    df = pd.DataFrame(all_metadata)
    df.to_csv('image_metadata.csv', index=False)

if __name__ == '__main__':
    main()
