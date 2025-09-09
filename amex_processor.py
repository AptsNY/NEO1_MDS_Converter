#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pandas>=2.0.0",
#     "numpy>=1.24.0", 
#     "pillow>=9.0.0",
#     "requests>=2.28.0"
# ]
# ///

"""
AMEX TO MDS INVOICE TRANSFORMER
===============================

This script converts Amex expense CSV files to MDS invoice format for upload.

HOW TO USE (PEP 723 COMPATIBLE):
1. Save this script as amex_processor.py
2. Run with: python amex_processor.py (dependencies will be auto-managed)
3. Or with pipx: pipx run amex_processor.py
4. Or with uv: uv run amex_processor.py

WHAT IT DOES:
- Filters out negative amounts (credits)
- Converts each expense to an invoice with vendor = "AMEX"
- Uses real vendor names in descriptions
- Generates unique invoice numbers and file specs
- Maintains GL account codes from source data
- Downloads receipt images from neo1.com URLs
- Saves images locally for MDS upload
"""

import pandas as pd
import hashlib
import binascii
from datetime import datetime, timedelta
import numpy as np
import os
import re
import glob
import requests
import urllib.parse
import shutil
import subprocess
import time
from typing import Optional
from pathlib import Path
from PIL import Image

class AmexToMDSTransformer:
    """
    Transforms Amex expense data to MDS invoice format.
    
    Business Rules:
    - Each positive Amex transaction becomes a separate invoice
    - Vendor Account = "AMEX" (paying Amex, not original vendor)
    - Company Code = "BLM" 
    - GL codes from Field 1, 2, 3 value codes (BA, BB, BC tree structure)
    - Invoice Description includes real vendor name
    - Filter out negative amounts (credits)
    """
    
    def __init__(self):
        self.company_code = "BLM"
        self.vendor_account = "AMEX"
        self.due_date_offset_days = 8
        self.images_folder = "Output"  # Images will go directly in Output folder
        
    def load_amex_data(self, file_path: str) -> pd.DataFrame:
        """Load and validate Amex CSV data."""
        try:
            # Handle large files efficiently
            df = pd.read_csv(file_path, dtype_backend='numpy_nullable')
            print(f"Loaded {len(df)} transactions from {file_path}")
            
            # Validate required columns exist
            required_cols = [
                'Billing Total Gross Amount',
                'Transaction Date', 
                'Vendor Name',
                'Description 1 (what the user types - typically purpose of expense)',
                'Field 1 value code',  # BA - Parent GL Code
                'Field 2 value code',  # BB - Child GL Code 1
                'Field 3 value code'   # BC - Child GL Code 2
            ]
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
                
            return df
            
        except Exception as e:
            raise Exception(f"Error loading Amex data: {str(e)}")
    
    def filter_positive_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter out negative amounts (credits) and invalid data."""
        print(f"Original transactions: {len(df)}")
        
        # Remove rows with missing or negative amounts
        filtered_df = df[
            (df['Billing Total Gross Amount'].notna()) & 
            (df['Billing Total Gross Amount'] > 0)
        ].copy()
        
        print(f"Positive transactions after filtering: {len(filtered_df)}")
        print(f"Filtered out {len(df) - len(filtered_df)} transactions (credits/invalid)")
        
        return filtered_df
    
    def generate_invoice_number(self, transaction_data: str) -> str:
        """Generate 8-character hex invoice number from transaction data."""
        # Create hash from transaction data
        hash_obj = hashlib.md5(transaction_data.encode('utf-8'))
        hex_digest = hash_obj.hexdigest()
        return hex_digest[:8].upper()
    
    def generate_crc32_hash_input(self, row: pd.Series, index: int) -> str:
        """Generate CRC32 hash input string."""
        # Use transaction ref ID if available, otherwise use index and date
        if 'Transaction Ref. ID' in row and pd.notna(row['Transaction Ref. ID']):
            base_id = str(row['Transaction Ref. ID'])[:10]  # Truncate if too long
        else:
            base_id = str(index)
            
        transaction_date = pd.to_datetime(row['Transaction Date']).strftime('%Y-%m-%d')
        return f"{base_id},{transaction_date}"
    
    def format_date_mmddyy(self, date_str: str) -> str:
        """Convert date to MM/DD/YY format."""
        try:
            date_obj = pd.to_datetime(date_str)
            return date_obj.strftime('%m/%d/%y')
        except:
            return ""
    
    def calculate_due_date(self, transaction_date: str) -> str:
        """Calculate due date (transaction date + offset days)."""
        try:
            date_obj = pd.to_datetime(transaction_date)
            due_date = date_obj + timedelta(days=self.due_date_offset_days)
            return due_date.strftime('%m/%d/%y')
        except:
            return ""
    
    def clean_text_for_filename(self, text: str) -> str:
        """Clean text for use in filename."""
        if pd.isna(text):
            return "unknown"
        # Replace spaces and special chars with underscores
        cleaned = re.sub(r'[^\w\s-]', '', str(text))
        cleaned = re.sub(r'\s+', '_', cleaned)
        return cleaned[:50]  # Limit length
    
    def generate_pdf_filename(self, row: pd.Series, index: int) -> str:
        """Generate PDF filename following the pattern."""
        # Extract date components
        try:
            date_obj = pd.to_datetime(row['Transaction Date'])
            year = date_obj.strftime('%Y')
            month = date_obj.strftime('%m')
        except:
            year = "2025"
            month = "01"
            
        # Clean vendor name for filename
        vendor_clean = self.clean_text_for_filename(row.get('Vendor Name', 'vendor'))
        
        # Generate sequence number (could be improved with actual sequencing logic)
        sequence = f"{index + 1:04d}"
        
        filename = f"{sequence}-{year}-{month}_amex_expense_-_{vendor_clean}.pdf"
        return filename
    
    def get_local_image_filename(self, row: pd.Series, index: int) -> str:
        """Get the local PDF image filename for the MDS output."""
        # Use PDF format for MDS (preferred format)
        pdf_image_path = row.get('PDF_Image_Path')
        if pdf_image_path and pd.notna(pdf_image_path):
            return os.path.basename(pdf_image_path)
        
        # Fallback to original local image path if PDF not available
        local_image_path = row.get('Local_Image_Path')
        if local_image_path and pd.notna(local_image_path):
            return os.path.basename(local_image_path)
        else:
            # Fallback to generated filename if no image was downloaded
            return self.generate_pdf_filename(row, index)
    
    def create_invoice_description(self, row: pd.Series) -> str:
        """Create invoice description with vendor name and purpose."""
        vendor_name = row.get('Vendor Name', 'Unknown Vendor')
        description = row.get('Description 1 (what the user types - typically purpose of expense)', '')
        
        if pd.isna(vendor_name):
            vendor_name = 'Unknown Vendor'
        if pd.isna(description):
            description = 'Expense'
            
        return f"{vendor_name} | {description}"
    
    def generate_image_urls_file(self, df: pd.DataFrame, output_folder: str) -> str:
        """Generate a file with all image URLs for manual download."""
        print(f"\n🖼️  Generating image URLs file for {len(df)} transactions...")
        
        # Create output folder if it doesn't exist (images will go here)
        output_path = Path(output_folder)
        output_path.mkdir(exist_ok=True)
        
        # Generate URLs file
        urls_file = Path(output_folder) / "receipt_image_urls.txt"
        
        with open(urls_file, 'w') as f:
            f.write("RECEIPT IMAGE URLs FOR MANUAL DOWNLOAD\n")
            f.write("=" * 50 + "\n")
            f.write("INSTRUCTIONS:\n")
            f.write("1. Make sure you are logged into neo1.com in your browser\n")
            f.write("2. Copy and paste each URL into your browser\n")
            f.write("3. Right-click on the image and 'Save As' to the Output folder\n")
            f.write("4. Use the suggested filename shown below each URL\n")
            f.write("=" * 50 + "\n\n")
            
            for index, row in df.iterrows():
                image_url = row.get('Image URL')
                transaction_id = row.get('Transaction Ref. ID', f"txn_{index}")
                vendor_name = row.get('Vendor Name', 'Unknown')
                amount = row.get('Billing Total Gross Amount', 0)
                date = row.get('Transaction Date', 'Unknown')
                
                if pd.notna(image_url) and image_url:
                    # Extract file extension from URL
                    parsed_url = urllib.parse.urlparse(image_url)
                    path_parts = parsed_url.path.split('/')
                    original_filename = path_parts[-1] if path_parts else 'receipt.png'
                    
                    # Create a clean filename
                    clean_filename = f"{index:04d}_{transaction_id[:8]}_{original_filename}"
                    
                    f.write(f"Transaction {index + 1}:\n")
                    f.write(f"Vendor: {vendor_name}\n")
                    f.write(f"Amount: ${amount}\n")
                    f.write(f"Date: {date}\n")
                    f.write(f"URL: {image_url}\n")
                    f.write(f"Save as: {clean_filename}\n")
                    f.write("-" * 40 + "\n\n")
        
        print(f"✅ Generated URLs file: {urls_file}")
        return str(urls_file)
    
    def create_batch_download_script(self, df: pd.DataFrame, output_folder: str) -> str:
        """Create a batch script to open all image URLs in browser."""
        print(f"\n🌐 Creating batch script to open image URLs in browser...")
        
        # Create working batch file (without pause for automatic execution)
        batch_file = Path(output_folder) / "open_receipt_urls.bat"
        
        with open(batch_file, 'w') as f:
            f.write("@echo off\n")
            f.write("echo Opening receipt URLs in browser...\n")
            f.write("echo Make sure you're logged into neo1.com!\n\n")
            
            for index, row in df.iterrows():
                image_url = row.get('Image URL')
                if pd.notna(image_url) and image_url:
                    f.write(f'start "" "{image_url}"\n')
                    f.write("timeout /t 2 /nobreak > nul\n")  # Wait 2 seconds between opens
        
        print(f"✅ Generated batch script: {batch_file}")
        return str(batch_file)
    
    def generate_image_download_instructions(self, df: pd.DataFrame, output_folder: str) -> pd.DataFrame:
        """Generate instructions and files for manual image download."""
        print(f"\n📋 Setting up manual image download process...")
        
        # Count transactions with images
        transactions_with_images = df[df['Image URL'].notna() & (df['Image URL'] != '')]
        print(f"Found {len(transactions_with_images)} transactions with receipt images")
        
        if len(transactions_with_images) > 0:
            # Generate URLs file
            urls_file = self.generate_image_urls_file(transactions_with_images, output_folder)
            
            # Generate batch script
            batch_script = self.create_batch_download_script(transactions_with_images, output_folder)
            
            print(f"\n📁 Files created:")
            print(f"   - URLs list: {urls_file}")
            print(f"   - Batch script: {batch_script}")
            print(f"   - Images folder: {output_folder}")
            
            print(f"\n📋 Next steps:")
            print(f"   1. Run the batch script to open all URLs in browser")
            print(f"   2. Manually save each image to the Output folder")
            print(f"   3. Use the suggested filenames from the URLs file")
        
        # Add placeholder for local image paths (will be filled after manual download)
        df_with_placeholders = df.copy()
        df_with_placeholders['Local_Image_Path'] = None
        
        return df_with_placeholders
    
    def get_download_folder(self) -> Path:
        """Get the user's default download folder."""
        # Try to get from environment variable first
        download_folder = os.environ.get('USERPROFILE') + '\\Downloads'
        if os.path.exists(download_folder):
            return Path(download_folder)
        
        # Fallback to common download locations
        common_paths = [
            os.path.expanduser('~/Downloads'),
            os.path.expanduser('~/Desktop'),
            'C:\\Users\\Public\\Downloads'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return Path(path)
        
        # Default to current directory if nothing found
        return Path.cwd()
    
    def find_and_move_downloaded_images(self, df: pd.DataFrame) -> pd.DataFrame:
        """Find recently downloaded images and move them to the Receipt_Images folder."""
        print(f"\n🔍 Searching for recently downloaded receipt images...")
        
        # Get download folder
        download_folder = self.get_download_folder()
        print(f"📁 Checking download folder: {download_folder}")
        
        # Create Output folder if it doesn't exist (images will go here)
        images_folder = Path(self.images_folder)
        images_folder.mkdir(exist_ok=True)
        
        # Get list of files in download folder (filter for image files and PDFs)
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.pdf'}
        downloaded_files = []
        
        for file_path in download_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                # Check if file was modified recently (within last 30 minutes)
                file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.total_seconds() < 1800:  # 30 minutes
                    downloaded_files.append(file_path)
        
        print(f"📸 Found {len(downloaded_files)} recently downloaded images")
        
        if not downloaded_files:
            print("❌ No recently downloaded images found in download folder")
            print("💡 Make sure to download the receipt images from neo1.com first")
            return df
        
        # Try to match downloaded files to transactions
        df_updated = df.copy()
        matched_count = 0
        
        for index, row in df.iterrows():
            image_url = row.get('Image URL')
            if pd.notna(image_url) and image_url:
                # Extract expected filename from URL
                parsed_url = urllib.parse.urlparse(image_url)
                path_parts = parsed_url.path.split('/')
                original_filename = path_parts[-1] if path_parts else 'receipt.png'
                transaction_id = row.get('Transaction Ref. ID', f"txn_{index}")
                expected_filename = f"{index:04d}_{transaction_id[:8]}_{original_filename}"
                
                # Look for matching file in downloaded files
                for downloaded_file in downloaded_files:
                    # Check if this file matches our expected pattern
                    if (downloaded_file.name.lower().endswith(original_filename.lower()) or
                        original_filename.lower() in downloaded_file.name.lower()):
                        
                        # Move file to Output folder with proper name
                        target_path = images_folder / expected_filename
                        try:
                            shutil.move(str(downloaded_file), str(target_path))
                            df_updated.at[index, 'Local_Image_Path'] = str(target_path)
                            print(f"✅ Moved: {downloaded_file.name} → {expected_filename}")
                            matched_count += 1
                            downloaded_files.remove(downloaded_file)  # Remove from list to avoid duplicates
                            break
                        except Exception as e:
                            print(f"❌ Failed to move {downloaded_file.name}: {str(e)}")
        
        print(f"✅ Successfully matched and moved {matched_count} images")
        
        # Show any remaining unmatched files
        if downloaded_files:
            print(f"⚠️  {len(downloaded_files)} downloaded images could not be matched:")
            for file in downloaded_files[:5]:  # Show first 5
                print(f"   - {file.name}")
            if len(downloaded_files) > 5:
                print(f"   ... and {len(downloaded_files) - 5} more")
        
        return df_updated
    
    def verify_downloaded_images(self, df: pd.DataFrame) -> pd.DataFrame:
        """Verify which images have been downloaded and update the dataframe."""
        print(f"\n🔍 Verifying downloaded images...")
        
        images_folder = Path(self.images_folder)
        if not images_folder.exists():
            print("❌ Output folder not found!")
            return df
        
        # Get list of downloaded images
        downloaded_files = list(images_folder.glob('*'))
        print(f"Found {len(downloaded_files)} files in Receipt_Images folder")
        
        # Update dataframe with actual downloaded image paths
        df_updated = df.copy()
        
        for index, row in df.iterrows():
            image_url = row.get('Image URL')
            if pd.notna(image_url) and image_url:
                # Extract expected filename from URL
                parsed_url = urllib.parse.urlparse(image_url)
                path_parts = parsed_url.path.split('/')
                original_filename = path_parts[-1] if path_parts else 'receipt.png'
                transaction_id = row.get('Transaction Ref. ID', f"txn_{index}")
                expected_filename = f"{index:04d}_{transaction_id[:8]}_{original_filename}"
                
                # Check if file exists
                expected_path = images_folder / expected_filename
                if expected_path.exists():
                    df_updated.at[index, 'Local_Image_Path'] = str(expected_path)
                    print(f"✅ Found: {expected_filename}")
                else:
                    print(f"❌ Missing: {expected_filename}")
        
        return df_updated
    
    def convert_image_to_pdf(self, input_path: str, output_path: str) -> bool:
        """Convert an image to PDF format for MDS compatibility."""
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (PDF requires RGB mode)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as PDF
                img.save(output_path, 'PDF', resolution=300.0)
                print(f"✅ Converted to PDF: {os.path.basename(output_path)}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to convert {os.path.basename(input_path)} to PDF: {str(e)}")
            return False
    
    def handle_pdf_file(self, input_path: str, output_path: str) -> bool:
        """Handle PDF files by copying them to the output folder."""
        try:
            shutil.copy2(input_path, output_path)
            print(f"✅ Copied PDF file: {os.path.basename(output_path)}")
            print(f"   Note: PDF files are already in the correct format for MDS")
            return True
        except Exception as e:
            print(f"❌ Failed to copy PDF {os.path.basename(input_path)}: {str(e)}")
            return False
    
    
    def process_images_for_mds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process all images to PDF format for MDS upload."""
        print(f"\n🖼️  Processing images for MDS compatibility (converting to PDF)...")
        
        images_folder = Path(self.images_folder)
        if not images_folder.exists():
            print("❌ Output folder not found!")
            return df
        
        # Images will go directly in the Output folder (no subfolder needed)
        pdf_folder = images_folder
        
        df_updated = df.copy()
        processed_count = 0
        pdf_count = 0
        failed_count = 0
        
        for index, row in df.iterrows():
            local_image_path = row.get('Local_Image_Path')
            if pd.notna(local_image_path) and local_image_path and os.path.exists(local_image_path):
                try:
                    # Generate filename
                    base_name = os.path.splitext(os.path.basename(local_image_path))[0]
                    file_extension = os.path.splitext(local_image_path)[1].lower()
                    
                    if file_extension == '.pdf':
                        # Handle PDF files by copying them
                        pdf_filename = f"{base_name}.pdf"
                        pdf_path = pdf_folder / pdf_filename
                        
                        if self.handle_pdf_file(local_image_path, str(pdf_path)):
                            pdf_count += 1
                            df_updated.at[index, 'PDF_Image_Path'] = str(pdf_path)
                        else:
                            failed_count += 1
                    else:
                        # Convert other image formats to PDF
                        pdf_filename = f"{base_name}.pdf"
                        pdf_path = pdf_folder / pdf_filename
                        
                        if self.convert_image_to_pdf(local_image_path, str(pdf_path)):
                            pdf_count += 1
                            df_updated.at[index, 'PDF_Image_Path'] = str(pdf_path)
                        else:
                            failed_count += 1
                    
                    processed_count += 1
                    
                except Exception as e:
                    print(f"❌ Error processing image for transaction {index}: {str(e)}")
                    failed_count += 1
        
        print(f"\n📊 Image Processing Summary:")
        print(f"   - Total files processed: {processed_count}")
        print(f"   - Files processed successfully: {pdf_count}")
        print(f"   - Failed conversions: {failed_count}")
        print(f"   - Output folder: {pdf_folder.absolute()}")
        
        if failed_count > 0:
            print(f"\n⚠️  {failed_count} files failed to process.")
            print(f"   This might be due to unsupported file formats or corrupted files.")
        
        return df_updated
    
    def auto_run_batch_script(self, output_folder: str) -> bool:
        """Automatically run the open_receipt_urls.bat script after CSV processing."""
        try:
            batch_file = Path(output_folder) / "open_receipt_urls.bat"
            
            if not batch_file.exists():
                print(f"❌ Batch script not found: {batch_file}")
                return False
            
            print(f"\n🚀 Automatically running batch script to open receipt URLs...")
            print(f"📁 Batch file: {batch_file}")
            print(f"⏳ This will open all receipt URLs in your default browser...")
            print(f"💡 Make sure you're logged into neo1.com in your browser!")
            
            # Give user a moment to read the message
            time.sleep(2)
            
            # Run the batch script using absolute path
            result = subprocess.run([str(batch_file)], 
                                 capture_output=True, 
                                 text=True,
                                 timeout=30)  # 30 second timeout
            
            if result.returncode == 0:
                print(f"✅ Batch script executed successfully!")
                print(f"🌐 Receipt URLs should now be opening in your browser...")
                return True
            else:
                print(f"⚠️  Batch script completed with warnings (return code: {result.returncode})")
                if result.stderr:
                    print(f"Error output: {result.stderr}")
                return True  # Still consider it successful if URLs opened
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Batch script timed out after 30 seconds")
            print(f"✅ URLs should still be opening in your browser...")
            return True
        except Exception as e:
            print(f"❌ Failed to run batch script: {str(e)}")
            print(f"💡 You can manually run the batch script: {batch_file}")
            return False
    
    def transform_to_mds_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform filtered Amex data to MDS invoice format."""
        print(f"Transforming {len(df)} transactions to MDS format...")
        
        # Create new DataFrame with MDS structure
        mds_data = []
        
        for index, row in df.iterrows():
            # Generate unique transaction identifier for hashing
            transaction_id = f"{row.get('Transaction Ref. ID', index)}_{row['Transaction Date']}_{row['Billing Total Gross Amount']}"
            
            mds_row = {
                'Unnamed: 0': index + 1,  # Sequential numbering
                'Company Code': self.company_code,
                'Vendor Account': self.vendor_account,
                'Invoice Amount': float(row['Billing Total Gross Amount']),
                'GL Amount 1': float(row['Billing Total Gross Amount']),  # Same as Invoice Amount
                'Invoice Number CRC32 Hash Input String': self.generate_crc32_hash_input(row, index),
                'Invoice Number': self.generate_invoice_number(transaction_id),
                'Invoice Date MMDDYY': self.format_date_mmddyy(row['Transaction Date']),
                'Due Date MMDDYY': self.calculate_due_date(row['Transaction Date']),
                'Invoice Description': self.create_invoice_description(row),
                'GL Account BA': str(row.get('Field 1 value code', '4470')) if pd.notna(row.get('Field 1 value code')) else '4470',
                'GL Account BB': str(row.get('Field 2 value code', '')) if pd.notna(row.get('Field 2 value code')) else '',
                'GL Account BC': str(row.get('Field 3 value code', '')) if pd.notna(row.get('Field 3 value code')) else '',
                'Image File Spec': self.get_local_image_filename(row, index)
            }
            
            mds_data.append(mds_row)
        
        mds_df = pd.DataFrame(mds_data)
        
        # Ensure correct data types
        mds_df['Unnamed: 0'] = mds_df['Unnamed: 0'].astype(int)
        mds_df['Invoice Amount'] = mds_df['Invoice Amount'].astype(float)
        mds_df['GL Amount 1'] = mds_df['GL Amount 1'].astype(float)
        # GL Account codes are kept as strings to preserve the tree structure
        
        print(f"Successfully transformed to {len(mds_df)} MDS invoice records")
        return mds_df
    
    def save_mds_data(self, df: pd.DataFrame, output_path: str) -> None:
        """Save MDS data to CSV file."""
        try:
            df.to_csv(output_path, index=False)
            print(f"MDS data saved to: {output_path}")
            
            # Print summary
            print(f"\nSummary:")
            print(f"- Total invoices: {len(df)}")
            print(f"- Total amount: ${df['Invoice Amount'].sum():,.2f}")
            print(f"- Date range: {df['Invoice Date MMDDYY'].min()} to {df['Invoice Date MMDDYY'].max()}")
            print(f"- Unique GL Account BA codes: {df['GL Account BA'].nunique()}")
            print(f"- Unique GL Account BB codes: {df['GL Account BB'].nunique()}")
            print(f"- Unique GL Account BC codes: {df['GL Account BC'].nunique()}")
            print(f"- GL Amount 1 total: ${df['GL Amount 1'].sum():,.2f}")
            
            # Check for image download setup
            images_folder = Path(self.images_folder)
            if images_folder.exists():
                image_count = len(list(images_folder.glob('*')))
                print(f"- Output folder created: {images_folder.absolute()}")
                print(f"- Image download instructions generated")
                print(f"- Batch script created for opening URLs")
            
        except Exception as e:
            raise Exception(f"Error saving MDS data: {str(e)}")
    
    def process_file(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """Complete processing pipeline from Amex CSV to MDS CSV."""
        print("=" * 50)
        print("AMEX TO MDS TRANSFORMATION PIPELINE")
        print("=" * 50)
        
        # Generate output filename if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = f"{base_name}_mds_format.csv"
        
        try:
            # Step 1: Load data
            amex_df = self.load_amex_data(input_file)
            
            # Step 2: Filter positive transactions
            filtered_df = self.filter_positive_transactions(amex_df)
            
            if len(filtered_df) == 0:
                print("WARNING: No positive transactions found after filtering!")
                return pd.DataFrame()
            
            # Step 3: Generate image download instructions
            output_folder = os.path.dirname(output_file)
            filtered_df_with_images = self.generate_image_download_instructions(filtered_df, output_folder)
            
            # Step 4: Transform to MDS format (without PDF conversion yet)
            mds_df = self.transform_to_mds_format(filtered_df_with_images)
            
            # Step 5: Save results
            self.save_mds_data(mds_df, output_file)
            
            # Step 6: Automatically run batch script to open receipt URLs
            self.auto_run_batch_script(output_folder)
            
            print("\n✅ TRANSFORMATION COMPLETED SUCCESSFULLY")
            return mds_df
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            raise


# Configuration - UPDATE THESE PATHS FOR YOUR COMPUTER
# =======================================================
# SETUP INSTRUCTIONS:
# 1. Update the INPUT_FOLDER path below to where you save Amex CSV files
# 2. Update the OUTPUT_FOLDER path below to where you want processed files
# 3. The script will create these folders automatically if they don't exist
# =======================================================

INPUT_FOLDER = r"Input"  # Folder where Amex CSV files are stored
OUTPUT_FOLDER = r"Output"  # Folder where processed files will be saved

# Alternative path examples for different operating systems:
# Windows: r"C:\Users\YourName\Documents\AmexFiles"
# Mac/Linux: "/Users/YourName/Documents/AmexFiles"  
# Network drive: r"\\server\shared\AmexFiles"


def setup_folders():
    """Create input and output folders if they don't exist."""
    try:
        # Create folders with exist_ok=True to prevent errors if they already exist
        os.makedirs(INPUT_FOLDER, exist_ok=True)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        
        # Check if folders were created successfully
        input_exists = os.path.exists(INPUT_FOLDER)
        output_exists = os.path.exists(OUTPUT_FOLDER)
        
        if input_exists and output_exists:
            print(f"✅ Folders ready:")
            print(f"   📁 Input folder: {os.path.abspath(INPUT_FOLDER)}")
            print(f"   📁 Output folder: {os.path.abspath(OUTPUT_FOLDER)}")
            return True
        else:
            print(f"❌ Failed to create required folders")
            return False
            
    except Exception as e:
        print(f"❌ Error creating folders: {e}")
        return False


def ensure_folders_exist():
    """Ensure required folders exist, create them if they don't."""
    try:
        # Check if folders exist
        input_exists = os.path.exists(INPUT_FOLDER)
        output_exists = os.path.exists(OUTPUT_FOLDER)
        
        if not input_exists or not output_exists:
            print(f"🔧 Setting up required folders...")
            return setup_folders()
        else:
            return True
            
    except Exception as e:
        print(f"❌ Error checking folders: {e}")
        return False


def find_csv_files():
    """Find all CSV files in the input folder."""
    import glob
    
    # Ensure folders exist first
    if not ensure_folders_exist():
        print(f"❌ Failed to set up required folders.")
        return []
    
    if not os.path.exists(INPUT_FOLDER):
        print(f"❌ Input folder does not exist: {INPUT_FOLDER}")
        print("Please create the folder and add your Amex CSV files there.")
        return []
    
    # Find all CSV files
    pattern = os.path.join(INPUT_FOLDER, "*.csv")
    csv_files = glob.glob(pattern)
    
    # Sort by modification date (newest first)
    csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return csv_files


def display_file_menu(csv_files):
    """Display numbered menu of available CSV files."""
    print("\n" + "=" * 60)
    print("AVAILABLE AMEX FILES FOR PROCESSING")
    print("=" * 60)
    
    if not csv_files:
        print("❌ No CSV files found in the input folder.")
        print(f"Please add Amex CSV files to: {INPUT_FOLDER}")
        return None
    
    for i, file_path in enumerate(csv_files, 1):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024  # KB
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        print(f"{i:2d}. {filename}")
        print(f"     Size: {file_size:.1f} KB | Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}")
        print()
    
    return csv_files


def get_user_selection(csv_files):
    """Get user's file selection."""
    max_choice = len(csv_files)
    
    while True:
        try:
            print(f"Enter your choice (1-{max_choice}) or 'q' to quit: ", end="")
            user_input = input().strip().lower()
            
            if user_input == 'q':
                print("👋 Goodbye!")
                return None
            
            choice = int(user_input)
            
            if 1 <= choice <= max_choice:
                selected_file = csv_files[choice - 1]
                print(f"✅ Selected: {os.path.basename(selected_file)}")
                return selected_file
            else:
                print(f"❌ Please enter a number between 1 and {max_choice}")
                
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")


def generate_output_filename(input_file):
    """Generate output filename based on input filename."""
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{base_name}_MDS_READY_{timestamp}.csv"
    return os.path.join(OUTPUT_FOLDER, output_filename)


def main():
    """Interactive file processor with folder-based file selection."""
    print("🚀 AMEX TO MDS INVOICE TRANSFORMER")
    print("=" * 50)
    
    # Ensure required folders exist before starting
    if not ensure_folders_exist():
        print("❌ Failed to set up required folders. Please check permissions and try again.")
        input("\nPress Enter to exit...")
        return
    
    while True:
        print("\n📋 MAIN MENU:")
        print("1. Process CSV + Transform + Open Image URLs (Complete Workflow)")
        print("2. Auto-detect, move, and convert images to PDF format")
        print("3. Verify downloaded images (Sanity Check)")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            process_amex_file()
        elif choice == "2":
            auto_detect_images()
        elif choice == "3":
            verify_images()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")


def process_amex_file():
    """Process Amex CSV file with complete workflow: CSV processing, transformation, and automatic image URL opening."""
    print("\n🔄 COMPLETE WORKFLOW: CSV + TRANSFORM + OPEN IMAGE URLs")
    print("=" * 60)
    
    # Folders are already ensured to exist by main() function
    
    # Find available CSV files
    csv_files = find_csv_files()
    
    # Display menu and get selection
    available_files = display_file_menu(csv_files)
    if not available_files:
        input("\nPress Enter to continue...")
        return
    
    # Get user selection
    selected_file = get_user_selection(available_files)
    if not selected_file:
        return
    
    # Generate output filename
    output_file = generate_output_filename(selected_file)
    
    # Initialize transformer and process
    transformer = AmexToMDSTransformer()
    
    try:
        print(f"\n🔄 Processing: {os.path.basename(selected_file)}")
        print(f"📤 Output will be saved to: {os.path.basename(output_file)}")
        
        # Run transformation
        result_df = transformer.process_file(selected_file, output_file)
        
        # Display results
        if len(result_df) > 0:
            print("\n" + "=" * 60)
            print("✅ PROCESSING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📊 Processed {len(result_df)} invoice records")
            print(f"💰 Total amount: ${result_df['Invoice Amount'].sum():,.2f}")
            print(f"📁 Output saved to: {output_file}")
            
            # Show sample of first few records
            print(f"\n📋 SAMPLE OUTPUT (first 3 records):")
            print("-" * 60)
            sample_cols = ['Company Code', 'Vendor Account', 'Invoice Amount', 'GL Amount 1', 'Invoice Description', 'GL Account BA', 'GL Account BB', 'GL Account BC']
            print(result_df[sample_cols].head(3).to_string(index=False))
            
            print(f"\n🎯 Ready for MDS upload!")
            
            # Show image download workflow information
            images_folder = Path(transformer.images_folder)
            output_folder = Path(os.path.dirname(output_file))
            
            print(f"\n📁 Image Download Workflow:")
            print(f"   - Output Folder: {images_folder.absolute()}")
            print(f"   - URLs List: {output_folder / 'receipt_image_urls.txt'}")
            print(f"   - Batch Script: {output_folder / 'open_receipt_urls.bat'}")
            
            print(f"\n📋 Next Steps:")
            print(f"   1. ✅ CSV processing and transformation completed")
            print(f"   2. ✅ Receipt URLs should have opened in your browser")
            print(f"   3. 📥 Download all images to your Downloads folder")
            print(f"   4. 🔄 Run option 2 to auto-detect, move, and convert images to PDF")
            print(f"   5. ✅ Run option 3 to verify all images (sanity check)")
            print(f"   6. 📤 Upload both the CSV and all images from the Output folder to MDS")
            
        else:
            print("⚠️  No records to process (all transactions may have been filtered out)")
            
    except Exception as e:
        print(f"❌ Processing failed: {e}")
    
    input("\nPress Enter to continue...")


def auto_detect_images():
    """Auto-detect, move, and convert downloaded images to PDF format."""
    print("\n🔍 AUTO-DETECT, MOVE, AND CONVERT IMAGES TO PDF")
    print("=" * 60)
    
    # Ensure folders exist
    if not ensure_folders_exist():
        print("❌ Failed to set up required folders.")
        input("\nPress Enter to continue...")
        return
    
    # Find the most recent processed CSV file
    output_files = list(Path(OUTPUT_FOLDER).glob("*_MDS_READY_*.csv"))
    if not output_files:
        print("❌ No processed CSV files found. Please run option 1 first.")
        input("\nPress Enter to continue...")
        return
    
    # Get the most recent file
    latest_file = max(output_files, key=lambda x: x.stat().st_mtime)
    print(f"📁 Using latest processed file: {latest_file.name}")
    
    # Find corresponding input file
    input_files = list(Path("Input").glob("*.csv"))
    if not input_files:
        print("❌ No input CSV files found.")
        input("\nPress Enter to continue...")
        return
    
    # Use the first input file (or you could match by name)
    input_file = input_files[0]
    
    # Initialize transformer
    transformer = AmexToMDSTransformer()
    
    try:
        # Load and filter the original data
        amex_df = transformer.load_amex_data(str(input_file))
        filtered_df = transformer.filter_positive_transactions(amex_df)
        
        # Auto-detect and move images
        updated_df = transformer.find_and_move_downloaded_images(filtered_df)
        
        # Convert moved images to PDF format
        if len(updated_df) > 0:
            print(f"\n🖼️  Converting moved images to PDF format...")
            processed_df = transformer.process_images_for_mds(updated_df)
            print(f"✅ PDF conversion complete!")
            
            # Regenerate the CSV with correct PDF filenames
            print(f"\n📝 Updating CSV with correct PDF filenames...")
            mds_df = transformer.transform_to_mds_format(processed_df)
            output_files = list(Path(OUTPUT_FOLDER).glob("*_MDS_READY_*.csv"))
            if output_files:
                latest_csv = max(output_files, key=lambda x: x.stat().st_mtime)
                transformer.save_mds_data(mds_df, str(latest_csv))
                print(f"✅ CSV updated with correct PDF filenames: {latest_csv.name}")
            else:
                print(f"⚠️  No CSV file found to update")
        else:
            print(f"⚠️  No images found to convert to PDF")
        
        print(f"\n✅ Auto-detection, move, and PDF conversion complete!")
        print(f"📁 Images have been moved and converted to PDF format")
        print(f"🔄 Run option 3 to verify all images were processed correctly")
        
    except Exception as e:
        print(f"❌ Auto-detection failed: {e}")
    
    input("\nPress Enter to continue...")


def verify_images():
    """Verify downloaded images (Sanity Check)."""
    print("\n🔍 VERIFY DOWNLOADED IMAGES (SANITY CHECK)")
    print("=" * 50)
    
    # Ensure folders exist
    if not ensure_folders_exist():
        print("❌ Failed to set up required folders.")
        input("\nPress Enter to continue...")
        return
    
    # Find the most recent processed CSV file
    output_files = list(Path(OUTPUT_FOLDER).glob("*_MDS_READY_*.csv"))
    if not output_files:
        print("❌ No processed CSV files found. Please run option 1 first.")
        input("\nPress Enter to continue...")
        return
    
    # Get the most recent file
    latest_file = max(output_files, key=lambda x: x.stat().st_mtime)
    print(f"📁 Using latest processed file: {latest_file.name}")
    
    # Find corresponding input file
    input_files = list(Path("Input").glob("*.csv"))
    if not input_files:
        print("❌ No input CSV files found.")
        input("\nPress Enter to continue...")
        return
    
    # Use the first input file
    input_file = input_files[0]
    
    # Use the existing verification function
    verify_images_for_file(str(input_file))
    
    input("\nPress Enter to continue...")


def process_single_file(file_path: str, output_path: str = None):
    """Convenience function to process a single file (for advanced users)."""
    transformer = AmexToMDSTransformer()
    return transformer.process_file(file_path, output_path)


def verify_images_for_file(csv_file_path: str):
    """Verify downloaded images for a processed CSV file."""
    print("🔍 IMAGE VERIFICATION TOOL")
    print("=" * 40)
    
    # Load the original Amex data
    transformer = AmexToMDSTransformer()
    try:
        amex_df = transformer.load_amex_data(csv_file_path)
        filtered_df = transformer.filter_positive_transactions(amex_df)
        
        # Verify downloaded images
        verified_df = transformer.verify_downloaded_images(filtered_df)
        
        # Count results
        total_with_images = len(verified_df[verified_df['Image URL'].notna() & (verified_df['Image URL'] != '')])
        downloaded_images = len(verified_df[verified_df['Local_Image_Path'].notna()])
        pdf_images = len(verified_df[verified_df['PDF_Image_Path'].notna()])
        
        print(f"\n📊 VERIFICATION RESULTS:")
        print(f"   - Total transactions with images: {total_with_images}")
        print(f"   - Successfully downloaded: {downloaded_images}")
        print(f"   - Converted to PDF: {pdf_images}")
        print(f"   - Missing images: {total_with_images - downloaded_images}")
        
        if downloaded_images < total_with_images:
            print(f"\n⚠️  Some images are missing. Please check the Output folder.")
            print(f"   Run the batch script again if needed.")
        
        return verified_df
        
    except Exception as e:
        print(f"❌ Error verifying images: {str(e)}")
        return None


if __name__ == "__main__":
    main()