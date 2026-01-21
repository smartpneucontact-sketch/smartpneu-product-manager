"""
Storage module for print job management

Simple in-memory storage that embeds PDF data directly in jobs.
No external cloud storage required.
"""

import os
import base64
from datetime import datetime, timedelta

# In-memory print job queue
print_jobs = {}


def create_print_job_with_pdf(pdf_path, sku, product_data=None):
    """
    Create a print job with embedded PDF data
    
    Args:
        pdf_path: Path to local PDF file
        sku: Product SKU for reference
        product_data: Optional additional product info
        
    Returns:
        Job ID
    """
    job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}_{sku}"
    
    # Read and encode PDF as base64
    with open(pdf_path, 'rb') as f:
        pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    print_jobs[job_id] = {
        'id': job_id,
        'pdf_data': pdf_base64,  # Embedded PDF
        'pdf_filename': os.path.basename(pdf_path),
        'sku': sku,
        'product_data': product_data or {},
        'status': 'pending',  # pending -> downloaded -> cleared
        'created_at': datetime.now().isoformat(),
        'downloaded_at': None,
        'printer': None,
        'error': None
    }
    
    print(f"📋 Created print job: {job_id} (SKU: {sku})")
    return job_id


def get_pending_jobs(include_pdf=True):
    """
    Get all pending print jobs (not yet downloaded by agent)
    
    Args:
        include_pdf: If True, include PDF data in response
    """
    jobs = []
    for job in print_jobs.values():
        if job['status'] == 'pending':
            if include_pdf:
                jobs.append(job)
            else:
                # Return job without PDF data (for listing)
                job_copy = {k: v for k, v in job.items() if k != 'pdf_data'}
                jobs.append(job_copy)
    return jobs


def get_job(job_id, include_pdf=True):
    """Get a specific job by ID"""
    job = print_jobs.get(job_id)
    if job and not include_pdf:
        return {k: v for k, v in job.items() if k != 'pdf_data'}
    return job


def mark_job_downloaded(job_id):
    """
    Mark a job as downloaded (saved locally by agent)
    Job stays in list but PDF data is cleared to save memory
    """
    if job_id not in print_jobs:
        return False
    
    print_jobs[job_id]['status'] = 'downloaded'
    print_jobs[job_id]['downloaded_at'] = datetime.now().isoformat()
    print_jobs[job_id]['pdf_data'] = None  # Free memory
    
    print(f"✅ Downloaded: Job {job_id}")
    return True


def complete_job(job_id, success=True, message="", printer=None):
    """
    Mark a job as downloaded (keeping backward compatibility)
    """
    return mark_job_downloaded(job_id)


def get_all_jobs(limit=50):
    """Get all jobs (without PDF data), sorted by creation time"""
    jobs = []
    for job in print_jobs.values():
        job_copy = {k: v for k, v in job.items() if k != 'pdf_data'}
        jobs.append(job_copy)
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    return jobs[:limit]


def clear_downloaded_jobs():
    """Remove all downloaded jobs to free memory"""
    to_remove = [
        job_id for job_id, job in print_jobs.items()
        if job['status'] == 'downloaded'
    ]
    
    for job_id in to_remove:
        del print_jobs[job_id]
    
    if to_remove:
        print(f"🧹 Cleared {len(to_remove)} downloaded jobs")
    
    return len(to_remove)


def get_pending_count():
    """Get count of pending jobs (not yet downloaded)"""
    return sum(1 for job in print_jobs.values() if job['status'] == 'pending')


def get_downloaded_count():
    """Get count of downloaded jobs"""
    return sum(1 for job in print_jobs.values() if job['status'] == 'downloaded')
