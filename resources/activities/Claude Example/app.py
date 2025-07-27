from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
import io
import os
from werkzeug.utils import secure_filename
import tempfile
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def calculate_imputation_stats(original_df, processed_df, numeric_columns):
    """Calculate statistics about the imputation process"""
    stats = {
        'total_rows': int(len(original_df)),
        'total_columns': int(len(original_df.columns)),
        'numeric_columns': int(len(numeric_columns)),
        'column_means': {},
        'imputed_counts': {},
        'total_imputations': 0
    }
    
    for col in numeric_columns:
        # Count missing values in original data
        missing_count = int(original_df[col].isna().sum())
        stats['imputed_counts'][col] = missing_count
        stats['total_imputations'] += missing_count
        
        # Calculate mean (excluding NaN values)
        mean_val = original_df[col].mean()
        stats['column_means'][col] = float(mean_val) if not pd.isna(mean_val) else 0.0
    
    # Calculate missing data rate
    total_numeric_cells = int(len(original_df) * len(numeric_columns))
    if total_numeric_cells > 0:
        stats['missing_data_rate'] = float(round((stats['total_imputations'] / total_numeric_cells) * 100, 2))
    else:
        stats['missing_data_rate'] = 0.0
    
    return stats

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for API status"""
    return jsonify({
        'status': 'success',
        'message': 'CSV Imputation API is running',
        'endpoints': {
            'upload': '/api/upload',
            'process': '/api/process',
            'download': '/api/download/<filename>'
        }
    })

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and return basic file info"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        timestamp = str(int(pd.Timestamp.now().timestamp()))
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Read CSV to get basic info
        try:
            df = pd.read_csv(file_path)
            file_info = {
                'filename': filename,
                'original_filename': file.filename,
                'rows': int(len(df)),
                'columns': int(len(df.columns)),
                'column_names': [str(col) for col in df.columns.tolist()],
                'file_size': int(os.path.getsize(file_path))
            }
            
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'file_info': file_info
            })
            
        except Exception as e:
            # Clean up file if CSV reading fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Invalid CSV file: {str(e)}'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/process', methods=['POST'])
def process_file():
    """Process the uploaded file and perform imputation"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Filename not provided'}), 400
        
        filename = data['filename']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Read the CSV file
        original_df = pd.read_csv(file_path)
        
        # Create a copy for processing
        processed_df = original_df.copy()
        
        # Identify numeric columns
        numeric_columns = processed_df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_columns:
            return jsonify({'error': 'No numeric columns found for imputation'}), 400
        
        # Perform mean imputation on numeric columns
        for col in numeric_columns:
            if processed_df[col].isna().any():
                mean_value = processed_df[col].mean()
                if not pd.isna(mean_value):
                    processed_df[col].fillna(mean_value, inplace=True)
        
        # Calculate statistics
        stats = calculate_imputation_stats(original_df, processed_df, numeric_columns)
        
        # Save processed file
        processed_filename = f"processed_{filename}"
        processed_file_path = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)
        processed_df.to_csv(processed_file_path, index=False)
        
        # Prepare preview data (first 50 rows) - convert to native Python types
        preview_df = processed_df.head(50)
        preview_data = []
        for _, row in preview_df.iterrows():
            row_dict = {}
            for col in preview_df.columns:
                value = row[col]
                if pd.isna(value):
                    row_dict[col] = None
                elif isinstance(value, (np.integer, np.int64, np.int32)):
                    row_dict[col] = int(value)
                elif isinstance(value, (np.floating, np.float64, np.float32)):
                    row_dict[col] = float(value)
                else:
                    row_dict[col] = str(value)
            preview_data.append(row_dict)
        
        # Create imputation flags for frontend highlighting
        imputation_flags = {}
        for col in numeric_columns:
            missing_mask = original_df[col].isna()
            imputation_flags[col] = [bool(x) for x in missing_mask.head(50).tolist()]
        
        return jsonify({
            'status': 'success',
            'message': 'File processed successfully',
            'stats': stats,
            'preview_data': preview_data,
            'imputation_flags': imputation_flags,
            'processed_filename': processed_filename,
            'numeric_columns': numeric_columns
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download the processed file"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"imputed_{filename.replace('processed_', '').split('_', 1)[1]}",
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up uploaded and processed files"""
    try:
        data = request.get_json()
        filenames = data.get('filenames', [])
        
        cleaned_files = []
        for filename in filenames:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                cleaned_files.append(filename)
        
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up {len(cleaned_files)} files',
            'cleaned_files': cleaned_files
        })
        
    except Exception as e:
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Flask CSV Imputation Server...")
    print("Main page: http://localhost:5000")
    print("API Endpoints:")
    print("  GET  /health               - Health check")
    print("  POST /api/upload           - Upload CSV file")
    print("  POST /api/process          - Process uploaded file")
    print("  GET  /api/download/<file>  - Download processed file")
    print("  POST /api/cleanup          - Clean up temporary files")
    
    app.run(debug=True, host='0.0.0.0', port=5000)