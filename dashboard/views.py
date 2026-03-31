from django.shortcuts import render

# Create your views here.
def dashboard(request):
    """Main dashboard view"""
    return render(request, 'dashboard/index.html')

def customer_list(request):
    """Customer listing page"""
    return render(request, 'dashboard/customers/list.html')

def project_list(request):
    """Project listing page"""
    return render(request, 'dashboard/projects/list.html')

def job_schedule(request):
    """Job schedule calendar view"""
    return render(request, 'dashboard/schedule.html')

def estimate_list(request):
    """Estimate listing page"""
    return render(request, 'dashboard/estimates/list.html')

def invoice_list(request):
    """Invoice listing page"""
    return render(request, 'dashboard/invoices/list.html')

def green_tech_report(request):
    """Green technology report page"""
    return render(request, 'dashboard/reports/green_tech.html')

def materials_list(request):
    """Materials listing page"""
    return render(request, 'dashboard/materials/list.html')

def reports_index(request):
    """Report index page"""
    return render(request, 'dashboard/reports/index.html')