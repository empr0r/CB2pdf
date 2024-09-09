#!/usr/bin/env python3

import os
import shutil
import time
from PIL import Image
import zipfile
import rarfile
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Define directories
current_dir = os.path.dirname(os.path.abspath(__file__))
old_dir = os.path.join(current_dir, 'old')
log_file = os.path.join(current_dir, 'error_log.txt')

# Create 'old' directory if it doesn't exist
if not os.path.exists(old_dir):
    os.makedirs(old_dir)

# Function to log errors
def log_error(message):
    with open(log_file, 'a') as log:
        log.write(f"{message}\n")

# Function to convert images to PDF without lowering quality
def images_to_pdf(image_files, pdf_path, archive):
    images = []
    for image_file in image_files:
        with archive.open(image_file) as file:
            img = Image.open(file).convert('RGB')
            images.append(img)

    if images:
        images[0].save(pdf_path, save_all=True, append_images=images[1:], resolution=300.0)

    # Cleanup
    for img in images:
        img.close()

# Process CBZ files
def process_cbz(file_path, pdf_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as archive:
            image_files = sorted([name for name in archive.namelist() if name.lower().endswith(('jpg', 'jpeg', 'png'))])
            images_to_pdf(image_files, pdf_path, archive)
    except Exception as e:
        log_error(f"Error processing CBZ {file_path}: {str(e)}")

# Process CBR files using rarfile
def process_cbr(file_path, pdf_path):
    try:
        with rarfile.RarFile(file_path, 'r') as archive:
            image_files = sorted([name for name in archive.namelist() if name.lower().endswith(('jpg', 'jpeg', 'png'))])
            images_to_pdf(image_files, pdf_path, archive)
    except rarfile.NotRarFile:
        log_error(f"Not a valid RAR file: {file_path}")
    except Exception as e:
        log_error(f"Error processing CBR {file_path}: {str(e)}")

# Process individual file
def process_file(filename):
    file_path = os.path.join(current_dir, filename)
    pdf_path = os.path.join(current_dir, filename.rsplit('.', 1)[0] + '.pdf')

    try:
        # Process the file (CBZ or CBR)
        if filename.lower().endswith('.cbz'):
            process_cbz(file_path, pdf_path)
        elif filename.lower().endswith('.cbr'):
            process_cbr(file_path, pdf_path)

        # Move the file to 'old' directory after successful processing
        shutil.move(file_path, os.path.join(old_dir, filename))

    except Exception as e:
        log_error(f"Failed to process {filename}: {str(e)}")

# Batch processing with threading
def process_files_in_batches(batch_size=5, sleep_time=10, max_workers=4):
    # Get all CBZ and CBR files in the current directory
    file_list = [f for f in os.listdir(current_dir) if f.lower().endswith(('.cbz', '.cbr'))]

    total_files = len(file_list)

    # Process files in batches
    for i in range(0, total_files, batch_size):
        batch_files = file_list[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(total_files + batch_size - 1)//batch_size}...")

        # Progress bar for the batch
        with tqdm(total=len(batch_files), desc=f"Processing batch {i//batch_size + 1}", ncols=100) as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_file, filename) for filename in batch_files]

                # Wait for all files to finish and update the progress bar
                for future in futures:
                    future.result()
                    pbar.update(1)

        # Explicitly call garbage collection and take a break between batches
        import gc
        gc.collect()

        if i + batch_size < total_files:
            print(f"Taking a break before processing the next batch...")
            time.sleep(sleep_time)

# Run the batch processing
process_files_in_batches(batch_size=5, sleep_time=10, max_workers=4)  # Batch of 5, 10 seconds pause, 4 threads
