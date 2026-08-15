from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import os
import json
import tempfile
import zipfile
from io import BytesIO

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

# HTML Frontend (embedded) - VIP PDF Splitter Design with Loader
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIP PDF Splitter</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --paper: #f2ecdd;
            --paper-card: #fbf8f0;
            --ink: #1e2a3f;
            --ink-soft: #4d5a70;
            --rule: #d8cfb6;
            --cut: #b5432a;
            --cut-soft: #e7b6a4;
            --brass: #a3813f;
            --sage: #4c6b53;
            --sage-soft: #d7e4d4;
            --rust: #9a3324;
            --rust-soft: #f1d3cb;
            --gold: #c9a84c;
            --gold-soft: #f5edd4;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background:
                repeating-linear-gradient(0deg, rgba(30,42,63,0.025) 0px, rgba(30,42,63,0.025) 1px, transparent 1px, transparent 26px),
                var(--paper);
            min-height: 100vh;
            padding: 32px 24px 64px;
            color: var(--ink);
        }

        .app-container {
            max-width: 1180px;
            margin: 0 auto;
        }

        /* ---------- HEADER: title plate ---------- */
        .header {
            background: var(--ink);
            border-radius: 4px;
            padding: 28px 36px;
            margin-bottom: 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
            position: relative;
            box-shadow: 0 10px 24px rgba(30,42,63,0.18);
        }

        .header::before {
            content: '';
            position: absolute;
            inset: 6px;
            border: 1px solid rgba(242,236,221,0.18);
            border-radius: 2px;
            pointer-events: none;
        }

        .header-left {
            display: flex;
            align-items: baseline;
            gap: 14px;
        }

        .header-mark {
            font-family: 'Fraunces', serif;
            font-size: 34px;
            font-weight: 700;
            color: var(--gold);
            letter-spacing: 0.5px;
        }

        .header h1 {
            font-family: 'Fraunces', serif;
            font-size: 26px;
            font-weight: 600;
            color: var(--paper);
            letter-spacing: 0.2px;
        }

        .header h1 .vip {
            color: var(--gold);
            font-weight: 700;
        }

        .header-subtitle {
            display: block;
            color: #b7c0d1;
            font-size: 12.5px;
            font-weight: 400;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            margin-top: 4px;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-badge {
            padding: 7px 14px;
            border-radius: 2px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.4px;
            background: rgba(242,236,221,0.1);
            color: #cdd4e0;
            border: 1px solid rgba(242,236,221,0.22);
            font-family: 'IBM Plex Mono', monospace;
        }

        .status-badge.active {
            background: var(--gold-soft);
            color: #7a6520;
            border-color: var(--gold);
        }

        /* ---------- shared card / ledger sheet ---------- */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
        }

        .card {
            background: var(--paper-card);
            border-radius: 3px;
            padding: 28px;
            border: 1px solid var(--rule);
            box-shadow: 0 1px 0 rgba(30,42,63,0.03);
            position: relative;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 22px;
            flex-wrap: wrap;
            gap: 12px;
            padding-bottom: 16px;
            border-bottom: 1px dashed var(--rule);
        }

        .card-title {
            font-family: 'Fraunces', serif;
            font-size: 19px;
            font-weight: 600;
            color: var(--ink);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-title .eyebrow {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            font-weight: 500;
            color: var(--brass);
            letter-spacing: 0.08em;
        }

        .card-title .badge {
            background: var(--paper);
            color: var(--ink-soft);
            padding: 3px 10px;
            border-radius: 2px;
            font-size: 11.5px;
            font-weight: 600;
            font-family: 'IBM Plex Mono', monospace;
            border: 1px solid var(--rule);
        }

        /* ---------- upload tray ---------- */
        .upload-zone {
            border: 2px dashed var(--rule);
            border-radius: 3px;
            padding: 44px 24px;
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
            background:
                repeating-linear-gradient(135deg, rgba(179,67,42,0.035) 0px, rgba(179,67,42,0.035) 2px, transparent 2px, transparent 14px),
                var(--paper);
            position: relative;
        }

        .upload-zone:hover {
            border-color: var(--cut);
            background:
                repeating-linear-gradient(135deg, rgba(179,67,42,0.05) 0px, rgba(179,67,42,0.05) 2px, transparent 2px, transparent 14px),
                #f6ede4;
        }

        .upload-zone.dragover {
            border-color: var(--cut);
            border-style: solid;
            background: #f6ede4;
            transform: scale(1.005);
        }

        .upload-zone.has-file {
            border-color: var(--sage);
            border-style: solid;
            background: var(--paper-card);
            padding: 22px;
        }

        .upload-icon {
            font-family: 'Fraunces', serif;
            font-size: 15px;
            color: var(--brass);
            letter-spacing: 0.1em;
            text-transform: uppercase;
            display: block;
            margin-bottom: 10px;
        }

        .upload-zone h3 {
            font-family: 'Fraunces', serif;
            font-size: 20px;
            font-weight: 600;
            color: var(--ink);
            margin-bottom: 4px;
        }

        .upload-zone p {
            color: var(--ink-soft);
            font-size: 13.5px;
        }

        .upload-zone .file-info {
            display: none;
            align-items: center;
            justify-content: center;
            gap: 16px;
            margin-top: 12px;
            padding: 14px 20px;
            background: var(--paper);
            border-radius: 2px;
            border: 1px solid var(--rule);
        }

        .upload-zone .file-info.show {
            display: flex;
        }

        .file-info .file-name {
            font-weight: 600;
            color: var(--ink);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 13px;
        }

        .file-info .file-size {
            color: var(--ink-soft);
            font-size: 12.5px;
            font-family: 'IBM Plex Mono', monospace;
        }

        .file-info .remove-btn {
            background: var(--rust-soft);
            border: none;
            color: var(--rust);
            padding: 5px 12px;
            border-radius: 2px;
            cursor: pointer;
            font-size: 12.5px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .file-info .remove-btn:hover {
            background: #e6b6ab;
        }

        #fileInput {
            display: none;
        }

        /* ---------- toolbar ---------- */
        .toolbar {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            align-items: center;
        }

        .btn {
            padding: 10px 18px;
            border: 1px solid transparent;
            border-radius: 2px;
            font-weight: 600;
            font-size: 13px;
            letter-spacing: 0.2px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
            font-family: 'Inter', sans-serif;
            position: relative;
        }

        .btn:active {
            transform: scale(0.97);
        }

        .btn-primary {
            background: var(--ink);
            color: var(--paper);
        }

        .btn-primary:hover {
            background: #2a3a56;
        }

        .btn-success {
            background: var(--cut);
            color: #fff5ee;
        }

        .btn-success:hover {
            background: #9c3a24;
        }

        .btn-success:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            box-shadow: none;
        }

        .btn-secondary {
            background: transparent;
            color: var(--ink);
            border-color: var(--rule);
        }

        .btn-secondary:hover {
            background: var(--paper);
            border-color: var(--ink-soft);
        }

        .btn-danger {
            background: transparent;
            color: var(--rust);
            border-color: var(--rust-soft);
        }

        .btn-danger:hover {
            background: var(--rust-soft);
        }

        .btn-gold {
            background: var(--gold);
            color: var(--ink);
        }

        .btn-gold:hover {
            background: #b8953a;
            box-shadow: 0 4px 12px rgba(201, 168, 76, 0.35);
        }

        .btn-gold:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            box-shadow: none;
        }

        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
        }

        /* Button Loader */
        .btn-loader {
            display: none;
            width: 18px;
            height: 18px;
            border: 2.5px solid rgba(30,42,63,0.15);
            border-top-color: var(--ink);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            flex-shrink: 0;
        }

        .btn.loading .btn-loader {
            display: inline-block;
        }

        .btn.loading .btn-text {
            display: none;
        }

        .btn.loading .btn-icon {
            display: none;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Full Page Overlay Loader */
        .overlay-loader {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(30,42,63,0.7);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 24px;
        }

        .overlay-loader.show {
            display: flex;
        }

        .overlay-loader .loader-box {
            background: var(--paper-card);
            padding: 48px 56px;
            border-radius: 4px;
            border: 1px solid var(--rule);
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
            max-width: 420px;
            position: relative;
            overflow: hidden;
        }

        .overlay-loader .loader-box::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--gold), var(--cut), var(--gold));
            background-size: 200% 100%;
            animation: shimmer 1.5s ease-in-out infinite;
        }

        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }

        .overlay-loader .loader-spinner {
            width: 52px;
            height: 52px;
            border: 4px solid var(--rule);
            border-top-color: var(--gold);
            border-radius: 50%;
            animation: spin 0.9s linear infinite;
            margin: 0 auto 16px;
        }

        .overlay-loader h2 {
            font-family: 'Fraunces', serif;
            font-size: 22px;
            font-weight: 600;
            color: var(--ink);
            margin-bottom: 6px;
        }

        .overlay-loader p {
            color: var(--ink-soft);
            font-size: 14px;
        }

        .overlay-loader .loader-progress {
            margin-top: 20px;
            width: 100%;
            height: 3px;
            background: var(--rule);
            border-radius: 2px;
            overflow: hidden;
        }

        .overlay-loader .loader-progress .fill {
            height: 100%;
            background: var(--gold);
            border-radius: 2px;
            transition: width 0.4s ease;
            width: 0%;
        }

        .overlay-loader .loader-status {
            margin-top: 10px;
            font-size: 12px;
            color: var(--ink-soft);
            font-family: 'IBM Plex Mono', monospace;
        }

        /* ---------- ledger table ---------- */
        .table-wrapper {
            overflow-x: auto;
            border-radius: 2px;
            border: 1px solid var(--rule);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        thead {
            background: var(--ink);
        }

        th {
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: var(--paper);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-family: 'IBM Plex Mono', monospace;
        }

        td {
            padding: 10px 16px;
            border-bottom: 1px dashed var(--rule);
            vertical-align: middle;
            background: var(--paper-card);
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: #f6f1e6;
        }

        .range-input {
            width: 100%;
            padding: 9px 12px;
            border: 1px solid var(--rule);
            border-radius: 2px;
            font-size: 13.5px;
            transition: all 0.2s;
            font-family: 'IBM Plex Mono', monospace;
            background: var(--paper);
            color: var(--ink);
        }

        .range-input::placeholder {
            color: #a9a08a;
        }

        .range-input:focus {
            outline: none;
            border-color: var(--cut);
            box-shadow: 0 0 0 3px rgba(181,67,42,0.12);
            background: #fffdf8;
        }

        .range-input.name-input {
            max-width: 220px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
        }

        .range-input.range-text {
            min-width: 190px;
        }

        .delete-btn {
            background: none;
            border: 1px dashed var(--rule);
            color: #a9a08a;
            cursor: pointer;
            padding: 6px 10px;
            border-radius: 2px;
            transition: all 0.2s;
            font-size: 14px;
            font-family: 'IBM Plex Mono', monospace;
        }

        .delete-btn:hover {
            border-color: var(--rust);
            color: var(--rust);
            background: var(--rust-soft);
        }

        .add-row-btn {
            width: 100%;
            padding: 13px;
            border: 1px dashed var(--rule);
            border-radius: 2px;
            background: none;
            color: var(--ink-soft);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s;
            margin-top: 12px;
            font-size: 13px;
            font-family: 'IBM Plex Mono', monospace;
            letter-spacing: 0.03em;
        }

        .add-row-btn:hover {
            border-color: var(--cut);
            color: var(--cut);
            background: #f9f2ec;
        }

        /* ---------- status / progress ---------- */
        .status-container {
            margin-top: 20px;
        }

        .status-message {
            padding: 13px 18px;
            border-radius: 2px;
            display: none;
            align-items: center;
            gap: 12px;
            font-size: 13.5px;
            font-weight: 500;
            border-left: 3px solid transparent;
        }

        .status-message.show {
            display: flex;
        }

        .status-message.info {
            background: #e7ecf3;
            color: #2a3a56;
            border-left-color: var(--ink);
        }

        .status-message.success {
            background: var(--sage-soft);
            color: #2c4530;
            border-left-color: var(--sage);
        }

        .status-message.error {
            background: var(--rust-soft);
            color: var(--rust);
            border-left-color: var(--rust);
        }

        .status-message .spinner {
            width: 16px;
            height: 16px;
            border: 2.5px solid rgba(0,0,0,0.12);
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            flex-shrink: 0;
        }

        .progress-wrapper {
            margin-top: 18px;
            display: none;
        }

        .progress-wrapper.show {
            display: block;
        }

        .progress-track {
            width: 100%;
            height: 4px;
            background: var(--rule);
            border-radius: 2px;
            overflow: hidden;
            position: relative;
        }

        .progress-track::after {
            content: '';
            position: absolute;
            inset: 0;
            background-image: repeating-linear-gradient(90deg, transparent 0, transparent 9px, rgba(30,42,63,0.15) 9px, rgba(30,42,63,0.15) 10px);
        }

        .progress-fill {
            height: 100%;
            background: var(--gold);
            transition: width 0.4s ease;
            width: 0%;
            position: relative;
            z-index: 1;
        }

        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
            font-size: 12px;
            color: var(--ink-soft);
            font-family: 'IBM Plex Mono', monospace;
        }

        /* ---------- output tray ---------- */
        .export-section {
            margin-top: 22px;
            padding: 22px;
            background: var(--paper);
            border-radius: 2px;
            display: none;
            border: 1px solid var(--rule);
            border-top: 3px solid var(--gold);
        }

        .export-section.show {
            display: block;
        }

        .export-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .export-header h3 {
            font-family: 'Fraunces', serif;
            font-size: 17px;
            font-weight: 600;
            color: var(--ink);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .export-header span {
            font-size: 12px;
            color: var(--ink-soft);
            font-family: 'IBM Plex Mono', monospace;
        }

        .export-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
            gap: 8px;
        }

        .export-item {
            background: var(--paper-card);
            padding: 10px 14px;
            border-radius: 2px;
            border: 1px solid var(--rule);
            border-left: 3px solid var(--gold);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12.5px;
            color: var(--ink);
            font-family: 'IBM Plex Mono', monospace;
        }

        .export-item .check {
            color: var(--sage);
            font-weight: 700;
        }

        .export-actions {
            margin-top: 18px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        .footer {
            margin-top: 36px;
            text-align: center;
            color: #a9a08a;
            font-size: 12px;
            font-family: 'IBM Plex Mono', monospace;
            letter-spacing: 0.03em;
            padding: 16px;
        }

        @media (max-width: 768px) {
            body {
                padding: 16px 12px;
            }

            .header {
                padding: 20px;
                flex-direction: column;
                align-items: stretch;
            }

            .header-left {
                flex-direction: column;
                align-items: flex-start;
                gap: 4px;
            }

            .header-right {
                flex-wrap: wrap;
            }

            .card {
                padding: 18px;
            }

            .upload-zone {
                padding: 30px 14px;
            }

            .toolbar {
                flex-direction: column;
                align-items: stretch;
            }

            .toolbar .btn {
                width: 100%;
                justify-content: center;
            }

            .toolbar span {
                text-align: center;
            }

            .range-input.name-input {
                max-width: 100%;
            }

            .range-input.range-text {
                min-width: 100%;
            }

            td {
                padding: 8px 10px;
            }

            .export-grid {
                grid-template-columns: 1fr;
            }

            .overlay-loader .loader-box {
                padding: 32px 24px;
                margin: 16px;
            }
        }

        @media (min-width: 769px) and (max-width: 1024px) {
            .card {
                padding: 22px;
            }
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: var(--paper);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--rule);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--gold);
        }
    </style>
</head>
<body>
    <!-- Overlay Loader -->
    <div class="overlay-loader" id="overlayLoader">
        <div class="loader-box">
            <div class="loader-spinner"></div>
            <h2 id="loaderTitle">Processing Your PDF</h2>
            <p id="loaderDesc">Please wait while we split your document...</p>
            <div class="loader-progress">
                <div class="fill" id="loaderProgressFill"></div>
            </div>
            <div class="loader-status" id="loaderStatus">0%</div>
        </div>
    </div>

    <div class="app-container">
        <header class="header">
            <div class="header-left">
                <span class="header-mark">✂</span>
                <div>
                    <h1><span class="vip">VIP</span> PDF Splitter</h1>
                    <span class="header-subtitle">Cut any PDF along your own page numbers</span>
                </div>
            </div>
            <div class="header-right">
                <span class="status-badge" id="systemStatus">STANDBY</span>
                <span class="status-badge" id="pageCount">0 PAGES</span>
            </div>
        </header>

        <div class="main-grid">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <span class="eyebrow">01</span>
                        Select Your PDF
                        <span class="badge">Required</span>
                    </div>
                    <span style="font-size:12px; color:var(--ink-soft); font-family:'IBM Plex Mono',monospace;">.pdf only</span>
                </div>

                <div class="upload-zone" id="uploadZone">
                    <span class="upload-icon">— place document on the tray —</span>
                    <h3>Drop your PDF here</h3>
                    <p>or click to browse your files</p>
                    <input type="file" id="fileInput" accept=".pdf">

                    <div class="file-info" id="fileInfo">
                        <span class="file-name" id="fileName">document.pdf</span>
                        <span class="file-size" id="fileSize">2.4 MB</span>
                        <button class="remove-btn" id="removeFileBtn">Remove</button>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <span class="eyebrow">02</span>
                        Mark the Cuts
                        <span class="badge" id="rangeCount">0 ranges</span>
                    </div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <button class="btn btn-gold" id="processBtn" disabled>
                            <span class="btn-icon">✂</span>
                            <span class="btn-text">Get New PDFs</span>
                            <span class="btn-loader"></span>
                        </button>
                        <button class="btn btn-danger btn-sm" id="clearAllBtn">Clear Table</button>
                    </div>
                </div>

                <div class="toolbar">
                    <button class="btn btn-primary" id="addRangeBtn">Add New Range</button>
                    <button class="btn btn-secondary btn-sm" id="exampleBtn">Use Example Marks</button>
                    <span style="font-size:12px; color:#a9a08a; align-self:center; margin-left:auto; font-family:'IBM Plex Mono',monospace;">
                        ⌘ + Enter
                    </span>
                </div>

                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th style="width:25%;">PDF Name</th>
                                <th style="width:55%;">Page Range(s)</th>
                                <th style="width:20%; text-align:center;">Discard</th>
                            </tr>
                        </thead>
                        <tbody id="rangesBody">
                        </tbody>
                    </table>
                </div>

                <button class="add-row-btn" id="addRangeBtnBottom">+ Add New Range</button>

                <div class="status-container">
                    <div class="status-message" id="statusMessage">
                        <span id="statusText">Processing...</span>
                    </div>
                </div>

                <div class="progress-wrapper" id="progressWrapper">
                    <div class="progress-track">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="progress-label">
                        <span id="progressText">0%</span>
                        <span id="progressStatus">Processing...</span>
                    </div>
                </div>

                <div class="export-section" id="exportSection">
                    <div class="export-header">
                        <h3>✓ Ready for Download</h3>
                        <span>your files are stacked below</span>
                    </div>
                    <div class="export-grid" id="exportList">
                    </div>
                    <div class="export-actions">
                        <button class="btn btn-gold" id="downloadAllBtn">Download Stack as ZIP</button>
                        <button class="btn btn-secondary" id="resetBtn">Clear the Bench</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            VIP PDF Splitter — nothing you feed the press is kept on the shelf
        </div>
    </div>

    <script>
        const state = {
            ranges: [],
            uploadedFile: null,
            isProcessing: false,
            totalPages: 0
        };

        const elements = {
            uploadZone: document.getElementById('uploadZone'),
            fileInput: document.getElementById('fileInput'),
            fileInfo: document.getElementById('fileInfo'),
            fileName: document.getElementById('fileName'),
            fileSize: document.getElementById('fileSize'),
            removeFileBtn: document.getElementById('removeFileBtn'),
            rangesBody: document.getElementById('rangesBody'),
            rangeCount: document.getElementById('rangeCount'),
            addRangeBtn: document.getElementById('addRangeBtn'),
            addRangeBtnBottom: document.getElementById('addRangeBtnBottom'),
            processBtn: document.getElementById('processBtn'),
            exampleBtn: document.getElementById('exampleBtn'),
            clearAllBtn: document.getElementById('clearAllBtn'),
            downloadAllBtn: document.getElementById('downloadAllBtn'),
            resetBtn: document.getElementById('resetBtn'),
            statusMessage: document.getElementById('statusMessage'),
            statusText: document.getElementById('statusText'),
            progressWrapper: document.getElementById('progressWrapper'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            progressStatus: document.getElementById('progressStatus'),
            exportSection: document.getElementById('exportSection'),
            exportList: document.getElementById('exportList'),
            systemStatus: document.getElementById('systemStatus'),
            pageCount: document.getElementById('pageCount'),
            overlayLoader: document.getElementById('overlayLoader'),
            loaderTitle: document.getElementById('loaderTitle'),
            loaderDesc: document.getElementById('loaderDesc'),
            loaderProgressFill: document.getElementById('loaderProgressFill'),
            loaderStatus: document.getElementById('loaderStatus')
        };

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

        function updateUI() {
            const count = state.ranges.length;
            elements.rangeCount.textContent = count + ' range' + (count !== 1 ? 's' : '');
            const isDisabled = count === 0 || !state.uploadedFile || state.isProcessing;
            elements.processBtn.disabled = isDisabled;
            elements.pageCount.textContent = '📄 ' + state.totalPages + ' pages';
        }

        function showStatus(message, type = 'info') {
            const el = elements.statusMessage;
            el.className = 'status-message show ' + type;
            elements.statusText.textContent = message;
        }

        function hideStatus() {
            elements.statusMessage.className = 'status-message';
        }

        function showProgress(percent, status = 'Processing...') {
            elements.progressWrapper.classList.add('show');
            elements.progressFill.style.width = percent + '%';
            elements.progressText.textContent = percent + '%';
            elements.progressStatus.textContent = status;
        }

        function hideProgress() {
            elements.progressWrapper.classList.remove('show');
        }

        function showExport(files) {
            elements.exportSection.classList.add('show');
            elements.exportList.innerHTML = files.map(file => `
                <div class="export-item">
                    <span>${file}</span>
                    <span class="check">✓</span>
                </div>
            `).join('');
        }

        function hideExport() {
            elements.exportSection.classList.remove('show');
        }

        // Overlay Loader Controls
        function showOverlayLoader(title = 'Processing Your PDF', desc = 'Please wait while we split your document...') {
            elements.overlayLoader.classList.add('show');
            elements.loaderTitle.textContent = title;
            elements.loaderDesc.textContent = desc;
            elements.loaderProgressFill.style.width = '0%';
            elements.loaderStatus.textContent = '0%';
        }

        function updateOverlayLoader(percent, status = '') {
            elements.loaderProgressFill.style.width = percent + '%';
            elements.loaderStatus.textContent = (status || percent + '%');
        }

        function hideOverlayLoader() {
            elements.overlayLoader.classList.remove('show');
        }

        function addRangeRow(name = '', rangeStr = '') {
            const id = generateId();
            const row = document.createElement('tr');
            row.dataset.id = id;
            row.innerHTML = `
                <td>
                    <input type="text" class="range-input name-input" 
                           placeholder="e.g., chapter1" value="${name}">
                </td>
                <td>
                    <input type="text" class="range-input range-text" 
                           placeholder="e.g., 1-5, 10-15" value="${rangeStr}">
                </td>
                <td style="text-align:center;">
                    <button class="delete-btn" data-id="${id}">✕</button>
                </td>
            `;

            elements.rangesBody.appendChild(row);

            const nameInput = row.querySelector('.name-input');
            const rangeInput = row.querySelector('.range-text');
            
            state.ranges.push({
                id: id,
                name: name,
                ranges: rangeStr
            });

            nameInput.addEventListener('input', () => {
                const found = state.ranges.find(r => r.id === id);
                if (found) found.name = nameInput.value;
            });

            rangeInput.addEventListener('input', () => {
                const found = state.ranges.find(r => r.id === id);
                if (found) found.ranges = rangeInput.value;
            });

            row.querySelector('.delete-btn').addEventListener('click', () => {
                row.remove();
                const index = state.ranges.findIndex(r => r.id === id);
                if (index > -1) state.ranges.splice(index, 1);
                updateUI();
                hideExport();
            });

            updateUI();
        }

        function parseRanges(rangeStr) {
            if (!rangeStr.trim()) return null;
            
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
            
            return parsed.length > 0 ? parsed : null;
        }

        function handleFile(file) {
            if (file.type !== 'application/pdf') {
                showStatus('Please upload a valid PDF file.', 'error');
                return;
            }

            state.uploadedFile = file;
            elements.fileName.textContent = file.name;
            elements.fileSize.textContent = formatFileSize(file.size);
            elements.fileInfo.classList.add('show');
            elements.uploadZone.classList.add('has-file');
            
            state.totalPages = 0;
            showStatus('✅ Loaded "' + file.name + '"', 'success');
            updateUI();
            hideExport();
        }

        async function processPDF() {
            if (!state.uploadedFile || state.ranges.length === 0 || state.isProcessing) return;
            
            state.isProcessing = true;
            updateUI();
            hideExport();
            hideStatus();
            
            // Show overlay loader
            showOverlayLoader('Preparing Your Document', 'Validating page ranges...');
            updateOverlayLoader(5);
            
            try {
                const validatedRanges = [];
                for (const range of state.ranges) {
                    if (!range.name.trim()) {
                        showStatus('Please provide a name for all ranges.', 'error');
                        state.isProcessing = false;
                        updateUI();
                        hideOverlayLoader();
                        return;
                    }
                    
                    const parsed = parseRanges(range.ranges);
                    if (!parsed) {
                        showStatus('Invalid range format for "' + range.name + '". Use e.g., "1-5,10-15"', 'error');
                        state.isProcessing = false;
                        updateUI();
                        hideOverlayLoader();
                        return;
                    }
                    
                    validatedRanges.push({
                        name: range.name.trim(),
                        ranges: parsed
                    });
                }
                
                updateOverlayLoader(15, 'Validated ' + validatedRanges.length + ' ranges');
                
                const formData = new FormData();
                formData.append('pdf', state.uploadedFile);
                formData.append('ranges', JSON.stringify(validatedRanges));
                
                updateOverlayLoader(30, 'Uploading to server...');
                elements.loaderDesc.textContent = 'Sending your PDF to the press...';
                
                const response = await fetch('/process-pdf', {
                    method: 'POST',
                    body: formData
                });
                
                updateOverlayLoader(60, 'Processing PDF...');
                elements.loaderDesc.textContent = 'Cutting pages according to your marks...';
                
                if (!response.ok) {
                    const error = await response.text();
                    throw new Error(error || 'Failed to process PDF');
                }
                
                updateOverlayLoader(85, 'Preparing download...');
                elements.loaderDesc.textContent = 'Stacking your new PDFs...';
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'split-pdfs.zip';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                
                updateOverlayLoader(100, 'Complete!');
                elements.loaderDesc.textContent = 'Your PDFs are ready!';
                
                // Show success after a brief delay
                await new Promise(resolve => setTimeout(resolve, 600));
                
                hideOverlayLoader();
                showProgress(100, 'Complete!');
                showStatus('✅ PDF split successfully! Download started.', 'success');
                
                const fileNames = validatedRanges.map(r => r.name + '.pdf');
                showExport(fileNames);
                
            } catch (error) {
                hideOverlayLoader();
                showStatus('❌ Error: ' + error.message, 'error');
                console.error(error);
            } finally {
                state.isProcessing = false;
                updateUI();
                setTimeout(() => hideProgress(), 3000);
            }
        }

        function resetAll() {
            if (state.ranges.length > 0 || state.uploadedFile) {
                if (!confirm('This will clear all ranges and uploaded file. Continue?')) return;
            }
            
            state.ranges = [];
            state.uploadedFile = null;
            state.totalPages = 0;
            state.isProcessing = false;
            
            elements.rangesBody.innerHTML = '';
            elements.fileInfo.classList.remove('show');
            elements.uploadZone.classList.remove('has-file');
            elements.fileInput.value = '';
            hideExport();
            hideStatus();
            hideProgress();
            hideOverlayLoader();
            updateUI();
            addRangeRow();
        }

        // Event Listeners
        elements.uploadZone.addEventListener('click', () => elements.fileInput.click());
        
        elements.uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.uploadZone.classList.add('dragover');
        });
        
        elements.uploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            elements.uploadZone.classList.remove('dragover');
        });
        
        elements.uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.uploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
        
        elements.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
        
        elements.removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            state.uploadedFile = null;
            state.totalPages = 0;
            elements.fileInfo.classList.remove('show');
            elements.uploadZone.classList.remove('has-file');
            elements.fileInput.value = '';
            updateUI();
            hideStatus();
            hideExport();
        });

        elements.addRangeBtn.addEventListener('click', () => addRangeRow());
        elements.addRangeBtnBottom.addEventListener('click', () => addRangeRow());
        elements.processBtn.addEventListener('click', processPDF);
        elements.downloadAllBtn.addEventListener('click', processPDF);
        elements.resetBtn.addEventListener('click', resetAll);
        
        elements.exampleBtn.addEventListener('click', () => {
            if (state.ranges.length > 0) {
                if (!confirm('This will replace all current ranges. Continue?')) return;
            }
            
            elements.rangesBody.innerHTML = '';
            state.ranges = [];
            
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
            
            for (const [name, rangeStr] of examples) {
                addRangeRow(name, rangeStr);
            }
            
            showStatus('✅ Example ranges loaded! Upload a PDF to get started.', 'success');
        });
        
        elements.clearAllBtn.addEventListener('click', () => {
            if (state.ranges.length === 0) return;
            if (confirm('Clear all ranges?')) {
                elements.rangesBody.innerHTML = '';
                state.ranges = [];
                updateUI();
                hideExport();
                hideStatus();
                addRangeRow();
            }
        });

        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                processPDF();
            }
        });

        // Initialize
        addRangeRow();
        updateUI();
        elements.systemStatus.textContent = '● READY';
        elements.systemStatus.className = 'status-badge active';
    </script>
</body>
</html>'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
