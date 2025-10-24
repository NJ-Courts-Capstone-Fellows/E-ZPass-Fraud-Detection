from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import shutil
import re
from pathlib import Path
import pendulum

# Configuration from environment variables
RAW_DATA_PATH = '/opt/airflow/data/raw/'
INTERIM_PATH = '/opt/airflow/data/interim/'
GCS_BUCKET = os.getenv('GCS_BUCKET_NAME')
GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID')
GCS_PREFIX = os.getenv('GCS_FOLDER_PREFIX_RAW', 'data/raw/')

# Set timezone to Eastern Time
local_tz = pendulum.timezone("America/New_York")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1, tzinfo=local_tz),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def detect_and_rename_files(**context):
    """
    Detect new CSV files in data/raw/ and rename them to transaction_{year}_{month}.csv
    Returns list of renamed file paths
    """
    raw_path = Path(RAW_DATA_PATH)
    interim_path = Path(INTERIM_PATH)
    interim_path.mkdir(parents=True, exist_ok=True)
    
    renamed_files = []
    
    # Get all CSV files in raw directory
    csv_files = list(raw_path.glob('*.csv'))
    
    if not csv_files:
        print("No CSV files found in raw directory")
        return []
    
    for csv_file in csv_files:
        # Extract date from filename or use current date
        # First try to extract numeric date (e.g., data_2024_01.csv, transactions_20240115.csv)
        date_match = re.search(r'(\d{4})[-_]?(\d{2})', csv_file.name)
        
        if date_match:
            year = date_match.group(1)
            month = date_match.group(2)
        else:
            # Try to extract month name and year from patterns like:
            # "Transactions April 2025" or "Transaction July 2025 1 thru 30"
            month_names = {
                'january': 'january', 'jan': 'january',
                'february': 'february', 'feb': 'february', 
                'march': 'march', 'mar': 'march',
                'april': 'april', 'apr': 'april',
                'may': 'may',
                'june': 'june', 'jun': 'june',
                'july': 'july', 'jul': 'july',
                'august': 'august', 'aug': 'august',
                'september': 'september', 'sep': 'september', 'sept': 'september',
                'october': 'october', 'oct': 'october',
                'november': 'november', 'nov': 'november',
                'december': 'december', 'dec': 'december'
            }
            
            # Look for month name and year pattern (case insensitive)
            # Matches: "Transactions April 2025", "Transaction July 2025 1 thru 30"
            month_year_match = re.search(r'(?:transactions?|transaction)\s+(\w+)\s+(\d{4})', csv_file.name.lower())
            
            if month_year_match:
                month_name = month_year_match.group(1)
                year = month_year_match.group(2)
                normalized_month = month_names.get(month_name, None)
                
                if normalized_month:
                    print(f"Extracted date from filename: {month_name} {year} → {year}_{normalized_month}")
                    month = normalized_month
                else:
                    # Use current date if month name not recognized
                    now = datetime.now()
                    year = now.strftime('%Y')
                    month = now.strftime('%B').lower()  # Full month name in lowercase
                    print(f"Unrecognized month '{month_name}', using current date: {year}_{month}")
            else:
                # Use current date if no date found in filename
                now = datetime.now()
                year = now.strftime('%Y')
                month = now.strftime('%B').lower()  # Full month name in lowercase
                print(f"No date pattern found in filename, using current date: {year}_{month}")
        
        # Create new filename
        new_filename = f'transaction_{year}_{month}.csv'
        new_filepath = interim_path / new_filename
        
        # Copy file to interim with new name
        shutil.copy2(csv_file, new_filepath)
        renamed_files.append(str(new_filepath))
        
        print(f"Renamed {csv_file.name} to {new_filename}")
    
    # Push renamed files list to XCom for next task
    context['ti'].xcom_push(key='renamed_files', value=renamed_files)
    
    return renamed_files

def upload_to_gcs(**context):
    """
    Upload renamed files to Google Cloud Storage using environment variables
    """
    from google.cloud import storage
    
    ti = context['ti']
    renamed_files = ti.xcom_pull(key='renamed_files', task_ids='detect_and_rename')
    
    if not renamed_files:
        print("No files to upload")
        return
    
    # Validate environment variables
    if not GCS_BUCKET:
        raise ValueError("GCS_BUCKET_NAME environment variable is not set")
    
    if not GCS_PROJECT_ID:
        raise ValueError("GCS_PROJECT_ID environment variable is not set")
    
    # Initialize GCS client
    client = storage.Client(project=GCS_PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)
    
    uploaded_count = 0
    for local_file in renamed_files:
        filename = Path(local_file).name
        # Use the prefix from environment variable
        blob_name = f"{GCS_PREFIX.rstrip('/')}/{filename}"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_file)
        
        print(f"✓ Uploaded {filename} to gs://{GCS_BUCKET}/{blob_name}")
        uploaded_count += 1
    
    print(f"\n=== Upload Summary ===")
    print(f"Total files uploaded: {uploaded_count}")
    print(f"Bucket: gs://{GCS_BUCKET}")
    print(f"Prefix: {GCS_PREFIX}")
    
    return uploaded_count


# Define the DAG
with DAG(
    'gcs_upload_raw_pipeline',
    default_args=default_args,
    description='Detect, rename, and upload CSV files to GCS',
    schedule_interval='@hourly',
    catchup=False,
    tags=['gcs', 'csv', 'upload', 'ezpass'],
) as dag:
    
    # Task 1: Detect and rename files
    detect_rename_task = PythonOperator(
        task_id='detect_and_rename',
        python_callable=detect_and_rename_files,
        provide_context=True,
    )
    
    # Task 2: Upload to GCS
    upload_task = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_to_gcs,
        provide_context=True,
    )
    
    # Execution order
    detect_rename_task >> upload_task