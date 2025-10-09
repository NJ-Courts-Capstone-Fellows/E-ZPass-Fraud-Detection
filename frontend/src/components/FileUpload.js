import React, { useState, useRef } from 'react';

// Upload Icon Component
const UploadIcon = () => (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
);

// Check Icon Component
const CheckIcon = () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
);

// Error Icon Component
const ErrorIcon = () => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
);

// Loading Spinner Component
const LoadingSpinner = () => (
    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400"></div>
);

const FileUpload = ({ onUploadSuccess, onUploadError }) => {
    const [dragActive, setDragActive] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null); // 'success', 'error', null
    const [uploadMessage, setUploadMessage] = useState('');
    const [uploadSummary, setUploadSummary] = useState(null);
    const fileInputRef = useRef(null);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileInput = (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = async (file) => {
        // Reset previous status
        setUploadStatus(null);
        setUploadMessage('');
        setUploadSummary(null);

        // Validate file type
        const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(csv|xlsx|xls)$/i)) {
            setUploadStatus('error');
            setUploadMessage('Please upload a CSV or Excel file (.csv, .xlsx, .xls)');
            if (onUploadError) onUploadError('Invalid file type');
            return;
        }

        // Validate file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            setUploadStatus('error');
            setUploadMessage('File size must be less than 10MB');
            if (onUploadError) onUploadError('File too large');
            return;
        }

        setUploading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('http://localhost:5000/api/upload', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (response.ok) {
                setUploadStatus('success');
                setUploadMessage(result.message);
                setUploadSummary(result.summary);
                if (onUploadSuccess) onUploadSuccess(result);
            } else {
                setUploadStatus('error');
                setUploadMessage(result.error || 'Upload failed');
                if (onUploadError) onUploadError(result.error);
            }
        } catch (error) {
            setUploadStatus('error');
            setUploadMessage('Network error. Please check if the backend server is running.');
            if (onUploadError) onUploadError(error.message);
        } finally {
            setUploading(false);
        }
    };

    const resetUpload = () => {
        setUploadStatus(null);
        setUploadMessage('');
        setUploadSummary(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 backdrop-blur-sm border border-slate-700/50 p-6 rounded-2xl shadow-xl">
            <div className="mb-6">
                <h3 className="font-bold text-xl text-white mb-2">Upload Transaction Data</h3>
                <p className="text-sm text-gray-400">Upload CSV or Excel files containing E-ZPass transaction data</p>
            </div>

            {/* Upload Area */}
            <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                    dragActive
                        ? 'border-teal-400 bg-teal-500/10'
                        : uploadStatus === 'success'
                        ? 'border-emerald-400 bg-emerald-500/10'
                        : uploadStatus === 'error'
                        ? 'border-red-400 bg-red-500/10'
                        : 'border-slate-600 bg-slate-700/20 hover:border-teal-400 hover:bg-teal-500/5'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileInput}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={uploading}
                />

                {uploading ? (
                    <div className="flex flex-col items-center">
                        <LoadingSpinner />
                        <p className="mt-4 text-teal-400 font-medium">Processing file...</p>
                        <p className="text-sm text-gray-400 mt-2">This may take a few moments</p>
                    </div>
                ) : uploadStatus === 'success' ? (
                    <div className="flex flex-col items-center">
                        <div className="p-3 bg-emerald-500/20 rounded-full mb-4">
                            <CheckIcon />
                        </div>
                        <p className="text-emerald-400 font-medium mb-2">Upload Successful!</p>
                        <p className="text-sm text-gray-300 mb-4">{uploadMessage}</p>
                        <button
                            onClick={resetUpload}
                            className="px-4 py-2 bg-slate-700 text-gray-300 rounded-lg hover:bg-slate-600 transition-colors text-sm"
                        >
                            Upload Another File
                        </button>
                    </div>
                ) : uploadStatus === 'error' ? (
                    <div className="flex flex-col items-center">
                        <div className="p-3 bg-red-500/20 rounded-full mb-4">
                            <ErrorIcon />
                        </div>
                        <p className="text-red-400 font-medium mb-2">Upload Failed</p>
                        <p className="text-sm text-gray-300 mb-4">{uploadMessage}</p>
                        <button
                            onClick={resetUpload}
                            className="px-4 py-2 bg-slate-700 text-gray-300 rounded-lg hover:bg-slate-600 transition-colors text-sm"
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    <div className="flex flex-col items-center">
                        <div className="p-4 bg-slate-700/50 rounded-full mb-4">
                            <UploadIcon />
                        </div>
                        <p className="text-white font-medium mb-2">Drop your file here</p>
                        <p className="text-sm text-gray-400 mb-4">or click to browse</p>
                        <p className="text-xs text-gray-500">Supports CSV, XLSX, XLS files up to 10MB</p>
                    </div>
                )}
            </div>

            {/* Upload Summary */}
            {uploadSummary && (
                <div className="mt-6 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                    <h4 className="font-semibold text-emerald-400 mb-3">Upload Summary</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                            <p className="text-gray-400">Total Transactions</p>
                            <p className="text-white font-semibold">{uploadSummary.total_transactions.toLocaleString()}</p>
                        </div>
                        <div>
                            <p className="text-gray-400">Flagged</p>
                            <p className="text-amber-400 font-semibold">{uploadSummary.flagged_transactions}</p>
                        </div>
                        <div>
                            <p className="text-gray-400">Investigating</p>
                            <p className="text-red-400 font-semibold">{uploadSummary.investigating_transactions}</p>
                        </div>
                        <div>
                            <p className="text-gray-400">Total Amount</p>
                            <p className="text-white font-semibold">${Math.abs(uploadSummary.total_amount).toLocaleString()}</p>
                        </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-emerald-500/20">
                        <p className="text-xs text-gray-400">
                            Date Range: {uploadSummary.date_range.start} to {uploadSummary.date_range.end}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                            Agencies: {uploadSummary.agencies.join(', ')}
                        </p>
                    </div>
                </div>
            )}

            {/* File Requirements */}
            <div className="mt-6 p-4 bg-slate-700/30 rounded-xl">
                <h4 className="font-semibold text-gray-300 mb-2">File Requirements</h4>
                <ul className="text-sm text-gray-400 space-y-1">
                    <li>- File formats: CSV, XLSX, XLS</li>
                    <li>- Maximum file size: 10MB</li>
                    <li>- Required columns: posting_date, transaction_date, tag_plate_number, agency, exit_time, exit_plaza, amount</li>
                    <li>- Data will be automatically processed for fraud detection</li>
                </ul>
            </div>
        </div>
    );
};

export default FileUpload;
