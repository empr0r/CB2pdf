# CB2PDF

This Python script converts `.cbz` and `.cbr` files to PDF format and moves the original files to a folder named `old` within the same directory.

## Requirements

- **Python 3**: Ensure that Python 3 is installed on your system.
- **Pillow**: Python Imaging Library to handle image processing.
- **rarfile**: Library to handle `.cbr` files.
- **tqdm**: Library for displaying progress bars.

## Installation

### Using pip (Preferred)

1. **Install Required Libraries**:
   - **Pillow**: Install using `pip`:
     ```bash
     pip install pillow
     ```
   - **rarfile**: Install using `pip`:
     ```bash
     pip install rarfile
     ```
   - **tqdm**: Install using `pip`:
     ```bash
     pip install tqdm
     ```

2. **Clone the Repository**:
   Open a terminal and clone the repository from GitHub:
    ```bash
    git clone https://github.com/empr0r/CB2PDF.git
    ```

### On Arch Linux

If `pip` is not an option or if you prefer to use system packages, follow these steps:

1. **Install Required Libraries**:
   - **Pillow**: Install using `pacman`:
     ```bash
     sudo pacman -S python-pillow
     ```
   - **rarfile**: Install using `paru` or another AUR helper:
     ```bash
     paru -S python-rarfile
     ```
   - **tqdm**: Install using `pacman`:
     ```bash
     sudo pacman -S python-tqdm
     ```

2. **Clone the Repository**:
   Open a terminal and clone the repository from GitHub:
    ```bash
    git clone https://github.com/empr0r/CB2PDF.git
    ```

## Usage

1. **Prepare Your Directory**:
   - Drop the `cbz_to_pdf.py` script into the directory containing your `.cbz` or `.cbr` files.

2. **Set Permissions**:
   - Open a terminal and navigate to the directory where you placed the script.
   - Make the script executable by running:
     ```bash
     chmod +x cbz_to_pdf.py
     ```

3. **Run the Script**:
   - Execute the script by running:
     ```bash
     ./cbz_to_pdf.py
     ```

   This will process all `.cbz` and `.cbr` files in the directory, convert them to PDF, and move the original files to a folder called `old`.

## How It Works

1. **Directory Setup**:
   - The script starts by identifying the current directory and setting up an `old` directory where the original files will be moved after conversion.

2. **File Processing**:
   - The script scans the current directory for files with `.cbz` or `.cbr` extensions.
   - For each file, it identifies whether it is a CBZ (ZIP archive) or CBR (RAR archive).

3. **Conversion**:
   - For `.cbz` files, the script extracts images from the ZIP archive and combines them into a single PDF.
   - For `.cbr` files, it uses the `rarfile` library to extract images from the RAR archive and then converts them to PDF.

4. **Batch Processing**:
   - The script processes files in batches to manage memory usage and system resources effectively. After processing a batch, it pauses to free up resources before moving on to the next batch.

5. **Progress Bar**:
   - The script uses `tqdm` to display a progress bar while processing each file, providing visual feedback on the conversion status.

6. **File Management**:
   - After successfully converting a file, the script moves the original file to the `old` directory to keep the working directory organized.

## License

**This project is licensed under the MIT License. See the LICENSE file for details.**

## Troubleshooting

- **ModuleNotFoundError: No module named 'PIL':**
  Ensure you have installed the Pillow library. Using `pip`, you can install it with:
  ```bash
  pip install pillow
  ```
  Alternatively, on Arch Linux, use:
  ```bash
  sudo pacman -S python-pillow
  ```

- **ModuleNotFoundError: No module named 'rarfile':**
  Ensure you have installed the `rarfile` library. Using `pip`, you can install it with:
  ```bash
  pip install rarfile
  ```
  Alternatively, on Arch Linux, use:
  ```bash
  paru -S python-rarfile
  ```

- **ModuleNotFoundError: No module named 'tqdm':**
  Ensure you have installed the `tqdm` library. Using `pip`, you can install it with:
  ```bash
  pip install tqdm
  ```
  Alternatively, on Arch Linux, use:
  ```bash
  sudo pacman -S python-tqdm
  ```

- **Permission Denied:**
  Make sure you have executed the `chmod +x cbz_to_pdf.py` command before running the script.

