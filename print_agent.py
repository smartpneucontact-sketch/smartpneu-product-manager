#!/usr/bin/env python3
"""
SmartPneu Local Print Agent

This script runs on your local Mac to poll the Railway server for pending
print jobs and send them to your Brother printer.

Usage:
    python print_agent.py

Configuration via environment variables or .env file:
    SERVER_URL - Railway app URL (e.g., https://your-app.railway.app)
    PRINTER_NAME - Local printer name (default: Brother_DCP_L2530DW_series)
    POLL_INTERVAL - Seconds between polls (default: 5)
    PRINT_AGENT_API_KEY - API key for authentication (optional)
"""

import os
import time
import base64
import requests
import subprocess
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:5000')
PRINTER_NAME = os.getenv('PRINTER_NAME', 'Brother_DCP_L2530DW_series')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 5))
API_KEY = os.getenv('PRINT_AGENT_API_KEY', '')


def get_pending_jobs():
    """Fetch pending print jobs from server"""
    try:
        headers = {}
        if API_KEY:
            headers['X-API-Key'] = API_KEY
        
        response = requests.get(
            f"{SERVER_URL}/api/print-jobs",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('jobs', [])
        elif response.status_code == 401:
            print("❌ Unauthorized - check your API key")
            return []
        else:
            print(f"⚠️  Error fetching jobs: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Connection error: {e}")
        return []


def save_pdf_from_base64(pdf_base64, filename):
    """Decode base64 PDF and save to temp file"""
    try:
        pdf_data = base64.b64decode(pdf_base64)
        
        # Create temp file with original filename
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)
        
        return pdf_path
    except Exception as e:
        print(f"⚠️  Error saving PDF: {e}")
        return None


def print_pdf(pdf_path):
    """Send PDF to Brother printer"""
    cmd = [
        'lp',
        '-d', PRINTER_NAME,
        '-o', 'media=Custom.120x220mm,labels',
        '-o', 'InputSlot=manual',
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


def mark_job_complete(job_id, success, message=""):
    """Notify server that job is complete"""
    try:
        headers = {}
        if API_KEY:
            headers['X-API-Key'] = API_KEY
        
        response = requests.post(
            f"{SERVER_URL}/api/print-jobs/{job_id}/complete",
            headers=headers,
            json={
                'success': success,
                'message': message,
                'printer': PRINTER_NAME
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️  Failed to mark job complete: {e}")
        return False


def process_job(job):
    """Process a single print job"""
    job_id = job['id']
    pdf_base64 = job.get('pdf_data')
    filename = job.get('pdf_filename', f'{job_id}.pdf')
    sku = job.get('sku', 'unknown')
    
    print(f"📥 Processing job {job_id} (SKU: {sku})")
    
    if not pdf_base64:
        print(f"❌ No PDF data in job")
        mark_job_complete(job_id, False, "No PDF data")
        return False
    
    # Save PDF from base64
    pdf_path = save_pdf_from_base64(pdf_base64, filename)
    if not pdf_path:
        mark_job_complete(job_id, False, "Failed to decode PDF")
        return False
    
    try:
        # Print PDF
        success, message = print_pdf(pdf_path)
        
        if success:
            print(f"✅ Printed: {sku}")
            mark_job_complete(job_id, True, f"Printed on {PRINTER_NAME}")
        else:
            print(f"❌ Print failed: {message}")
            mark_job_complete(job_id, False, message)
        
        return success
    finally:
        # Clean up temp file
        try:
            os.unlink(pdf_path)
        except:
            pass


def check_printer():
    """Check if configured printer is available"""
    try:
        result = subprocess.run(['lpstat', '-p', PRINTER_NAME], capture_output=True, text=True)
        if result.returncode == 0 and 'enabled' in result.stdout.lower():
            return True
        return False
    except:
        return False


def main():
    """Main loop - poll for jobs and print them"""
    print("=" * 50)
    print("🖨️  SmartPneu Print Agent")
    print("=" * 50)
    print(f"Server: {SERVER_URL}")
    print(f"Printer: {PRINTER_NAME}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    print(f"API Key: {'configured' if API_KEY else 'not set'}")
    print("=" * 50)
    
    # Check printer
    if check_printer():
        print(f"✅ Printer '{PRINTER_NAME}' is available")
    else:
        print(f"⚠️  Printer '{PRINTER_NAME}' not found or disabled")
        print("   Available printers:")
        os.system("lpstat -p 2>/dev/null | head -5")
    
    print("=" * 50)
    print("Waiting for print jobs... (Ctrl+C to stop)")
    print()
    
    while True:
        try:
            jobs = get_pending_jobs()
            
            if jobs:
                print(f"📋 Found {len(jobs)} pending job(s)")
                for job in jobs:
                    process_job(job)
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n👋 Print agent stopped")
            break
        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
