import os
import csv
import hashlib
import requests
from PIL import Image, ImageOps
from io import BytesIO
from datetime import datetime
import pandas as pd

OUTPUT_DIR = 'images'
CSV_LINK_FILE = 'image_links.csv'
MAX_IMAGES_PER_CATEGORY = 500
downloaded_count_per_category = {} 
downloaded_count = 0
def get_category_chunks(df):
    unique_categories = df['category'].unique()
    chunks = [unique_categories[i::4] for i in range(4)]
    return chunks

def get_aspect_ratio(image):
    width, height = image.size
    return width / height

def find_closest_aspect_ratio(image):
    aspect_ratios = {
        "1:1": 1.0,
        "4:3": 4 / 3,
        "16:9": 16 / 9
    }
    original_aspect_ratio = get_aspect_ratio(image)
    return min(aspect_ratios, key=lambda r: abs(aspect_ratios[r] - original_aspect_ratio))

def resize_image(image, target_size):
    image = ImageOps.exif_transpose(image)
    new_image = Image.new("RGB", target_size, (255, 255, 255))
    image.thumbnail(target_size)
    x_offset = (target_size[0] - image.size[0]) // 2
    y_offset = (target_size[1] - image.size[1]) // 2
    new_image.paste(image, (x_offset, y_offset))
    return new_image

def resize_and_save(image, file_path):
    closest_ratio = find_closest_aspect_ratio(image)
    if closest_ratio == "1:1":
        resized_img = resize_image(image, (640, 640))
    elif closest_ratio == "4:3":
        resized_img = resize_image(image, (1024, 768))
    elif closest_ratio == "16:9":
        resized_img = resize_image(image, (1280, 720))
    resized_img.save(file_path.replace('.jpg', f'_{closest_ratio.replace(":", "-")}.jpg'))

def download_image_from_csv_row(category, url, output_dir, CSV_METADATA_FILE):
    global downloaded_count_per_category
    if downloaded_count_per_category.get(category, 0) >= MAX_IMAGES_PER_CATEGORY:
        print(f"Reached the maximum download limit of 500 images for category '{category}'.")
        return

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # print(f"Downloading image from {url}...")
            image_content = response.content
            file_hash = hashlib.md5(image_content).hexdigest()
            image = Image.open(BytesIO(image_content))
            image_format = image.format

            if image_format == 'PNG':
                file_ext = 'png'
            elif image_format in ['JPEG', 'JPG', 'WEBP']:
                file_ext = 'jpg'
            else:
                print(f"Unsupported format: {image_format}")
                return

            category_path = os.path.join(output_dir, category)
            os.makedirs(category_path, exist_ok=True)
            file_path = os.path.join(category_path, f"{file_hash}.{file_ext}")
            # print(f"File path: {file_path}")
            if not os.path.exists(file_path) and 'plus.unsplash' not in url:
                resize_and_save(image, file_path)
                print(f"Saved image: {file_path} from {url}")
                downloaded_count_per_category[category] = downloaded_count_per_category.get(category, 0) + 1  # Increment the counter for the category

                already_logged = False
                if os.path.exists(CSV_METADATA_FILE):
                    with open(CSV_METADATA_FILE, newline='', encoding='utf-8') as meta_file:
                        reader = csv.DictReader(meta_file)
                        for row in reader:
                            if row['file_path'] == file_path:
                                already_logged = True
                                break

                if not already_logged:
                    with open(CSV_METADATA_FILE, mode='a', newline='', encoding='utf-8') as metafile:
                        meta_writer = csv.writer(metafile)
                        if os.stat(CSV_METADATA_FILE).st_size == 0:
                            meta_writer.writerow(['category', 'url', 'download_time', 'file_path'])
                        meta_writer.writerow([category, url, datetime.now(), file_path])
            # else:
            #     print(f"Image already exists: {file_path}")
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")

def download_images_from_csv(output_dir, df, CSV_METADATA_FILE):
    global downloaded_count_per_category
    for _, row in df.iterrows():
        category = row['category']
        url = row['url']
        if downloaded_count_per_category.get(category, 0) >= MAX_IMAGES_PER_CATEGORY:
            print(f"Reached the maximum download limit of 500 images for category '{category}'.")
            continue
        download_image_from_csv_row(category, url, output_dir, CSV_METADATA_FILE)
