"""
Data extraction and upload utilities for E-ZPass Fraud Detection project.
"""

import os
import logging
import re
from typing import Optional, Union, List, Dict
from pathlib import Path
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gcs_config() -> dict:
    """
    Load GCS configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary with GCS settings
        
    Raises:
        ValueError: If required environment variables are missing
    """
    config = {
        'bucket_name': os.getenv("GCS_BUCKET_NAME"),
        'project_id': os.getenv("GCS_PROJECT_ID"),
        'credentials_path': os.getenv("GCS_CREDENTIALS_PATH"),
        'folder_prefix_raw': os.getenv("GCS_FOLDER_PREFIX_RAW", "data/raw/"),
        'default_content_type': os.getenv("GCS_DEFAULT_CONTENT_TYPE", "text/csv")
    }
    
    # Validate required variables
    if not config['bucket_name']:
        raise ValueError("GCS_BUCKET_NAME environment variable is required")
    
    if not config['project_id']:
        raise ValueError("GCS_PROJECT_ID environment variable is required")
    
    return config


def rename_transaction_files(directory_path: Union[str, Path]) -> dict:
    """
    Rename CSV transaction files to the format 'transactions_{year}_{month}.csv'.
    
    Args:
        directory_path (str or Path): Path to the directory containing CSV files
        
    Returns:
        dict: Dictionary with original filenames as keys and new filenames as values
        
    Example:
        'Transaction July 2025 1 thru 30.csv' -> 'transactions_2025_jul.csv'
        'Transactions April 2025.csv' -> 'transactions_2025_apr.csv'
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return {}
    
    # Month name to abbreviation mapping
    month_mapping = {
        'january': 'jan', 'jan': 'jan',
        'february': 'feb', 'feb': 'feb', 
        'march': 'mar', 'mar': 'mar',
        'april': 'apr', 'apr': 'apr',
        'may': 'may',
        'june': 'jun', 'jun': 'jun',
        'july': 'jul', 'jul': 'jul',
        'august': 'aug', 'aug': 'aug',
        'september': 'sep', 'sept': 'sep', 'sep': 'sep',
        'october': 'oct', 'oct': 'oct',
        'november': 'nov', 'nov': 'nov',
        'december': 'dec', 'dec': 'dec'
    }
    
    rename_results = {}
    
    # Find all CSV files in the directory
    csv_files = list(directory.glob("*.csv"))
    
    for csv_file in csv_files:
        original_name = csv_file.name.lower()
        
        # Extract month and year using regex patterns
        # Pattern 1: "transaction[s]? [month] [year]"
        pattern1 = r'transaction[s]?\s+(\w+)\s+(\d{4})'
        match1 = re.search(pattern1, original_name)
        
        # Pattern 2: "[month] [year]" (for files that start with month)
        pattern2 = r'^(\w+)\s+(\d{4})'
        match2 = re.search(pattern2, original_name)
        
        month = None
        year = None
        
        if match1:
            month_str = match1.group(1)
            year = match1.group(2)
        elif match2:
            month_str = match2.group(1)
            year = match2.group(2)
        else:
            logger.warning(f"Could not extract month/year from filename: {csv_file.name}")
            continue
        
        # Convert month to abbreviation
        month_abbr = month_mapping.get(month_str)
        if not month_abbr:
            logger.warning(f"Unknown month: {month_str} in file {csv_file.name}")
            continue
        
        # Create new filename (year then month format)
        new_filename = f"transactions_{year}_{month_abbr}.csv"
        new_path = csv_file.parent / new_filename
        
        # Check if target file already exists
        if new_path.exists() and new_path != csv_file:
            logger.warning(f"Target file already exists: {new_path}")
            continue
        
        try:
            # Rename the file
            csv_file.rename(new_path)
            rename_results[csv_file.name] = new_filename
            logger.info(f"Renamed: {csv_file.name} -> {new_filename}")
            
        except Exception as e:
            logger.error(f"Failed to rename {csv_file.name}: {str(e)}")
    
    return rename_results


def upload_files(file_paths: Union[str, Path, List[Union[str, Path]]],
                bucket_name: str,
                destination_names: Optional[Union[str, List[str]]] = None,
                folder_prefix: str = "",
                content_type: str = "text/csv",
                credentials_path: Optional[str] = None,
                project_id: Optional[str] = None) -> Union[bool, Dict[str, bool]]:
    """
    Upload CSV files to Google Cloud Storage.
    
    This function can handle multiple use cases:
    - Single file: pass file_paths as string/Path, destination_names as string (optional)
    - Multiple files: pass file_paths as list, destination_names as list (optional)
    
    Args:
        file_paths (str, Path, or List): Single file path or list of file paths
        bucket_name (str): Name of the GCS bucket
        destination_names (str or List[str], optional): Destination names in GCS
        folder_prefix (str): Optional folder prefix in GCS
        content_type (str): MIME type for the uploaded files
        credentials_path (str, optional): Path to service account JSON file
        project_id (str, optional): Google Cloud project ID
        
    Returns:
        For single file: bool (success status)
        For multiple files: Dict[str, bool] (file paths as keys, success status as values)
    """
    # Initialize GCS client
    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        client = storage.Client(credentials=credentials, project=project_id)
        logger.info(f"Initialized GCS client with service account: {credentials_path}")
    else:
        # Use default credentials (e.g., from environment or gcloud auth)
        client = storage.Client(project=project_id)
        logger.info("Initialized GCS client with default credentials")
    
    # Normalize input to list
    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]
        single_file = True
    else:
        single_file = False
    
    # Normalize destination names
    if destination_names is None:
        destination_names = [None] * len(file_paths)
    elif isinstance(destination_names, str):
        destination_names = [destination_names]
    
    if len(destination_names) != len(file_paths):
        logger.error("Number of destination names must match number of files")
        return False if single_file else {}
    
    results = {}
    
    for i, file_path in enumerate(file_paths):
        try:
            local_path = Path(file_path)
            
            # Validate file exists
            if not local_path.exists():
                logger.error(f"File not found: {local_path}")
                results[str(file_path)] = False
                continue
            
            # Validate it's a CSV file
            if local_path.suffix.lower() != '.csv':
                logger.warning(f"File {local_path} doesn't have .csv extension")
            
            # Set destination blob name
            if destination_names[i] is None:
                destination_blob_name = local_path.name
            else:
                destination_blob_name = destination_names[i]
            
            # Add folder prefix if provided
            if folder_prefix:
                destination_blob_name = f"{folder_prefix}{destination_blob_name}"
            
            # Get bucket
            bucket = client.bucket(bucket_name)
            
            # Create blob
            blob = bucket.blob(destination_blob_name)
            
            # Upload file
            blob.upload_from_filename(str(local_path), content_type=content_type)
            
            logger.info(f"Successfully uploaded {local_path} to gs://{bucket_name}/{destination_blob_name}")
            results[str(file_path)] = True
            
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {str(e)}")
            results[str(file_path)] = False
    
    # Return appropriate format based on input
    if single_file:
        return results[str(file_paths[0])]
    else:
        return results
    
def list_files(bucket_name: str,
               prefix: str = "",
               credentials_path: Optional[str] = None,
               project_id: Optional[str] = None) -> list:
    """
    List files in the GCS bucket.
    
    Args:
        bucket_name (str): Name of the GCS bucket
        prefix (str): Optional prefix to filter files
        credentials_path (str, optional): Path to service account JSON file
        project_id (str, optional): Google Cloud project ID
        
    Returns:
        list: List of blob names
    """
    try:
        # Initialize GCS client
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            client = storage.Client(credentials=credentials, project=project_id)
        else:
            client = storage.Client(project=project_id)
        
        bucket = client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        return []
    
def download_csv(blob_name: str,
                 local_file_path: Union[str, Path],
                 bucket_name: str,
                 credentials_path: Optional[str] = None,
                 project_id: Optional[str] = None) -> bool:
    """
    Download a CSV file from Google Cloud Storage.
    
    Args:
        blob_name (str): Name of the blob in GCS
        local_file_path (str or Path): Local path to save the file
        bucket_name (str): Name of the GCS bucket
        credentials_path (str, optional): Path to service account JSON file
        project_id (str, optional): Google Cloud project ID
        
    Returns:
        bool: True if download successful, False otherwise
    """
    try:
        # Initialize GCS client
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            client = storage.Client(credentials=credentials, project=project_id)
        else:
            client = storage.Client(project=project_id)
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        local_path = Path(local_file_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading gs://{bucket_name}/{blob_name} to {local_path}")
        blob.download_to_filename(str(local_path))
        
        logger.info(f"Successfully downloaded {blob_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {blob_name}: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        # Load GCS configuration
        config = get_gcs_config()
        
        # Rename transaction files
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        raw_data_dir = script_dir / "../../data/raw"
        print("Renaming transaction files...")
        rename_results = rename_transaction_files(raw_data_dir)
        
        if rename_results:
            print("File rename results:")
            for old_name, new_name in rename_results.items():
                print(f"  {old_name} -> {new_name}")
        else:
            print("No files were renamed.")
        
        print("\n" + "="*50 + "\n")
        
        # Upload multiple CSV files
        # Get all CSV files from raw data directory
        csv_files = list(raw_data_dir.glob("*.csv"))
        if not csv_files:
            print("No CSV files found in raw data directory")
            csv_files = []
        
        results = upload_files(
            file_paths=csv_files,
            bucket_name=config['bucket_name'],
            folder_prefix=config['folder_prefix_raw'],
            credentials_path=config['credentials_path'],
            project_id=config['project_id']
        )
        
        print("Upload results:")
        for file_path, success in results.items():
            print(f"{file_path}: {'Success' if success else 'Failed'}")
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Please check your .env file: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"An error occurred: {e}")
