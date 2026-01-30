#!/usr/bin/env python3
"""
SmartPneu Local Print Agent

This script runs on your local Mac to:
1. Download labels from Railway server
2. Save them locally
3. Provide a web UI to view and print labels manually

Web interface: http://localhost:5050

Configuration via environment variables or .env file:
    SERVER_URL - Railway app URL (e.g., https://your-app.railway.app)
    PRINTER_NAME - Local printer name (default: Brother_MFC_L3710CW_series)
    POLL_INTERVAL - Seconds between polls (default: 5)
    PRINT_AGENT_API_KEY - API key for authentication (optional)
    LABELS_FOLDER - Where to save labels (default: ~/Documents/SmartPneu-Labels)
    LOCAL_PORT - Port for local web interface (default: 5050)
"""

import os
import time
import base64
import json
import requests
import subprocess
import threading
import shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, jsonify, send_file, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:5000')
PRINTER_NAME = os.getenv('PRINTER_NAME', 'Brother_MFC_L3710CW_series')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 5))
API_KEY = os.getenv('PRINT_AGENT_API_KEY', '')
LABELS_FOLDER = os.getenv('LABELS_FOLDER', os.path.expanduser('~/Documents/SmartPneu-Labels'))
ARCHIVE_FOLDER = os.path.join(LABELS_FOLDER, '_archive')
LOCAL_PORT = int(os.getenv('LOCAL_PORT', 5050))

# Track pending count for UI
pending_on_server = 0

# Flask app for local web interface
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SmartPneu Labels</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="10">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }
        h1 { color: #333; margin-bottom: 20px; }
        .status { 
            background: #e8f5e9; padding: 15px 20px; border-radius: 8px; 
            margin-bottom: 20px; display: flex; align-items: center; gap: 15px;
            flex-wrap: wrap;
        }
        .status.warning { background: #fff3e0; }
        .status-item { display: flex; align-items: center; gap: 8px; }
        .badge { 
            background: #1976d2; color: white; padding: 2px 8px; 
            border-radius: 12px; font-size: 13px; font-weight: 600;
        }
        .badge.pending { background: #ff9800; }
        .badge.success { background: #43a047; }
        .badge.archive { background: #9e9e9e; }
        .tabs {
            display: flex; gap: 10px; margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px; border: none; border-radius: 8px;
            cursor: pointer; font-size: 14px; font-weight: 500;
            background: #e0e0e0; color: #666;
        }
        .tab.active { background: #1976d2; color: white; }
        .tab:hover:not(.active) { background: #d0d0d0; }
        .date-group { 
            background: white; border-radius: 12px; padding: 20px; 
            margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .date-header { 
            font-size: 18px; font-weight: 600; color: #1976d2; 
            margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e3f2fd;
            display: flex; justify-content: space-between; align-items: center;
        }
        .date-header.archive { color: #757575; border-bottom-color: #e0e0e0; }
        .labels-grid { 
            display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
            gap: 15px;
        }
        .label-card { 
            border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px;
            background: #fafafa; transition: all 0.2s;
        }
        .label-card:hover { border-color: #1976d2; background: #fff; }
        .label-card.printed { border-left: 4px solid #43a047; }
        .label-card.archived { opacity: 0.7; border-left: 4px solid #9e9e9e; }
        .label-name { font-weight: 500; margin-bottom: 8px; word-break: break-all; }
        .label-meta { color: #666; font-size: 13px; margin-bottom: 12px; }
        .btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn { 
            flex: 1; padding: 10px 12px; border: none; border-radius: 6px; 
            cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;
            min-width: 70px;
        }
        .btn-view { background: #e3f2fd; color: #1976d2; }
        .btn-view:hover { background: #bbdefb; }
        .btn-print { background: #1976d2; color: white; }
        .btn-print:hover { background: #1565c0; }
        .btn-print:disabled { background: #ccc; cursor: not-allowed; }
        .btn-archive { background: #f5f5f5; color: #757575; border: 1px solid #e0e0e0; }
        .btn-archive:hover { background: #eeeeee; }
        .btn-restore { background: #fff3e0; color: #f57c00; }
        .btn-restore:hover { background: #ffe0b2; }
        .btn-print-all { background: #43a047; color: white; padding: 8px 16px; }
        .btn-print-all:hover { background: #388e3c; }
        .btn-archive-all { background: #9e9e9e; color: white; padding: 8px 16px; margin-left: 8px; }
        .btn-archive-all:hover { background: #757575; }
        .empty { text-align: center; padding: 40px; color: #666; }
        .toast {
            position: fixed; bottom: 20px; right: 20px; padding: 15px 25px;
            background: #333; color: white; border-radius: 8px;
            display: none; animation: fadeIn 0.3s; z-index: 1000;
        }
        .toast.success { background: #43a047; }
        .toast.error { background: #e53935; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } }
        .header { display: flex; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        .header h1 { margin: 0; flex: 1; }
        .refresh-btn {
            background: #fff; border: 1px solid #ddd; padding: 8px 16px;
            border-radius: 6px; cursor: pointer;
        }
        .refresh-btn:hover { background: #f5f5f5; }
        .content-section { display: none; }
        .content-section.active { display: block; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏷️ SmartPneu Labels</h1>
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
    </div>
    
    <div class="status {% if pending_on_server > 0 %}warning{% endif %}">
        <div class="status-item">
            🖨️ <strong>{{ printer }}</strong>
        </div>
        <div class="status-item">
            📁 <span class="badge success">{{ total_labels }}</span> labels
        </div>
        <div class="status-item">
            📦 <span class="badge archive">{{ total_archived }}</span> archived
        </div>
        {% if pending_on_server > 0 %}
        <div class="status-item">
            ⏳ <span class="badge pending">{{ pending_on_server }}</span> downloading...
        </div>
        {% endif %}
    </div>
    
    <div class="tabs">
        <button class="tab active" onclick="showTab('labels')">📁 Labels ({{ total_labels }})</button>
        <button class="tab" onclick="showTab('archive')">📦 Archive ({{ total_archived }})</button>
    </div>
    
    <!-- Labels Section -->
    <div id="labels-section" class="content-section active">
        {% if labels_by_date %}
            {% for date, labels in labels_by_date.items() %}
            <div class="date-group">
                <div class="date-header">
                    <span>📅 {{ date }} ({{ labels|length }} labels)</span>
                    <div>
                        <button class="btn btn-print-all" onclick="printAllInGroup('{{ date }}')">
                            🖨️ Print All
                        </button>
                        <button class="btn btn-archive-all" onclick="archiveAllInGroup('{{ date }}')">
                            📦 Archive All
                        </button>
                    </div>
                </div>
                <div class="labels-grid">
                    {% for label in labels %}
                    <div class="label-card" data-date="{{ date }}" data-path="{{ label.path }}">
                        <div class="label-name">{{ label.sku }}</div>
                        <div class="label-meta">
                            ⏰ {{ label.time }} · {{ label.name }}
                        </div>
                        <div class="btn-group">
                            <a href="/view/{{ label.path }}" target="_blank" class="btn btn-view">👁️</a>
                            <button class="btn btn-print" onclick="printLabel('{{ label.path }}', this)">🖨️ Print</button>
                            <button class="btn btn-archive" onclick="archiveLabel('{{ label.path }}')">📦</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="date-group">
                <div class="empty">
                    <p style="font-size: 48px; margin: 0;">📭</p>
                    <p><strong>No labels yet</strong></p>
                    <p>Create products in the web app and labels will appear here</p>
                </div>
            </div>
        {% endif %}
    </div>
    
    <!-- Archive Section -->
    <div id="archive-section" class="content-section">
        {% if archived_by_date %}
            {% for date, labels in archived_by_date.items() %}
            <div class="date-group">
                <div class="date-header archive">
                    <span>📦 {{ date }} ({{ labels|length }} archived)</span>
                </div>
                <div class="labels-grid">
                    {% for label in labels %}
                    <div class="label-card archived" data-path="{{ label.path }}">
                        <div class="label-name">{{ label.sku }}</div>
                        <div class="label-meta">
                            ⏰ {{ label.time }} · {{ label.name }}
                        </div>
                        <div class="btn-group">
                            <a href="/view-archive/{{ label.path }}" target="_blank" class="btn btn-view">👁️</a>
                            <button class="btn btn-restore" onclick="restoreLabel('{{ label.path }}')">↩️ Restore</button>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="date-group">
                <div class="empty">
                    <p style="font-size: 48px; margin: 0;">📦</p>
                    <p><strong>No archived labels</strong></p>
                    <p>Archived labels will appear here</p>
                </div>
            </div>
        {% endif %}
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        function showTab(tab) {
            // Update tabs
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update sections
            document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
            document.getElementById(tab + '-section').classList.add('active');
        }
        
        function showToast(message, type) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type;
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 3000);
        }
        
        async function printLabel(path, btn) {
            if (btn) {
                btn.disabled = true;
                btn.textContent = '⏳';
            }
            try {
                const response = await fetch('/print/' + path, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    showToast('✅ Sent to printer!', 'success');
                    if (btn) btn.closest('.label-card').classList.add('printed');
                } else {
                    showToast('❌ ' + data.error, 'error');
                }
            } catch (e) {
                showToast('❌ Error: ' + e.message, 'error');
            }
            if (btn) {
                btn.disabled = false;
                btn.textContent = '🖨️ Print';
            }
        }
        
        async function archiveLabel(path) {
            try {
                const response = await fetch('/archive/' + path, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    showToast('📦 Archived!', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast('❌ ' + data.error, 'error');
                }
            } catch (e) {
                showToast('❌ Error: ' + e.message, 'error');
            }
        }
        
        async function restoreLabel(path) {
            try {
                const response = await fetch('/restore/' + path, { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    showToast('↩️ Restored!', 'success');
                    setTimeout(() => location.reload(), 500);
                } else {
                    showToast('❌ ' + data.error, 'error');
                }
            } catch (e) {
                showToast('❌ Error: ' + e.message, 'error');
            }
        }
        
        async function printAllInGroup(date) {
            const cards = document.querySelectorAll(`.label-card[data-date="${date}"]`);
            showToast(`🖨️ Printing ${cards.length} labels...`, 'success');
            
            for (const card of cards) {
                const path = card.dataset.path;
                const btn = card.querySelector('.btn-print');
                await printLabel(path, btn);
                await new Promise(r => setTimeout(r, 500));
            }
        }
        
        async function archiveAllInGroup(date) {
            const cards = document.querySelectorAll(`.label-card[data-date="${date}"]`);
            if (!confirm(`Archive all ${cards.length} labels from ${date}?`)) return;
            
            showToast(`📦 Archiving ${cards.length} labels...`, 'success');
            
            for (const card of cards) {
                const path = card.dataset.path;
                try {
                    await fetch('/archive/' + path, { method: 'POST' });
                } catch (e) {}
            }
            
            setTimeout(() => location.reload(), 500);
        }
    </script>
</body>
</html>
"""


def ensure_folders():
    """Create labels and archive folders if they don't exist"""
    Path(LABELS_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(ARCHIVE_FOLDER).mkdir(parents=True, exist_ok=True)


def get_labels_from_folder(base_folder):
    """Get all labels organized by date from a folder"""
    labels_by_date = {}
    total = 0
    
    if not os.path.exists(base_folder):
        return labels_by_date, total
    
    # Get all date folders, sorted newest first
    date_folders = sorted(
        [d for d in os.listdir(base_folder) 
         if os.path.isdir(os.path.join(base_folder, d)) and not d.startswith('_')],
        reverse=True
    )
    
    for date_folder in date_folders:
        folder_path = os.path.join(base_folder, date_folder)
        pdfs = sorted(
            [f for f in os.listdir(folder_path) if f.endswith('.pdf')],
            reverse=True
        )
        
        if pdfs:
            labels_by_date[date_folder] = []
            for pdf in pdfs:
                # Extract time and SKU from filename (HHMMSS_SKU.pdf)
                parts = pdf.replace('.pdf', '').split('_', 1)
                time_str = parts[0] if len(parts) > 1 else ''
                sku = parts[1] if len(parts) > 1 else pdf.replace('.pdf', '')
                
                if len(time_str) == 6:
                    time_formatted = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
                else:
                    time_formatted = ''
                
                labels_by_date[date_folder].append({
                    'name': pdf,
                    'path': f"{date_folder}/{pdf}",
                    'time': time_formatted,
                    'sku': sku
                })
                total += 1
    
    return labels_by_date, total


def get_all_labels():
    """Get all active labels"""
    return get_labels_from_folder(LABELS_FOLDER)


def get_archived_labels():
    """Get all archived labels"""
    return get_labels_from_folder(ARCHIVE_FOLDER)


def print_pdf(pdf_path):
    """Send PDF to Brother printer"""
    cmd = [
        'lp',
        '-d', PRINTER_NAME,
        '-o', 'media=Custom.120x220mm,labels',
        '-o', 'InputSlot=Auto',
        pdf_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


# Flask routes
@app.route('/')
def index():
    labels_by_date, total = get_all_labels()
    archived_by_date, total_archived = get_archived_labels()
    return render_template_string(
        HTML_TEMPLATE,
        labels_by_date=labels_by_date,
        total_labels=total,
        archived_by_date=archived_by_date,
        total_archived=total_archived,
        printer=PRINTER_NAME,
        pending_on_server=pending_on_server
    )


@app.route('/view/<path:filepath>')
def view_label(filepath):
    full_path = os.path.join(LABELS_FOLDER, filepath)
    if os.path.exists(full_path):
        return send_file(full_path, mimetype='application/pdf')
    return "Not found", 404


@app.route('/view-archive/<path:filepath>')
def view_archived_label(filepath):
    full_path = os.path.join(ARCHIVE_FOLDER, filepath)
    if os.path.exists(full_path):
        return send_file(full_path, mimetype='application/pdf')
    return "Not found", 404


@app.route('/print/<path:filepath>', methods=['POST'])
def reprint_label(filepath):
    full_path = os.path.join(LABELS_FOLDER, filepath)
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'error': 'File not found'})
    
    success, message = print_pdf(full_path)
    return jsonify({'success': success, 'error': message if not success else None})


@app.route('/archive/<path:filepath>', methods=['POST'])
def archive_label(filepath):
    """Move a label to archive"""
    src_path = os.path.join(LABELS_FOLDER, filepath)
    if not os.path.exists(src_path):
        return jsonify({'success': False, 'error': 'File not found'})
    
    try:
        # Create archive date folder if needed
        date_folder = os.path.dirname(filepath)
        archive_date_folder = os.path.join(ARCHIVE_FOLDER, date_folder)
        Path(archive_date_folder).mkdir(parents=True, exist_ok=True)
        
        # Move file
        dst_path = os.path.join(ARCHIVE_FOLDER, filepath)
        shutil.move(src_path, dst_path)
        
        # Clean up empty source folder
        src_folder = os.path.dirname(src_path)
        if os.path.isdir(src_folder) and not os.listdir(src_folder):
            os.rmdir(src_folder)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/restore/<path:filepath>', methods=['POST'])
def restore_label(filepath):
    """Restore a label from archive"""
    src_path = os.path.join(ARCHIVE_FOLDER, filepath)
    if not os.path.exists(src_path):
        return jsonify({'success': False, 'error': 'File not found'})
    
    try:
        # Create labels date folder if needed
        date_folder = os.path.dirname(filepath)
        labels_date_folder = os.path.join(LABELS_FOLDER, date_folder)
        Path(labels_date_folder).mkdir(parents=True, exist_ok=True)
        
        # Move file
        dst_path = os.path.join(LABELS_FOLDER, filepath)
        shutil.move(src_path, dst_path)
        
        # Clean up empty archive folder
        src_folder = os.path.dirname(src_path)
        if os.path.isdir(src_folder) and not os.listdir(src_folder):
            os.rmdir(src_folder)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/labels')
def api_labels():
    labels_by_date, total = get_all_labels()
    archived_by_date, total_archived = get_archived_labels()
    return jsonify({
        'labels': labels_by_date, 
        'total': total,
        'archived': archived_by_date,
        'total_archived': total_archived,
        'pending_on_server': pending_on_server
    })


@app.route('/api/status')
def api_status():
    return jsonify({
        'printer': PRINTER_NAME,
        'server': SERVER_URL,
        'pending_on_server': pending_on_server,
        'labels_folder': LABELS_FOLDER
    })


# Print agent functions
def get_pending_jobs():
    """Fetch pending print jobs from server"""
    global pending_on_server
    try:
        headers = {}
        if API_KEY:
            headers['X-API-Key'] = API_KEY
        
        response = requests.get(
            f"{SERVER_URL.rstrip('/')}/api/print-jobs",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            jobs = response.json().get('jobs', [])
            pending_on_server = len(jobs)
            return jobs
        elif response.status_code == 401:
            print("❌ Unauthorized - check your API key")
            return []
        else:
            print(f"⚠️  Error fetching jobs: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Connection error: {e}")
        return []


def save_pdf_from_base64(pdf_base64, filename, sku):
    """Decode base64 PDF and save to labels folder"""
    try:
        pdf_data = base64.b64decode(pdf_base64)
        
        # Create dated subfolder
        date_folder = datetime.now().strftime("%Y-%m-%d")
        folder_path = os.path.join(LABELS_FOLDER, date_folder)
        Path(folder_path).mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to filename
        timestamp = datetime.now().strftime("%H%M%S")
        safe_filename = f"{timestamp}_{sku}.pdf"
        pdf_path = os.path.join(folder_path, safe_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)
        
        return pdf_path
    except Exception as e:
        print(f"⚠️  Error saving PDF: {e}")
        return None


def mark_job_downloaded(job_id):
    """Notify server that job was downloaded"""
    try:
        headers = {}
        if API_KEY:
            headers['X-API-Key'] = API_KEY
        
        response = requests.post(
            f"{SERVER_URL.rstrip('/')}/api/print-jobs/{job_id}/complete",
            headers=headers,
            json={'success': True, 'message': 'Downloaded to local agent'},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️  Failed to mark job downloaded: {e}")
        return False


def process_job(job):
    """Process a single print job - download and save only (no auto-print)"""
    job_id = job['id']
    pdf_base64 = job.get('pdf_data')
    filename = job.get('pdf_filename', f'{job_id}.pdf')
    sku = job.get('sku', 'unknown')
    
    print(f"📥 Downloading: {sku}")
    
    if not pdf_base64:
        print(f"❌ No PDF data in job")
        mark_job_downloaded(job_id)
        return False
    
    # Save PDF to labels folder
    pdf_path = save_pdf_from_base64(pdf_base64, filename, sku)
    if not pdf_path:
        mark_job_downloaded(job_id)
        return False
    
    print(f"💾 Saved: {pdf_path}")
    
    # Mark as downloaded on server (removes from pending queue)
    mark_job_downloaded(job_id)
    
    return True


def check_printer():
    """Check if configured printer is available"""
    try:
        result = subprocess.run(['lpstat', '-p', PRINTER_NAME], capture_output=True, text=True)
        if result.returncode == 0 and 'enabled' in result.stdout.lower():
            return True
        return False
    except:
        return False


def poll_loop():
    """Background thread to poll for print jobs"""
    global pending_on_server
    while True:
        try:
            jobs = get_pending_jobs()
            
            if jobs:
                print(f"📋 Found {len(jobs)} new label(s)")
                for job in jobs:
                    process_job(job)
                pending_on_server = 0
            
            time.sleep(POLL_INTERVAL)
            
        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(POLL_INTERVAL)


def main():
    """Main entry point"""
    print("=" * 55)
    print("🏷️  SmartPneu Label Manager")
    print("=" * 55)
    print(f"Server:        {SERVER_URL}")
    print(f"Printer:       {PRINTER_NAME}")
    print(f"Labels folder: {LABELS_FOLDER}")
    print(f"Archive:       {ARCHIVE_FOLDER}")
    print(f"Web UI:        http://localhost:{LOCAL_PORT}")
    print("=" * 55)
    
    # Ensure folders exist
    ensure_folders()
    
    # Check printer
    if check_printer():
        print(f"✅ Printer ready")
    else:
        print(f"⚠️  Printer '{PRINTER_NAME}' not found")
    
    print("=" * 55)
    print("📌 Labels are saved locally and NOT auto-printed")
    print(f"📌 Open http://localhost:{LOCAL_PORT} to view & print")
    print("=" * 55)
    print()
    
    # Start polling in background thread
    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()
    
    # Run Flask web interface
    app.run(host='127.0.0.1', port=LOCAL_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
