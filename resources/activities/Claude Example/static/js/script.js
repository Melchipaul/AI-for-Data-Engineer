const API_BASE_URL = '/api';
let currentFileInfo = null;
let processedFilename = null;

document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
});

async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
        showError('Please select a CSV file.');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading('Uploading file...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            currentFileInfo = result.file_info;
            document.getElementById('fileInfo').innerHTML = `
                ✅ <strong>${result.file_info.original_filename}</strong><br>
                📊 ${result.file_info.rows} rows × ${result.file_info.columns} columns<br>
                📁 ${(result.file_info.file_size / 1024).toFixed(1)} KB
            `;
            document.getElementById('processBtn').disabled = false;
            showSuccess('File uploaded successfully!');
        } else {
            showError(result.error || 'Upload failed');
            currentFileInfo = null;
        }
    } catch (error) {
        hideLoading();
        showError('Network error: ' + error.message);
        currentFileInfo = null;
    }
}

async function processFile() {
    if (!currentFileInfo) {
        showError('Please upload a file first!');
        return;
    }
    
    showLoading('Processing data and imputing missing values...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: currentFileInfo.filename
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            processedFilename = result.processed_filename;
            displayResults(result);
            showSuccess('Data processed successfully!');
        } else {
            showError(result.error || 'Processing failed');
        }
    } catch (error) {
        hideLoading();
        showError('Network error: ' + error.message);
    }
}

function displayResults(result) {
    displayStats(result.stats);
    displayTable(result.preview_data, result.imputation_flags, result.numeric_columns);
    document.getElementById('results').style.display = 'block';
}

function displayStats(stats) {
    const statsHtml = `
        <div class="stat-card">
            <div class="stat-number">${stats.total_rows}</div>
            <div>Total Rows</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.numeric_columns}</div>
            <div>Numeric Columns</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.total_imputations}</div>
            <div>Values Imputed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">${stats.missing_data_rate}%</div>
            <div>Missing Data Rate</div>
        </div>
    `;
    document.getElementById('stats').innerHTML = statsHtml;
}

function displayTable(data, imputationFlags, numericColumns) {
    const table = document.getElementById('dataTable');
    
    if (data.length === 0) {
        table.innerHTML = '<tr><td>No data to display</td></tr>';
        return;
    }
    
    const columns = Object.keys(data[0]);
    
    // Create header
    const headerRow = `<tr>${columns.map(col => `<th>${col}</th>`).join('')}</tr>`;
    
    // Create rows
    const dataRows = data.map((row, rowIndex) => {
        const cells = columns.map(col => {
            const value = row[col];
            const isImputed = imputationFlags[col] && imputationFlags[col][rowIndex];
            const cellClass = isImputed ? 'imputed-value' : '';
            const displayValue = value !== null && value !== undefined ? value : '';
            return `<td><span class="${cellClass}">${displayValue}</span></td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');
    
    table.innerHTML = headerRow + dataRows;
    
    if (data.length >= 50) {
        table.innerHTML += `<tr><td colspan="${columns.length}" style="text-align: center; font-style: italic; color: #666;">Showing first 50 rows</td></tr>`;
    }
}

async function downloadProcessedFile() {
    if (!processedFilename) {
        showError('No processed file available for download.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/download/${processedFilename}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `imputed_${currentFileInfo.original_filename}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showSuccess('File downloaded successfully!');
        } else {
            const error = await response.json();
            showError(error.error || 'Download failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

async function cleanupFiles() {
    if (!currentFileInfo) return;
    
    const filesToCleanup = [currentFileInfo.filename];
    if (processedFilename) {
        filesToCleanup.push(processedFilename);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/cleanup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filenames: filesToCleanup
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showSuccess('Temporary files cleaned up successfully!');
            // Reset the interface
            currentFileInfo = null;
            processedFilename = null;
            document.getElementById('fileInfo').textContent = 'No file selected';
            document.getElementById('processBtn').disabled = true;
            document.getElementById('results').style.display = 'none';
            document.getElementById('fileInput').value = '';
        } else {
            showError(result.error || 'Cleanup failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

function showLoading(text) {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    showMessage(message, 'error');
}

function showSuccess(message) {
    showMessage(message, 'success');
}

function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = type;
    messageDiv.textContent = message;
    
    const container = document.querySelector('.container');
    const results = document.getElementById('results');
    container.insertBefore(messageDiv, results);
    
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}