import os
import shutil
import zipfile
import tempfile
import logging
import gc
import sys

# External libraries required
try:
	import rarfile
	import img2pdf
	from natsort import natsorted
	from PIL import Image
	from tqdm import tqdm
except ImportError:
	print("ERROR: Missing dependencies.")
	print("Please install them using: pip install img2pdf natsort rarfile pillow tqdm")
	exit(1)

# --- Configuration ---
if getattr(sys, 'frozen', False):
	# If running as a bundled executable (PyInstaller)
	CURRENT_DIR = os.path.dirname(sys.executable)
else:
	# If running as a normal Python script
	CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OLD_DIR = os.path.join(CURRENT_DIR, 'old_files')
LOG_FILE = os.path.join(CURRENT_DIR, 'conversion_error_log.txt')

# Tuple of allowed image extensions (Tuple is strictly required by the .endswith() string method)
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif')

# Define a bounding box (Width, Height) to avoid excessively large images.
# 2560x2560 allows standard pages and horizontal spreads to scale down cleanly 
# without breaking the aspect ratio.
MAX_IMAGE_SIZE = (2560, 2560)

# System directories to ignore to prevent errors with hidden metadata files
IGNORED_FOLDERS = ('__MACOSX', '.git', '.ds_store')

# --- UnRAR Configuration for cross-platform support ---
# First, tries to find unrar in the system's global PATH (Linux, macOS, and configured Windows)
SYSTEM_UNRAR = shutil.which('unrar')

if SYSTEM_UNRAR:
	rarfile.UNRAR_TOOL = SYSTEM_UNRAR
else:
	# Fallback hardcoded paths for standard Windows installations
	WINDOWS_UNRAR_PATHS = [
		"C:/Programs/WinRar/UnRAR.exe",
		"C:/Program Files/WinRAR/UnRAR.exe",
		"C:/Program Files (x86)/WinRAR/UnRAR.exe"
	]
	
	unrar_found = False
	for path in WINDOWS_UNRAR_PATHS:
		if os.path.exists(path):
			rarfile.UNRAR_TOOL = path
			unrar_found = True
			break
			
	if not unrar_found:
		print("WARNING: UnRAR.exe could not be found in the system.")
		print("Make sure WinRAR is installed or place UnRAR.exe inside the script's directory.")


# --- Log Setup ---
logging.basicConfig(
	filename=LOG_FILE,
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)


# --- Functions ---

def log_msg(msg: str, msg_type: str = 'info') -> None:
	"""
	Prints a message to the console and simultaneously logs it to the log file.
	
	Args:
		msg (str): The message content to be logged.
		msg_type (str): The severity level of the log ('info' or 'error').
	"""
	print(msg)
	if msg_type == 'info':
		logging.info(msg)
	elif msg_type == 'error':
		logging.error(msg)


def setup_folders() -> None:
	"""
	Creates the necessary output directories if they do not exist.
	"""
	if not os.path.exists(OLD_DIR):
		os.makedirs(OLD_DIR)


def extract_files(file_path: str, destination_folder: str) -> bool:
	"""
	Extracts a CBZ or CBR archive into a specified destination directory.
	
	Args:
		file_path (str): The absolute path to the archive.
		destination_folder (str): The path where the files should be extracted.
		
	Returns:
		bool: True if the extraction was successful, False otherwise.
	"""
	try:
		if file_path.lower().endswith('.cbz'):
			with zipfile.ZipFile(file_path, 'r') as zf:
				zf.extractall(destination_folder)
			return True
		elif file_path.lower().endswith('.cbr'):
			with rarfile.RarFile(file_path, 'r') as rf:
				rf.extractall(destination_folder)
			return True
	except Exception as e:
		log_msg(f"  [ERROR] Failed extracting '{os.path.basename(file_path)}': {e}", 'error')
		return False
	return False


def find_images_recursively(root_folder: str) -> list:
	"""
	Scans the given directory and its subdirectories for supported image files.
	
	Args:
		root_folder (str): The base directory to start scanning.
		
	Returns:
		list: A naturally sorted list of absolute paths to the found images.
	"""
	image_files = []

	for root, dirs, files in os.walk(root_folder):
		# Modifying dirs in-place to prune ignored directories from os.walk
		dirs[:] = [d for d in dirs if d.lower() not in IGNORED_FOLDERS]
		
		for file in files:
			if file.lower().endswith(IMAGE_EXTENSIONS) and not file.startswith('._'):
				complete_path = os.path.join(root, file)
				image_files.append(complete_path)
	
	# Returns the list naturally sorted (e.g., page_2.jpg before page_10.jpg)
	return natsorted(image_files)


def convert_image_to_compatible(image_path: str) -> str | None:
	"""
	Ensures an image is strictly compatible with the PDF specification.
	Resizes excessively large images to maintain a consistent reading experience
	and converts unsupported formats to RGB JPEGs.
	
	Args:
		image_path (str): The absolute path to the original image.
		
	Returns:
		str | None: The path to the compatible image, or None if the image is corrupted.
	"""
	try:
		with Image.open(image_path) as img:
			# Check if the image exceeds the defined bounding box in any dimension
			needs_resize = img.width > MAX_IMAGE_SIZE[0] or img.height > MAX_IMAGE_SIZE[1]
			
			# Optimization: Skip processing if it's already a standard, properly-sized image
			if not needs_resize and img.format in ['JPEG', 'PNG'] and img.mode in ['RGB', 'L']:
				return image_path
			
			new_path = os.path.splitext(image_path)[0] + ".temp.jpg"
			
			# Handle transparency by flattening the image onto a white background
			if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
				bg = Image.new('RGB', img.size, (255, 255, 255))
				if img.mode != 'RGBA':
					img = img.convert('RGBA')
				bg.paste(img, mask=img.split()[3])
				img = bg  # Reassign to apply further transformations
			else:
				img = img.convert('RGB')
				
			# Apply resizing if necessary
			if needs_resize:
				# thumbnail() modifies the image in-place, strictly preserving aspect ratio.
				# LANCZOS is used to prevent Moiré patterns in comic book halftones.
				img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
			
			img.save(new_path, quality=90)
			return new_path
	except Exception as e:
		log_msg(f"  [WARNING] Corrupted or invalid image ignored: {os.path.basename(image_path)} - {e}", 'error')
		return None


def create_pdf(image_list: list, pdf_out_path: str) -> bool:
	"""
	Compiles a list of processed image paths into a single PDF file.
	
	Args:
		image_list (list): A list containing paths to the images.
		pdf_out_path (str): The destination path for the generated PDF.
		
	Returns:
		bool: True if the PDF was created successfully, False otherwise.
	"""
	final_images = []
	
	# Prepare and validate all images before conversion
	for img_path in image_list:
		compatible_img = convert_image_to_compatible(img_path)
		if compatible_img:
			final_images.append(compatible_img)
			
	if not final_images:
		return False

	try:
		# Convert images to PDF bytes
		pdf_bytes = img2pdf.convert(final_images)
		
		# Pylance Type Safety: Explicit check to assure pdf_bytes is not None
		if pdf_bytes is not None:
			with open(pdf_out_path, "wb") as f:
				f.write(pdf_bytes)
			return True
		else:
			log_msg(f"  [ERROR] Internal img2pdf conversion returned null for '{os.path.basename(pdf_out_path)}'.", 'error')
			return False
			
	except Exception as e:
		log_msg(f"  [ERROR] Failed saving PDF '{os.path.basename(pdf_out_path)}': {e}", 'error')
		if os.path.exists(pdf_out_path):
			os.remove(pdf_out_path)
		return False


def process_file(filename: str) -> None:
	"""
	Handles the full lifecycle of a single archive (extraction, processing, compilation, and cleanup).
	
	Args:
		filename (str): The name of the file to be processed.
	"""
	file_path = os.path.join(CURRENT_DIR, filename)
	pdf_name = os.path.splitext(filename)[0] + ".pdf"
	pdf_path = os.path.join(CURRENT_DIR, pdf_name)

	with tempfile.TemporaryDirectory() as temp_dir:
		# 1. Extraction Phase
		if not extract_files(file_path, temp_dir):
			return

		# 2. Deep Scan Phase
		images = find_images_recursively(temp_dir)
		
		if not images:
			log_msg(f"  [ERROR] No images found inside '{filename}' (Verify if the archive is empty).", 'error')
			return

		log_msg(f"  -> Found {len(images)} images (Structure: {os.path.dirname(images[0])})")

		# 3. PDF Generation Phase
		success = create_pdf(images, pdf_path)

		# 4. Cleanup and Archiving Phase
		if success:
			try:
				shutil.move(file_path, os.path.join(OLD_DIR, filename))
				log_msg(f"  [SUCCESS] '{pdf_name}' successfully created.")
			except Exception as e:
				log_msg(f"  [ERROR] PDF created, but failed to move the original archive: {e}", 'error')


def main() -> None:
	"""
	Main entry point. Orchestrates the batch processing of all archives in the directory.
	"""
	setup_folders()
	
	archives = [f for f in os.listdir(CURRENT_DIR) if f.lower().endswith(('.cbz', '.cbr'))]
	
	if not archives:
		print("No .cbz or .cbr files found in the current directory.")
		return

	print(f"Starting processing of {len(archives)} files...")
	print("=" * 60)

	with tqdm(total=len(archives), unit="vol") as pbar:
		for archive in archives:
			pbar.set_description(f"Processing {archive[:15]}...")
			process_file(archive)
			pbar.update(1)
			
			# Explicit garbage collection to free memory after heavy image processing
			gc.collect()

	print("=" * 60)
	print("Process finished. Check 'conversion_error_log.txt' in case of errors.")


if __name__ == "__main__":
	main()
