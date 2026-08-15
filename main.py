from flask import Flask, request, jsonify, send_file, render_template_string, send_from_directory
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import os
import json
import tempfile
import zipfile
from io import BytesIO
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

# HTML Frontend (embedded)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Splitter Tool</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 40px;
        }

        .header h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .header p {
            opacity: 0.9;
            font-size: 16px;
        }

        .content {
            padding: 40px;
        }

        /* File Upload Section */
        .upload-section {
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            transition: all 0.3s ease;
            cursor: pointer;
        }

        .upload-section:hover {
            border-color: #667eea;
            background: #f0f1ff;
        }

        .upload-section.dragover {
            border-color: #667eea;
            background: #e8eaff;
        }

        .upload-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        .upload-section h3 {
            color: #333;
            margin-bottom: 8px;
        }

        .upload-section p {
            color: #6c757d;
            font-size: 14px;
        }

        #fileInput {
            display: none;
        }

        .file-info {
            display: none;
            background: #e8f5e9;
            padding: 16px 20px;
            border-radius: 8px;
            margin-top: 16px;
            align-items: center;
            gap: 12px;
        }

        .file-info.show {
            display: flex;
        }

        .file-info .file-name {
            flex: 1;
            font-weight: 500;
            color: #2e7d32;
        }

        .file-info .file-size {
            color: #555;
            font-size: 14px;
        }

        .file-info .remove-file {
            background: #dc3545;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }

        .file-info .remove-file:hover {
            background: #c82333;
        }

        /* Controls */
        .controls {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }

        .controls button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5a67d8;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .btn-success {
            background: #48bb78;
            color: white;
        }

        .btn-success:hover {
            background: #38a169;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
        }

        .btn-danger {
            background: #fc8181;
            color: white;
        }

        .btn-danger:hover {
            background: #f56565;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(252, 129, 129, 0.4);
        }

        .btn-secondary {
            background: #e2e8f0;
            color: #2d3748;
        }

        .btn-secondary:hover {
            background: #cbd5e0;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }

        /* Ranges Table */
        .ranges-container {
            margin-top: 24px;
            overflow-x: auto;
        }

        .ranges-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .ranges-header h2 {
            font-size: 20px;
            color: #2d3748;
        }

        .range-count {
            background: #e2e8f0;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            color: #4a5568;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }

        thead {
            background: #f7fafc;
            border-bottom: 2px solid #e2e8f0;
        }

        th {
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        td {
            padding: 12px 16px;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: middle;
        }

        tr:hover {
            background: #f7fafc;
        }

        .range-input {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }

        .range-input input {
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            width: 80px;
            transition: border-color 0.3s ease;
        }

        .range-input input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .range-input input.name-input {
            width: 140px;
        }

        .range-input span {
            color: #718096;
            font-weight: 500;
        }

        .delete-row {
            background: none;
            border: none;
            color: #fc8181;
            cursor: pointer;
            font-size: 18px;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.2s ease;
        }

        .delete-row:hover {
            background: #fed7d7;
            color: #e53e3e;
        }

        .add-row {
            margin-top: 16px;
            padding: 12px;
            width: 100%;
            border: 2px dashed #e2e8f0;
            border-radius: 8px;
            background: none;
            color: #4a5568;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .add-row:hover {
            border-color: #667eea;
            background: #f7fafc;
            color: #667eea;
        }

        /* Status/Progress */
        .status {
            margin-top: 24px;
            padding: 16px 20px;
            border-radius: 8px;
            display: none;
            align-items: center;
            gap: 12px;
        }

        .status.show {
            display: flex;
        }

        .status.info {
            background: #bee3f8;
            color: #2a69ac;
        }

        .status.success {
            background: #c6f6d5;
            color: #22543d;
        }

        .status.error {
            background: #fed7d7;
            color: #9b2c2c;
        }

        .status .spinner {
            width: 20px;
            height: 20px;
            border: 3px solid rgba(0, 0, 0, 0.1);
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Progress Bar */
        .progress-container {
            margin-top: 16px;
            display: none;
        }

        .progress-container.show {
            display: block;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-bar .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            width: 0%;
        }

        .progress-text {
            margin-top: 8px;
            font-size: 14px;
            color: #4a5568;
        }

        /* Export Section */
        .export-section {
            margin-top: 24px;
            padding: 20px;
            background: #f7fafc;
            border-radius: 8px;
            display: none;
        }

        .export-section.show {
            display: block;
        }

        .export-section h3 {
            color: #2d3748;
            margin-bottom: 12px;
        }

        .export-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 8px;
            margin-top: 12px;
        }

        .export-item {
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            font-size: 14px;
            color: #2d3748;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .export-item .badge {
            background: #48bb78;
            color: white;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 24px;
            }
            
            .content {
                padding: 20px;
            }
            
            .range-input input {
                width: 60px;
            }
            
            .range-input input.name-input {
                width: 100px;
            }
            
            .controls {
                flex-direction: column;
            }
            
            .controls button {
                width: 100%;
                justify-content: center;
            }
        }

        /* Scrollable table container */
        .table-wrapper {
            overflow-x: auto;
            border-radius: 8px;
        }

        /* Example ranges badge */
        .example-badge {
            display: inline-block;
            background: #e9d5ff;
            color: #6b21a5;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 8px;
        }

        .tooltip {
            position: relative;
            cursor: help;
        }

        .tooltip:hover::after {
            content: attr(data-tip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #1a202c;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            margin-bottom: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📄 PDF Splitter</h1>
            <p>Split your PDF into multiple files based on custom page ranges</p>
        </div>

        <!-- Content -->
        <div class="content">
            <!-- File Upload -->
            <div class="upload-section" id="uploadSection">
                <div class="upload-icon">📤</div>
                <h3>Upload your PDF file</h3>
                <p>Drag and drop or click to browse</p>
                <input type="file" id="fileInput" accept=".pdf">
                
                <div class="file-info" id="fileInfo">
                    <span class="file-name" id="fileName">document.pdf</span>
                    <span class="file-size" id="fileSize">2.4 MB</span>
                    <button class="remove-file" id="removeFile">✕</button>
                </div>
            </div>

            <!-- Controls -->
            <div class="controls">
                <button class="btn-primary" id="addRangeBtn">
                    ➕ Add Range
                </button>
                <button class="btn-success" id="processBtn" disabled>
                    🚀 Process PDF
                </button>
                <button class="btn-secondary" id="exampleBtn">
                    📋 Load Example
                </button>
                <button class="btn-danger" id="clearAllBtn">
                    🗑️ Clear All
                </button>
            </div>

            <!-- Ranges Table -->
            <div class="ranges-container">
                <div class="ranges-header">
                    <h2>Page Ranges</h2>
                    <span class="range-count" id="rangeCount">0 ranges</span>
                </div>
                
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 30%">Output Name</th>
                                <th style="width: 55%">Page Range(s)</th>
                                <th style="width: 15%">Action</th>
                            </tr>
                        </thead>
                        <tbody id="rangesBody">
                            <!-- Rows will be added here -->
                        </tbody>
                    </table>
                </div>
                
                <button class="add-row" id="addRangeBtnBottom">
                    + Add new range
                </button>
            </div>

            <!-- Status -->
            <div class="status" id="status">
                <span id="statusMessage">Processing...</span>
            </div>

            <!-- Progress -->
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <div class="progress-text" id="progressText">0%</div>
            </div>

            <!-- Export Section -->
            <div class="export-section" id="exportSection">
                <h3>✅ Split Complete! Files created:</h3>
                <div class="export-list" id="exportList">
                    <!-- Exported files will be listed here -->
                </div>
                <button class="btn-primary" id="downloadAllBtn" style="margin-top: 16px;">
                    📦 Download All as ZIP
                </button>
            </div>
        </div>
    </div>

    <script>
        // State
        let ranges = [];
        let uploadedFile = null;
        let totalPages = 0;
        let isProcessing = false;

        // DOM Elements
        const uploadSection = document.getElementById('uploadSection');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const removeFileBtn = document.getElementById('removeFile');
        const rangesBody = document.getElementById('rangesBody');
        const rangeCount = document.getElementById('rangeCount');
        const addRangeBtn = document.getElementById('addRangeBtn');
        const addRangeBtnBottom = document.getElementById('addRangeBtnBottom');
        const processBtn = document.getElementById('processBtn');
        const exampleBtn = document.getElementById('exampleBtn');
        const clearAllBtn = document.getElementById('clearAllBtn');
        const status = document.getElementById('status');
        const statusMessage = document.getElementById('statusMessage');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const exportSection = document.getElementById('exportSection');
        const exportList = document.getElementById('exportList');
        const downloadAllBtn = document.getElementById('downloadAllBtn');

        // Utility Functions
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function generateId() {
            return Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        }

        function updateRangeCount() {
            rangeCount.textContent = ranges.length + ' range' + (ranges.length !== 1 ? 's' : '');
            processBtn.disabled = ranges.length === 0 || !uploadedFile;
        }

        function showStatus(message, type = 'info') {
            status.className = 'status show ' + type;
            statusMessage.textContent = message;
        }

        function hideStatus() {
            status.className = 'status';
        }

        function showProgress(percent, text) {
            progressContainer.classList.add('show');
            progressFill.style.width = percent + '%';
            progressText.textContent = text || percent + '%';
        }

        function hideProgress() {
            progressContainer.classList.remove('show');
        }

        function showExport(files) {
            exportSection.classList.add('show');
            exportList.innerHTML = files.map(file => `
                <div class="export-item">
                    <span>${file}</span>
                    <span class="badge">✓</span>
                </div>
            `).join('');
        }

        function hideExport() {
            exportSection.classList.remove('show');
        }

        // Add Range Row
        function addRangeRow(name = '', rangesStr = '') {
            const id = generateId();
            const row = document.createElement('tr');
            row.dataset.id = id;
            row.innerHTML = `
                <td>
                    <input type="text" class="name-input" placeholder="e.g., chapter1" value="${name}" style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px;">
                </td>
                <td>
                    <input type="text" class="range-input-text" placeholder="e.g., 1-5,10-15" value="${rangesStr}" style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px;">
                </td>
                <td>
                    <button class="delete-row" data-id="${id}">✕</button>
                </td>
            `;
            
            rangesBody.appendChild(row);
            
            // Store in state
            const nameInput = row.querySelector('.name-input');
            const rangeInput = row.querySelector('.range-input-text');
            
            ranges.push({
                id: id,
                name: name,
                ranges: rangesStr
            });
            
            // Update state on change
            nameInput.addEventListener('input', () => {
                const found = ranges.find(r => r.id === id);
                if (found) found.name = nameInput.value;
            });
            
            rangeInput.addEventListener('input', () => {
                const found = ranges.find(r => r.id === id);
                if (found) found.ranges = rangeInput.value;
            });
            
            // Delete
            row.querySelector('.delete-row').addEventListener('click', () => {
                row.remove();
                const index = ranges.findIndex(r => r.id === id);
                if (index > -1) ranges.splice(index, 1);
                updateRangeCount();
                hideExport();
            });
            
            updateRangeCount();
        }

        // Parse ranges string
        function parseRanges(rangeStr) {
            if (!rangeStr.trim()) return [];
            
            const parts = rangeStr.split(',').map(s => s.trim());
            const parsed = [];
            
            for (const part of parts) {
                if (part.includes('-')) {
                    const [start, end] = part.split('-').map(n => parseInt(n.trim()));
                    if (!isNaN(start) && !isNaN(end) && start <= end) {
                        parsed.push([start, end]);
                    } else {
                        return null;
                    }
                } else {
                    const num = parseInt(part);
                    if (!isNaN(num)) {
                        parsed.push([num, num]);
                    } else {
                        return null;
                    }
                }
            }
            
            return parsed;
        }

        // Process PDF
        async function processPDF() {
            if (!uploadedFile || ranges.length === 0 || isProcessing) return;
            
            isProcessing = true;
            processBtn.disabled = true;
            hideExport();
            hideStatus();
            showProgress(0, 'Preparing...');
            
            try {
                // Validate all ranges first
                const validatedRanges = [];
                for (const range of ranges) {
                    if (!range.name.trim()) {
                        showStatus('Please provide a name for all ranges.', 'error');
                        isProcessing = false;
                        processBtn.disabled = false;
                        hideProgress();
                        return;
                    }
                    
                    const parsed = parseRanges(range.ranges);
                    if (!parsed || parsed.length === 0) {
                        showStatus(`Invalid range format for "${range.name}". Use e.g., "1-5,10-15"`, 'error');
                        isProcessing = false;
                        processBtn.disabled = false;
                        hideProgress();
                        return;
                    }
                    
                    validatedRanges.push({
                        name: range.name.trim(),
                        ranges: parsed
                    });
                }
                
                // Create form data
                const formData = new FormData();
                formData.append('pdf', uploadedFile);
                formData.append('ranges', JSON.stringify(validatedRanges));
                
                showProgress(30, 'Sending to server...');
                
                // Send to backend
                const response = await fetch('/process-pdf', {
                    method: 'POST',
                    body: formData
                });
                
                showProgress(70, 'Processing...');
                
                if (!response.ok) {
                    const error = await response.text();
                    throw new Error(error || 'Failed to process PDF');
                }
                
                // Get the ZIP file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'split-pdfs.zip';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                
                showProgress(100, 'Complete!');
                showStatus('✅ PDF split successfully! Download started.', 'success');
                
                // Show exported files (simulate)
                const fileNames = validatedRanges.map(r => r.name + '.pdf');
                showExport(fileNames);
                
            } catch (error) {
                showStatus('❌ Error: ' + error.message, 'error');
                console.error(error);
            } finally {
                isProcessing = false;
                processBtn.disabled = false;
                setTimeout(() => {
                    hideProgress();
                }, 2000);
            }
        }

        // File upload handlers
        uploadSection.addEventListener('click', () => fileInput.click());
        
        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadSection.classList.add('dragover');
        });
        
        uploadSection.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('dragover');
        });
        
        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                handleFile(files[0]);
            } else {
                showStatus('Please upload a valid PDF file.', 'error');
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
        
        function handleFile(file) {
            uploadedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileInfo.classList.add('show');
            uploadSection.style.borderColor = '#48bb78';
            
            // Read total pages
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    // Try to get page count using a simple method
                    // For now, we'll just show a generic message
                    showStatus(`✅ Loaded "${file.name}"`, 'success');
                    processBtn.disabled = ranges.length === 0;
                } catch (error) {
                    console.error('Error reading PDF:', error);
                    showStatus('Could not read PDF pages. Please try another file.', 'error');
                }
            };
            reader.readAsArrayBuffer(file);
            
            hideExport();
        }
        
        removeFileBtn.addEventListener('click', () => {
            uploadedFile = null;
            totalPages = 0;
            fileInfo.classList.remove('show');
            uploadSection.style.borderColor = '#dee2e6';
            fileInput.value = '';
            processBtn.disabled = true;
            hideStatus();
            hideExport();
        });

        // Add range buttons
        addRangeBtn.addEventListener('click', () => addRangeRow());
        addRangeBtnBottom.addEventListener('click', () => addRangeRow());

        // Load Example
        exampleBtn.addEventListener('click', () => {
            // Clear existing
            rangesBody.innerHTML = '';
            ranges = [];
            
            // Add example ranges
            const examples = [
                ['chapter1', '24-27,90-98'],
                ['chapter2', '28-30,98-100'],
                ['chapter3', '31-33,100-105'],
                ['chapter4', '34-36,105-108'],
                ['chapter5', '37-41,109-113'],
                ['chapter6', '42-44,113-114'],
                ['chapter7', '45-47,114-115'],
                ['chapter8', '48-49,116-117'],
                ['chapter9', '50-52,118-122']
            ];
            
            for (const [name, rangesStr] of examples) {
                addRangeRow(name, rangesStr);
            }
            
            showStatus('✅ Example ranges loaded! Upload a PDF to get started.', 'success');
        });

        // Clear All
        clearAllBtn.addEventListener('click', () => {
            if (ranges.length === 0) return;
            if (confirm('Are you sure you want to clear all ranges?')) {
                rangesBody.innerHTML = '';
                ranges = [];
                updateRangeCount();
                hideExport();
                hideStatus();
            }
        });

        // Process button
        processBtn.addEventListener('click', processPDF);

        // Download All (actually just triggers processing again if files exist)
        downloadAllBtn.addEventListener('click', processPDF);

        // Initialize with one empty row
        addRangeRow();

        // Add keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                processPDF();
            }
        });

        console.log('📄 PDF Splitter loaded!');
        console.log('💡 Tips:');
        console.log('  - Add page ranges like "1-5" or "10-15,20-25"');
        console.log('  - Use Ctrl+Enter to process');
        console.log('  - Drag and drop PDF files');
    </script>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_range_string(range_str):
    """Parse range string like '1-5,10-15' into list of tuples"""
    if not range_str or not range_str.strip():
        return []
    
    parts = range_str.split(',')
    ranges = []
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            start = int(start.strip())
            end = int(end.strip())
            if start <= end:
                ranges.append((start, end))
        else:
            num = int(part)
            ranges.append((num, num))
    
    return ranges

@app.route('/')
def index():
    """Serve the frontend"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    try:
        # Check if file is present
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file uploaded'}), 400
        
        file = request.files['pdf']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400
        
        # Get ranges from request
        ranges_data = request.form.get('ranges')
        if not ranges_data:
            return jsonify({'error': 'No ranges provided'}), 400
        
        try:
            ranges = json.loads(ranges_data)
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid ranges format'}), 400
        
        if not ranges:
            return jsonify({'error': 'No valid ranges provided'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        try:
            # Read PDF
            reader = PdfReader(temp_path)
            total_pages = len(reader.pages)
            
            # Create output directory for this session
            session_dir = tempfile.mkdtemp()
            output_files = []
            
            # Process each range
            for range_item in ranges:
                name = range_item.get('name', '').strip()
                range_list = range_item.get('ranges', [])
                
                if not name:
                    continue
                
                # Validate ranges
                valid_ranges = []
                for start, end in range_list:
                    if start < 1 or end > total_pages or start > end:
                        continue
                    valid_ranges.append((start, end))
                
                if not valid_ranges:
                    continue
                
                # Create PDF for this range
                writer = PdfWriter()
                for start, end in valid_ranges:
                    for page_num in range(start - 1, end):
                        writer.add_page(reader.pages[page_num])
                
                # Save file
                output_filename = f"{name}.pdf"
                output_path = os.path.join(session_dir, output_filename)
                with open(output_path, 'wb') as f:
                    writer.write(f)
                
                output_files.append(output_filename)
            
            if not output_files:
                return jsonify({'error': 'No valid ranges processed'}), 400
            
            # Create ZIP file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename in output_files:
                    file_path = os.path.join(session_dir, filename)
                    zip_file.write(file_path, filename)
            
            zip_buffer.seek(0)
            
            # Clean up temp files
            os.unlink(temp_path)
            for filename in output_files:
                os.unlink(os.path.join(session_dir, filename))
            os.rmdir(session_dir)
            
            # Send ZIP file
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name='split-pdfs.zip'
            )
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
