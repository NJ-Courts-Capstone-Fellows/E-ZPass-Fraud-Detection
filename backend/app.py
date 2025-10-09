from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import uuid
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = '../data/raw'
PROCESSED_FOLDER = '../data/processed'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_transaction_data(df):
    """Validate uploaded transaction data structure"""
    required_columns = [
        'posting_date', 'transaction_date', 'tag_plate_number', 
        'agency', 'exit_time', 'exit_plaza', 'amount'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    # Check for empty data
    if df.empty:
        return False, "File contains no data"
    
    # Check data types
    try:
        pd.to_datetime(df['posting_date'])
        pd.to_datetime(df['transaction_date'])
        pd.to_numeric(df['amount'])
    except Exception as e:
        return False, f"Data type validation failed: {str(e)}"
    
    return True, "Data validation passed"

def process_transaction_data(df):
    """Process and enrich transaction data for fraud detection"""
    try:
        # Convert date columns
        df['posting_date'] = pd.to_datetime(df['posting_date'])
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        # Extract hour from exit time
        df['exit_hour'] = df['exit_time'].dt.hour
        
        # Calculate risk scores based on simple heuristics
        df['risk_score'] = 0
        
        # High amount transactions
        high_amount_threshold = df['amount'].quantile(0.95)
        df.loc[df['amount'] > high_amount_threshold, 'risk_score'] += 30
        
        # Unusual hours (late night/early morning)
        df.loc[(df['exit_hour'] < 5) | (df['exit_hour'] > 23), 'risk_score'] += 20
        
        # Negative amounts (potential refunds)
        df.loc[df['amount'] < 0, 'risk_score'] += 25
        
        # Multiple transactions same day
        daily_counts = df.groupby(['tag_plate_number', 'transaction_date']).size()
        df['daily_transaction_count'] = df.set_index(['tag_plate_number', 'transaction_date']).index.map(daily_counts)
        df.loc[df['daily_transaction_count'] > 5, 'risk_score'] += 15
        
        # Determine status based on risk score
        df['status'] = 'Normal'
        df.loc[df['risk_score'] >= 50, 'status'] = 'Flagged'
        df.loc[df['risk_score'] >= 80, 'status'] = 'Investigating'
        
        # Determine category
        df['category'] = 'Normal'
        df.loc[df['amount'] < 0, 'category'] = 'Refund'
        df.loc[df['daily_transaction_count'] > 5, 'category'] = 'Toll Evasion'
        df.loc[df['risk_score'] >= 80, 'category'] = 'Account Takeover'
        
        # Determine severity
        df['severity'] = 'Low'
        df.loc[df['risk_score'] >= 50, 'severity'] = 'Medium'
        df.loc[df['risk_score'] >= 80, 'severity'] = 'High'
        
        # Generate transaction IDs
        df['id'] = ['TXN' + str(uuid.uuid4().hex[:6]).upper() for _ in range(len(df))]
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        raise e

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Please upload CSV or Excel files.'}), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save file
        file.save(filepath)
        logger.info(f"File saved: {filepath}")
        
        # Read and validate data
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
        except Exception as e:
            os.remove(filepath)  # Clean up invalid file
            return jsonify({'error': f'Error reading file: {str(e)}'}), 400
        
        # Validate data structure
        is_valid, message = validate_transaction_data(df)
        if not is_valid:
            os.remove(filepath)  # Clean up invalid file
            return jsonify({'error': message}), 400
        
        # Process data
        processed_df = process_transaction_data(df)
        
        # Save processed data
        processed_filename = f"processed_{timestamp}_{filename.replace('.xlsx', '.csv').replace('.xls', '.csv')}"
        processed_filepath = os.path.join(PROCESSED_FOLDER, processed_filename)
        processed_df.to_csv(processed_filepath, index=False)
        
        # Generate summary statistics
        summary = {
            'total_transactions': len(processed_df),
            'flagged_transactions': len(processed_df[processed_df['status'] == 'Flagged']),
            'investigating_transactions': len(processed_df[processed_df['status'] == 'Investigating']),
            'total_amount': float(processed_df['amount'].sum()),
            'high_risk_transactions': len(processed_df[processed_df['risk_score'] >= 80]),
            'agencies': processed_df['agency'].unique().tolist(),
            'date_range': {
                'start': processed_df['transaction_date'].min().strftime('%Y-%m-%d'),
                'end': processed_df['transaction_date'].max().strftime('%Y-%m-%d')
            }
        }
        
        logger.info(f"File processed successfully: {processed_filename}")
        
        return jsonify({
            'message': 'File uploaded and processed successfully',
            'filename': unique_filename,
            'processed_filename': processed_filename,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """Get processed transaction data"""
    try:
        # Get the most recent processed file
        processed_files = [f for f in os.listdir(PROCESSED_FOLDER) if f.startswith('processed_')]
        if not processed_files:
            return jsonify({'transactions': [], 'message': 'No processed data available'})
        
        # Sort by filename (which includes timestamp)
        latest_file = sorted(processed_files)[-1]
        filepath = os.path.join(PROCESSED_FOLDER, latest_file)
        
        df = pd.read_csv(filepath)
        
        # Convert to JSON-serializable format
        transactions = df.to_dict('records')
        
        # Convert datetime objects to strings
        for transaction in transactions:
            for key, value in transaction.items():
                if pd.isna(value):
                    transaction[key] = None
                elif isinstance(value, (pd.Timestamp, datetime)):
                    transaction[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, (int, float)) and pd.isna(value):
                    transaction[key] = None
        
        return jsonify({
            'transactions': transactions,
            'total_count': len(transactions),
            'source_file': latest_file
        })
        
    except Exception as e:
        logger.error(f"Error retrieving transactions: {str(e)}")
        return jsonify({'error': f'Error retrieving data: {str(e)}'}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get dashboard statistics"""
    try:
        # Get the most recent processed file
        processed_files = [f for f in os.listdir(PROCESSED_FOLDER) if f.startswith('processed_')]
        if not processed_files:
            return jsonify({
                'total_alerts': 0,
                'potential_loss': 0,
                'detected_frauds': 0,
                'message': 'No data available'
            })
        
        latest_file = sorted(processed_files)[-1]
        filepath = os.path.join(PROCESSED_FOLDER, latest_file)
        df = pd.read_csv(filepath)
        
        # Calculate statistics
        total_alerts = len(df[df['status'].isin(['Flagged', 'Investigating'])])
        potential_loss = float(df[df['status'].isin(['Flagged', 'Investigating'])]['amount'].sum())
        detected_frauds = len(df[df['status'] == 'Investigating'])
        
        return jsonify({
            'total_alerts': total_alerts,
            'potential_loss': abs(potential_loss),  # Use absolute value for display
            'detected_frauds': detected_frauds,
            'total_transactions': len(df),
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {str(e)}")
        return jsonify({'error': f'Error calculating statistics: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
