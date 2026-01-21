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
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'completed_at': None,
        'printer': None,
        'error': None
    }
    
    print(f"📋 Created print job: {job_id} (SKU: {sku})")
    return job_id


def get_pending_jobs(include_pdf=True):
    """
    Get all pending print jobs
    
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


def complete_job(job_id, success=True, message="", printer=None):
    """
    Mark a job as complete and remove PDF data to free memory
    """
    if job_id not in print_jobs:
        return False
    
    print_jobs[job_id]['status'] = 'complete' if success else 'failed'
    print_jobs[job_id]['completed_at'] = datetime.now().isoformat()
    print_jobs[job_id]['printer'] = printer
    print_jobs[job_id]['pdf_data'] = None  # Free memory
    
    if not success:
        print_jobs[job_id]['error'] = message
    
    status = "✅ Complete" if success else "❌ Failed"
    print(f"{status}: Job {job_id}")
    
    return True


def get_all_jobs(limit=50):
    """Get all jobs (without PDF data), sorted by creation time"""
    jobs = []
    for job in print_jobs.values():
        job_copy = {k: v for k, v in job.items() if k != 'pdf_data'}
        jobs.append(job_copy)
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    return jobs[:limit]


def cleanup_old_jobs(max_age_hours=24):
    """Remove completed jobs older than max_age_hours"""
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    
    to_remove = []
    for job_id, job in print_jobs.items():
        if job['status'] in ['complete', 'failed']:
            created = datetime.fromisoformat(job['created_at'])
            if created < cutoff:
                to_remove.append(job_id)
    
    for job_id in to_remove:
        del print_jobs[job_id]
    
    if to_remove:
        print(f"🧹 Cleaned up {len(to_remove)} old jobs")


def get_pending_count():
    """Get count of pending jobs"""
    return sum(1 for job in print_jobs.values() if job['status'] == 'pending')
