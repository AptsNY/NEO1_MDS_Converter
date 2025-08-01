# NEO1 MDS Converter

## Overview

The **NEO1 MDS Converter** is a powerful Python tool designed to transform American Express (Amex) expense CSV files into the MDS (Management Document System) invoice format for seamless upload and processing. This tool automates the conversion of expense data while maintaining data integrity and providing comprehensive receipt image management.

## 🚀 Features

### Core Functionality
- **CSV Transformation**: Converts Amex expense CSV files to MDS invoice format
- **Data Filtering**: Automatically filters out negative amounts (credits) and invalid transactions
- **Invoice Generation**: Creates unique invoice numbers and proper invoice descriptions
- **GL Code Mapping**: Preserves General Ledger account codes from source data
- **Date Handling**: Converts and formats transaction dates to MDS requirements

### Receipt Image Management
- **URL Extraction**: Extracts receipt image URLs from neo1.com
- **Batch Download**: Generates batch scripts for opening multiple receipt URLs
- **Auto-Detection**: Automatically detects and moves downloaded images to organized folders
- **Image Verification**: Verifies downloaded images and provides status reports
- **File Organization**: Organizes receipt images with consistent naming conventions

### User Experience
- **Interactive Menu**: User-friendly command-line interface with numbered file selection
- **Progress Tracking**: Real-time progress updates and status messages
- **Error Handling**: Comprehensive error handling with helpful error messages
- **Summary Reports**: Detailed processing summaries with transaction counts and amounts

## 📋 Prerequisites

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
pathlib (built-in)
hashlib (built-in)
datetime (built-in)
```

## 🛠️ Installation

### 1. Clone or Download the Repository
```bash
git clone https://github.com/yourusername/NEO1_MDS_Converter.git
cd NEO1_MDS_Converter
```

### 2. Install Python Dependencies
```bash
pip install pandas numpy requests
```

### 3. Configure Folder Paths
Edit the configuration section in `Amex processor.py`:

```python
# Configuration - UPDATE THESE PATHS FOR YOUR COMPUTER
INPUT_FOLDER = r"Input"  # Folder where Amex CSV files are stored
OUTPUT_FOLDER = r"Output"  # Folder where processed files will be saved
```

### 4. Create Required Folders
The script will automatically create these folders if they don't exist:
- `Input/` - Place your Amex CSV files here
- `Output/` - Processed MDS files will be saved here
- `Receipt_Images/` - Downloaded receipt images will be stored here

## 📖 Usage

### Quick Start

1. **Prepare Your Data**
   - Export your Amex expense data as a CSV file
   - Place the CSV file in the `Input/` folder

2. **Run the Converter**
   ```bash
   python "Amex processor.py"
   ```

3. **Select Your File**
   - Choose from the numbered list of available CSV files
   - The script will process your selection automatically

4. **Download Receipt Images**
   - Run the generated batch script to open receipt URLs
   - Download images to your Downloads folder
   - Use the auto-detection feature to organize images

### Detailed Workflow

#### Step 1: File Processing
```
🔄 AMEX FILE PROCESSING
========================
1. Load Amex CSV data
2. Filter positive transactions
3. Generate image download instructions
4. Transform to MDS format
5. Save processed file
```

#### Step 2: Image Management
```
📁 Image Download Workflow
==========================
1. Open neo1.com in your browser
2. Log into your account
3. Run the batch script (open_receipt_urls.bat)
4. Download all images to Downloads folder
5. Use auto-detection to move images to Receipt_Images folder
```

#### Step 3: MDS Upload
```
🎯 Ready for MDS Upload
=======================
1. Upload the processed CSV file to MDS
2. Upload the Receipt_Images folder to MDS
3. Verify all images are properly linked
```

### Menu Options

The main menu provides four options:

1. **Process Amex CSV file** - Main processing workflow
2. **Auto-detect and move downloaded images** - Organize downloaded images
3. **Verify downloaded images** - Check image download status
4. **Exit** - Close the application

## 📊 Input File Format

### Required CSV Columns
Your Amex CSV file must contain these columns:

| Column Name | Description | Required |
|-------------|-------------|----------|
| `Billing Total Gross Amount` | Transaction amount | ✅ |
| `Transaction Date` | Date of transaction | ✅ |
| `Vendor Name` | Name of the vendor | ✅ |
| `Description 1 (what the user types - typically purpose of expense)` | Expense description | ✅ |
| `Field 1 value code` | GL account code | ✅ |
| `Transaction Ref. ID` | Transaction reference ID | ❌ (optional) |
| `Image URL` | Receipt image URL | ❌ (optional) |

### Sample Input Data
```csv
Billing Total Gross Amount,Transaction Date,Vendor Name,Description 1 (what the user types - typically purpose of expense),Field 1 value code,Transaction Ref. ID,Image URL
125.50,2024-01-15,Office Supplies Co,Office supplies for Q1,4470,TXN123456,https://neo1.com/receipts/123456.png
89.99,2024-01-16,Restaurant ABC,Business lunch meeting,4470,TXN123457,https://neo1.com/receipts/123457.png
```

## 📤 Output Format

### MDS Invoice Structure
The processed file will contain these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `Unnamed: 0` | Sequential numbering | 1, 2, 3... |
| `Company Code` | Company identifier | BLM |
| `Vendor Account` | Vendor account code | AMEX |
| `Invoice Amount` | Transaction amount | 125.50 |
| `Invoice Number CRC32 Hash Input String` | Hash input for invoice number | TXN123456,2024-01-15 |
| `Invoice Number` | Unique 8-character hex invoice number | A1B2C3D4 |
| `Invoice Date MMDDYY` | Invoice date in MM/DD/YY format | 01/15/24 |
| `Due Date MMDDYY` | Due date (transaction date + 8 days) | 01/23/24 |
| `Invoice Description` | Vendor name and description | Office Supplies Co | Office supplies for Q1 |
| `GL Account 1` | General Ledger account code | 4470 |
| `GL Amount 1` | GL amount (same as invoice amount) | 125.50 |
| `Image File Spec` | Local image filename | 0001_TXN12345_receipt.png |

### Sample Output Data
```csv
Unnamed: 0,Company Code,Vendor Account,Invoice Amount,Invoice Number CRC32 Hash Input String,Invoice Number,Invoice Date MMDDYY,Due Date MMDDYY,Invoice Description,GL Account 1,GL Amount 1,Image File Spec
1,BLM,AMEX,125.50,"TXN123456,2024-01-15",A1B2C3D4,01/15/24,01/23/24,"Office Supplies Co | Office supplies for Q1",4470,125.50,0001_TXN12345_receipt.png
2,BLM,AMEX,89.99,"TXN123457,2024-01-16",E5F6G7H8,01/16/24,01/24/24,"Restaurant ABC | Business lunch meeting",4470,89.99,0002_TXN12346_receipt.png
```

## 🔧 Configuration

### Business Rules
The converter follows these business rules:

- **Vendor Account**: Always set to "AMEX" (paying Amex, not original vendor)
- **Company Code**: Set to "BLM"
- **GL Codes**: Preserved from Field 1 value code in source data
- **Invoice Descriptions**: Include real vendor name and expense purpose
- **Filtering**: Negative amounts (credits) are automatically filtered out
- **Due Date**: Transaction date + 8 days
- **Invoice Numbers**: Generated as 8-character hexadecimal hashes

### Customizable Settings
You can modify these settings in the `AmexToMDSTransformer` class:

```python
class AmexToMDSTransformer:
    def __init__(self):
        self.company_code = "BLM"           # Change company code
        self.vendor_account = "AMEX"        # Change vendor account
        self.due_date_offset_days = 8       # Change due date offset
        self.images_folder = "Receipt_Images"  # Change images folder name
```

## 📁 File Structure

```
NEO1_MDS_Converter/
├── Amex processor.py          # Main application file
├── README.md                  # This documentation file
├── Input/                     # Place Amex CSV files here
│   ├── amex_expenses_jan.csv
│   └── amex_expenses_feb.csv
├── Output/                    # Processed MDS files
│   ├── amex_expenses_jan_MDS_READY_20240115_143022.csv
│   ├── receipt_image_urls.txt
│   └── open_receipt_urls.bat
└── Receipt_Images/           # Downloaded receipt images
    ├── 0001_TXN12345_receipt.png
    ├── 0002_TXN12346_receipt.png
    └── ...
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Missing Required Columns
**Error**: `Missing required columns: ['Billing Total Gross Amount']`
**Solution**: Ensure your CSV file contains all required columns with exact names

#### 2. No Positive Transactions Found
**Error**: `WARNING: No positive transactions found after filtering!`
**Solution**: Check if your CSV contains positive amounts (not all credits)

#### 3. Image Download Issues
**Problem**: Images not downloading from neo1.com
**Solutions**:
- Ensure you're logged into neo1.com in your browser
- Check that the Image URL column contains valid URLs
- Try downloading images manually using the URLs file

#### 4. Permission Errors
**Error**: `Permission denied` when creating folders
**Solution**: Run the script with appropriate permissions or change folder paths

### Debug Mode
For detailed debugging, you can add logging to the script:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔒 Security Considerations

- **Data Privacy**: The tool processes financial data locally on your machine
- **No Data Transmission**: No data is sent to external servers
- **Local Storage**: All files are stored locally in your specified folders
- **Image URLs**: Receipt image URLs are from neo1.com (your expense management system)

## 🤝 Contributing

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

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

### Getting Help
- **Documentation**: Check this README file first
- **Issues**: Create an issue on GitHub for bugs or feature requests
- **Email**: Contact the development team for urgent issues

### Feature Requests
We welcome feature requests! Please include:
- Detailed description of the feature
- Use case or business need
- Sample data if applicable

## 🔄 Version History

### Version 1.0.0 (Current)
- Initial release
- Core CSV transformation functionality
- Receipt image management
- Interactive command-line interface
- Comprehensive error handling

### Planned Features
- Web-based interface
- Batch processing of multiple files
- Advanced GL code mapping
- Integration with other expense systems
- Automated MDS upload functionality

---

**Note**: This tool is specifically designed for converting Amex expense data to MDS format. Ensure your data source and target system are compatible before use. 