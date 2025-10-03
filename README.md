# NEO1 MDS Converter

## Overview

The **NEO1 MDS Converter** is a powerful Python tool designed to transform American Express (Amex) expense CSV files into the MDS (Management Document System) invoice format for seamless upload and processing. This tool automates the conversion of expense data while maintaining data integrity and providing comprehensive receipt image management with TIFF conversion for MDS compatibility.

## Features

### Core Functionality
- **CSV Transformation**: Converts Amex expense CSV files to MDS invoice format
- **Data Filtering**: Automatically filters out negative amounts (credits) and invalid transactions
- **Invoice Generation**: Creates unique invoice numbers and proper invoice descriptions
- **GL Code Tree Mapping**: Preserves General Ledger account codes (BA, BB, BC tree structure) from source data
- **Date Handling**: Converts and formats transaction dates to MDS requirements
- **Automated Workflow**: Complete end-to-end processing with minimal user intervention

### Receipt Image Management
- **URL Extraction**: Extracts receipt image URLs from neo1.com
- **Chrome Integration**: Uses Chrome with `--download-path` flag to download directly to Output folder
- **Smart Browser Detection**: Automatically finds Chrome, Edge, or Brave executable across all platforms
- **Multi-Directory Search**: Searches 20+ possible download locations across Windows/Mac/Linux
- **Windows Registry Integration**: Reads actual Windows Downloads folder from registry (handles custom locations)
- **PDF Conversion**: Converts all images to PDF format (MDS-compatible)
- **PDF Support**: Handles existing PDF receipts by copying them to output folder
- **Intelligent File Matching**: Finds files by exact filename (no time restrictions)
- **Image Verification**: Verifies downloaded images and provides status reports
- **File Organization**: Organizes receipt images with consistent naming conventions
- **Auto Cleanup**: Automatically removes batch files before exit (ready for email)

### User Experience
- **Streamlined 3-Step Workflow**: Process → Download → Verify
- **Interactive Menu**: User-friendly command-line interface with numbered file selection
- **Progress Tracking**: Real-time progress updates and status messages
- **Error Handling**: Comprehensive error handling with helpful error messages
- **Automatic Setup**: Creates required folders automatically on first run
- **Summary Reports**: Detailed processing summaries with transaction counts and amounts

## Prerequisites

### System Requirements
- **Python 3.7+** (recommended: Python 3.8 or higher)
- **Windows 10/11** (primary platform, may work on other systems)
- **Internet Connection** (for downloading receipt images from neo1.com)
- **Web Browser** (for accessing neo1.com and downloading images)

### Required Python Packages
```
pandas>=1.3.0
numpy>=1.21.0
requests>=2.25.0
Pillow>=9.0.0
```

## Installation

### 1. Clone or Download the Repository
```bash
git clone https://github.com/yourusername/NEO1_MDS_Converter.git
cd NEO1_MDS_Converter
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Folder Paths
Edit the configuration section in `amex_processor.py`:

```python
# Configuration - UPDATE THESE PATHS FOR YOUR COMPUTER
INPUT_FOLDER = r"Input"  # Folder where Amex CSV files are stored
OUTPUT_FOLDER = r"Output"  # Folder where processed files will be saved
```

### 4. Automatic Folder Setup
The script automatically creates required folders on first run:
- `Input/` - Place your Amex CSV files here
- `Output/` - Processed MDS files and images will be saved here

**No manual folder creation needed!** The script handles everything automatically.

## Usage

### Quick Start

1. **Prepare Your Data**
   - Export your Amex expense data as a CSV file
   - Place the CSV file in the `Input/` folder

2. **Run the Converter**
   ```bash
   python amex_processor.py
   ```

3. **Follow the 3-Step Workflow**
   - **Step 1**: Process CSV + Transform + Open Image URLs (Complete Workflow)
   - **Step 2**: Auto-detect, move, and convert images to TIFF format
   - **Step 3**: Verify downloaded images (Sanity Check)

### Detailed Workflow

#### Step 1: Complete Workflow
```
COMPLETE WORKFLOW: CSV + TRANSFORM + OPEN IMAGE URLs
============================================================
1. Load Amex CSV data
2. Filter positive transactions
3. Generate image download instructions and batch scripts
4. Transform to MDS format with proper GL code mapping
5. Save processed file (Image File Spec shows "PLACEHOLDER" until images are downloaded)
6. Automatically run batch script to open receipt URLs
```

#### Step 2: Image Processing
```
AUTO-DETECT, MOVE, AND CONVERT IMAGES TO PDF
==================================================
1. Search 20+ download directories (including Windows Registry locations)
2. Find images by exact filename (no time restrictions)
3. Move images to Output folder with UUID-based naming
4. Convert all images to PDF format for MDS compatibility
5. Handle existing PDF files by copying them to output folder
6. Update CSV with actual PDF filenames (replaces "PLACEHOLDER" with real filenames)
```

#### Step 3: Verification
```
VERIFY DOWNLOADED IMAGES (SANITY CHECK)
==========================================
1. Check which images have been successfully processed
2. Show summary of found vs missing images
3. Verify TIFF conversion completed successfully
```

### Menu Options

The main menu provides four options:

1. **Process CSV + Transform + Open Image URLs (Complete Workflow)** - Main processing workflow with Chrome integration
2. **Auto-detect, move, and convert images to PDF format** - Intelligent multi-directory search and PDF conversion
3. **Verify downloaded images (Sanity Check)** - Check image processing status
4. **Exit** - Clean up batch files and close the application

## Input File Format

### Required CSV Columns
Your Amex CSV file must contain these columns:

| Column Name | Description | Required | MDS Mapping |
|-------------|-------------|----------|-------------|
| `Billing Total Gross Amount` | Transaction amount | Yes | Invoice Amount |
| `Transaction Date` | Date of transaction | Yes | Invoice Date |
| `Vendor Name` | Name of the vendor | Yes | Invoice Description |
| `Description 1 (what the user types - typically purpose of expense)` | Expense description | Yes | Invoice Description |
| `Field 1 value code` | Parent GL code (BA) | Yes | GL Account BA |
| `Field 2 value code` | Child GL code 1 (BB) | Yes | GL Account BB |
| `Field 3 value code` | Child GL code 2 (BC) | Yes | GL Account BC |
| `Transaction Ref. ID` | Transaction reference ID | No (optional) | Invoice Number generation |
| `Image URL` | Receipt image URL | No (optional) | Image File Spec |

### Sample Input Data
```csv
Billing Total Gross Amount,Transaction Date,Vendor Name,Description 1 (what the user types - typically purpose of expense),Field 1 value code,Field 2 value code,Field 3 value code,Transaction Ref. ID,Image URL
125.50,2024-01-15,Office Supplies Co,Office supplies for Q1,4470,YONKERS/WESTCHESTER,ACESL,TXN123456,https://neo1.com/receipts/123456.png
89.99,2024-01-16,Restaurant ABC,Business lunch meeting,4470,YONKERS/WESTCHESTER,111B,TXN123457,https://neo1.com/receipts/123457.png
```

## Output Format

### MDS Invoice Structure
The processed file will contain these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `Unnamed: 0` | Sequential numbering | 1, 2, 3... |
| `Company Code` | Company identifier | BLM |
| `Vendor Account` | Vendor account code | AMEX911 |
| `Invoice Amount` | Transaction amount | 125.50 |
| `GL Amount 1` | GL amount (same as Invoice Amount) | 125.50 |
| `Invoice Number CRC32 Hash Input String` | Hash input for invoice number | TXN123456,2024-01-15 |
| `Invoice Number` | Unique 8-character hex invoice number | A1B2C3D4 |
| `Invoice Date MMDDYY` | Invoice date in MM/DD/YY format | 01/15/24 |
| `Due Date MMDDYY` | Due date (transaction date + 8 days) | 01/23/24 |
| `Invoice Description` | Vendor name and description | Office Supplies Co \| Office supplies for Q1 |
| `GL Account BA` | Parent GL account code | 4470 |
| `GL Account BB` | Child GL account code 1 | YONKERS/WESTCHESTER |
| `GL Account BC` | Child GL account code 2 | ACESL |
| `Image File Spec` | Local PDF image filename | PLACEHOLDER (before download), 0001_TXN12345_receipt.pdf (after download) |

### Sample Output Data

**After Step 1 (before images downloaded):**
```csv
Unnamed: 0,Company Code,Vendor Account,Invoice Amount,GL Amount 1,Invoice Number CRC32 Hash Input String,Invoice Number,Invoice Date MMDDYY,Due Date MMDDYY,Invoice Description,GL Account BA,GL Account BB,GL Account BC,Image File Spec
1,BLM,AMEX911,125.50,125.50,"TXN123456,2024-01-15",A1B2C3D4,01/15/24,01/23/24,"Office Supplies Co | Office supplies for Q1",4470,YONKERS/WESTCHESTER,ACESL,PLACEHOLDER
2,BLM,AMEX911,89.99,89.99,"TXN123457,2024-01-16",E5F6G7H8,01/16/24,01/24/24,"Restaurant ABC | Business lunch meeting",4470,YONKERS/WESTCHESTER,111B,PLACEHOLDER
```

**After Step 2 (images downloaded and converted):**
```csv
Unnamed: 0,Company Code,Vendor Account,Invoice Amount,GL Amount 1,Invoice Number CRC32 Hash Input String,Invoice Number,Invoice Date MMDDYY,Due Date MMDDYY,Invoice Description,GL Account BA,GL Account BB,GL Account BC,Image File Spec
1,BLM,AMEX911,125.50,125.50,"TXN123456,2024-01-15",A1B2C3D4,01/15/24,01/23/24,"Office Supplies Co | Office supplies for Q1",4470,YONKERS/WESTCHESTER,ACESL,0000_TXN12345_4f08ae18-fd91-4689-8d3e-a4f96b23cbdf.pdf
2,BLM,AMEX911,89.99,89.99,"TXN123457,2024-01-16",E5F6G7H8,01/16/24,01/24/24,"Restaurant ABC | Business lunch meeting",4470,YONKERS/WESTCHESTER,111B,0001_TXN12346_72fc4987-68e8-4ba9-afda-f8b2a2641722.pdf
```

## Configuration

### Business Rules
The converter follows these business rules:

- **Vendor Account**: Always set to "AMEX911" (paying Amex, not original vendor)
- **Company Code**: Set to "BLM"
- **GL Code Tree**: Preserves Field 1, 2, 3 value codes as BA, BB, BC tree structure
- **Invoice Descriptions**: Include real vendor name and expense purpose
- **Filtering**: Negative amounts (credits) are automatically filtered out
- **Due Date**: Transaction date + 8 days
- **Invoice Numbers**: Generated as 8-character hexadecimal hashes
- **Image Format**: All images converted to PDF format for MDS compatibility
- **Download Method**: Chrome browser with `--download-path` for direct Output folder delivery

### Customizable Settings
You can modify these settings in the `AmexToMDSTransformer` class:

```python
class AmexToMDSTransformer:
    def __init__(self):
        self.company_code = "BLM"           # Change company code
        self.vendor_account = "AMEX911"     # Change vendor account
        self.due_date_offset_days = 8       # Change due date offset
        self.images_folder = "Output"  # Images go directly in Output folder
```

## File Structure

```
NEO1_MDS_Converter/
├── amex_processor.py          # Main application file
├── README.md                  # This documentation file
├── requirements.txt           # Python dependencies
├── Input/                     # Place Amex CSV files here
│   ├── amex_expenses_jan.csv
│   └── amex_expenses_feb.csv
└── Output/                   # Processed CSV and receipt images (created automatically)
    ├── amex_expenses_jan_MDS_READY_20240115_143022.csv
    ├── 0001_TXN12345_receipt.pdf
    ├── 0002_TXN12346_receipt.pdf
    └── [other PDF images]  # All images in same directory as CSV
    # Note: Batch files are auto-deleted on exit (Option 4)
```

## Troubleshooting

### Common Issues

#### 1. Missing Required Columns
**Error**: `Missing required columns: ['Field 1 value code', 'Field 2 value code', 'Field 3 value code']`
**Solution**: Ensure your CSV file contains all required GL code columns with exact names

#### 2. No Positive Transactions Found
**Error**: `WARNING: No positive transactions found after filtering!`
**Solution**: Check if your CSV contains positive amounts (not all credits)

#### 3. Image Download Issues
**Problem**: Images not downloading from neo1.com
**Solutions**:
- Ensure you're logged into neo1.com in your browser
- Check that the Image URL column contains valid URLs
- The batch script should automatically open URLs in your browser

#### 4. PDF Conversion Issues
**Problem**: Images not converting to PDF format
**Solutions**:
- Ensure Pillow library is installed: `pip install Pillow>=9.0.0`
- Check that images were successfully downloaded and moved
- Verify file permissions for the Output folder

#### 5. Custom Downloads Folder Not Found
**Problem**: Files not found even though they were downloaded
**Solutions**:
- The script now reads Windows Registry for actual Downloads location
- Searches 20+ possible download directories automatically
- Check console output to see which directories are being searched
- If still not found, files may be in an unexpected location

#### 6. Batch Script Not Running
**Problem**: Batch script fails to download images
**Solutions**:
- Ensure Chrome, Edge, or Brave browser is installed
- Check that you're logged into neo1.com in your browser
- Script automatically detects browser executable
- If Chrome not found, falls back to default browser
- Check console output to see which browser is being used

### Debug Mode
For detailed debugging, you can add logging to the script:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- **Data Privacy**: The tool processes financial data locally on your machine
- **No Data Transmission**: No data is sent to external servers
- **Local Storage**: All files are stored locally in your specified folders
- **Image URLs**: Receipt image URLs are from neo1.com (your expense management system)

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly with sample data
5. Submit a pull request

### Code Style
- Follow PEP 8 Python style guidelines
- Add comments for complex logic
- Include docstrings for all functions
- Test with various CSV formats

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

### Getting Help
- **Documentation**: Check this README file first
- **Issues**: Create an issue on GitHub for bugs or feature requests
- **Email**: Contact the development team for urgent issues

### Feature Requests
We welcome feature requests! Please include:
- Detailed description of the feature
- Use case or business need
- Sample data if applicable

## Version History

### Version 3.1.0 (Current)
- **PLACEHOLDER Fix**: Image File Spec now shows "PLACEHOLDER" instead of misleading filenames before download
- **Clear Status Indication**: Immediately visible which images haven't been downloaded yet
- **UUID-Based Filenames**: Actual downloaded files use UUID-based naming for uniqueness

### Version 3.0.0
- **Chrome Integration**: Direct downloads to Output folder using `--download-path` flag
- **Smart Browser Detection**: Automatic Chrome/Edge/Brave executable detection across all platforms
- **Windows Registry Support**: Reads actual Downloads folder location from Windows Registry
- **Multi-Directory Search**: Searches 20+ possible download locations (Windows/Mac/Linux)
- **Intelligent File Matching**: Finds files by exact filename without time restrictions
- **PDF Conversion**: Converts all images to PDF format for MDS compatibility
- **Auto Cleanup**: Removes batch files on exit for email-ready output
- **Cross-Platform**: Full support for Windows, macOS, and Linux

### Version 2.0.0
- **Major Update**: Complete workflow automation
- **GL Code Tree Mapping**: Proper BA, BB, BC tree structure support
- **TIFF Conversion**: Automatic image conversion to MDS-preferred format
- **Automated Batch Scripts**: Automatic URL opening in browser
- **Streamlined Workflow**: 3-step process for maximum efficiency
- **PDF Support**: Handles PDF receipts alongside images
- **Enhanced Error Handling**: Better error messages and troubleshooting

### Version 1.0.0
- Initial release
- Core CSV transformation functionality
- Basic receipt image management
- Interactive command-line interface

### Planned Features
- Web-based interface
- Batch processing of multiple files
- Advanced GL code validation
- Integration with other expense systems
- Automated MDS upload functionality

---

**Note**: This tool is specifically designed for converting Amex expense data to MDS format with proper GL code tree structure. Ensure your data source and target system are compatible before use.