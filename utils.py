"""
Utility functions for Bidii Builders
"""
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.core.mail import EmailMessage
from django.conf import settings
from weasyprint import HTML
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import (
    BuildingProject, Invoice, Payment, MaterialOrder, 
    Customer, DashboardMetrics
)


def generate_invoice_pdf(invoice):
    """Generate PDF invoice for printing/emailing"""
    template = get_template('core/invoice_pdf.html')
    
    context = {
        'invoice': invoice,
        'project': invoice.project,
        'customer': invoice.project.customer,
        'payments': invoice.payments.all(),
        'outstanding': invoice.get_outstanding_balance(),
        'today': timezone.now().date(),
    }
    
    html = template.render(context)
    
    # Generate PDF
    pdf_file = BytesIO()
    HTML(string=html).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file


def send_estimate_email(estimate):
    """Send estimate to customer via email"""
    subject = f"Estimate for Building Project - {estimate.project.id}"
    
    # Generate PDF estimate
    template = get_template('core/estimate_pdf.html')
    context = {
        'estimate': estimate,
        'project': estimate.project,
        'customer': estimate.project.customer,
    }
    html = template.render(context)
    
    pdf_file = BytesIO()
    HTML(string=html).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    email = EmailMessage(
        subject=subject,
        body=f"Dear {estimate.project.customer.name},\n\nPlease find your estimate attached.\n\n"
             f"Estimated Cost: KES {estimate.estimated_cost:,.2f}\n"
             f"Visit Date: {estimate.visit_date}\n\n"
             f"Thank you for choosing Bidii Quality Builders.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[estimate.project.customer.email] if estimate.project.customer.email else [],
    )
    
    email.attach(f'estimate_{estimate.project.id}.pdf', pdf_file.getvalue(), 'application/pdf')
    email.send()


def send_invoice_email(invoice):
    """Send invoice to customer via email"""
    subject = f"Invoice {invoice.invoice_number} - Building Project"
    
    pdf_file = generate_invoice_pdf(invoice)
    
    email = EmailMessage(
        subject=subject,
        body=f"Dear {invoice.project.customer.name},\n\n"
             f"Please find your invoice attached.\n\n"
             f"Total Amount: KES {invoice.actual_cost:,.2f}\n"
             f"Due Date: {invoice.due_date}\n\n"
             f"Thank you for your business.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.project.customer.email] if invoice.project.customer.email else [],
    )
    
    email.attach(f'invoice_{invoice.invoice_number}.pdf', pdf_file.getvalue(), 'application/pdf')
    email.send()


def get_dashboard_metrics():
    """Calculate and cache dashboard metrics"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    def calculate_metrics():
        # Active projects
        active_projects = BuildingProject.objects.filter(
            status__in=['estimated', 'scheduled', 'in_progress']
        ).count()
        
        # Total revenue this month
        monthly_revenue = Payment.objects.filter(
            payment_date__gte=start_of_month
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        # Overdue invoices
        overdue_invoices = Invoice.objects.filter(
            paid=False,
            due_date__lt=today
        ).count()
        
        # Outstanding balance
        outstanding_invoices = Invoice.objects.filter(paid=False)
        outstanding_balance = sum(
            inv.get_outstanding_balance() for inv in outstanding_invoices
        )
        
        # Projects needing estimates within deadline
        urgent_estimates = Estimate.objects.filter(
            status='draft',
            visit_date__gte=today - timedelta(days=3)
        ).count()
        
        # Upcoming schedules this week
        week_end = today + timedelta(days=7)
        upcoming_schedules = JobSchedule.objects.filter(
            scheduled_date__range=[today, week_end],
            start_confirmed=False
        ).count()
        
        # Completed projects this month
        completed_projects = BuildingProject.objects.filter(
            end_date__gte=start_of_month,
            status__in=['completed', 'paid']
        ).count()
        
        # Green projects
        green_projects = BuildingProject.objects.filter(
            green_tech_used=True
        ).count()
        
        return {
            'active_projects': active_projects,
            'monthly_revenue': float(monthly_revenue),
            'overdue_invoices': overdue_invoices,
            'outstanding_balance': float(outstanding_balance),
            'urgent_estimates': urgent_estimates,
            'upcoming_schedules': upcoming_schedules,
            'completed_projects': completed_projects,
            'green_projects': green_projects,
        }
    
    return DashboardMetrics.get_or_calculate('dashboard_metrics', calculate_metrics)


def generate_project_report(project):
    """Generate detailed project report as PDF"""
    template = get_template('core/project_report_pdf.html')
    
    # Calculate material costs
    material_orders = project.material_orders.all()
    total_material_cost = sum(order.total_cost() for order in material_orders)
    
    # Calculate labor costs
    tasks = project.tasks.all()
    total_labor_cost = 0
    for task in tasks:
        if task.actual_hours and hasattr(task.assigned_to_employee, 'hourly_rate'):
            total_labor_cost += task.actual_hours * (task.assigned_to_employee.hourly_rate or 0)
    
    # Get payments
    payments = []
    if hasattr(project, 'invoice'):
        payments = project.invoice.payments.all()
    
    context = {
        'project': project,
        'customer': project.customer,
        'material_orders': material_orders,
        'total_material_cost': total_material_cost,
        'total_labor_cost': total_labor_cost,
        'payments': payments,
        'tasks': tasks,
        'progress_reports': project.progress_reports.all(),
        'today': timezone.now().date(),
    }
    
    html = template.render(context)
    
    pdf_file = BytesIO()
    HTML(string=html).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file


def create_dashboard_chart(chart_type, data):
    """Create matplotlib chart for dashboard"""
    plt.style.use('seaborn-v0_8-darkgrid')
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if chart_type == 'revenue':
        # Revenue over time
        months = [item['month'].strftime('%b') for item in data]
        revenues = [float(item['total']) for item in data]
        ax.plot(months, revenues, marker='o', linewidth=2, markersize=8)
        ax.set_title('Monthly Revenue', fontsize=14, fontweight='bold')
        ax.set_xlabel('Month')
        ax.set_ylabel('Revenue (KES)')
        ax.tick_params(axis='x', rotation=45)
        
    elif chart_type == 'status':
        # Project status distribution
        statuses = [item['status'] for item in data]
        counts = [item['count'] for item in data]
        colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']
        ax.pie(counts, labels=statuses, autopct='%1.1f%%', colors=colors)
        ax.set_title('Project Status Distribution', fontsize=14, fontweight='bold')
        
    elif chart_type == 'materials':
        # Material usage
        materials = [item['material__name'] for item in data]
        quantities = [float(item['total_quantity']) for item in data]
        ax.barh(materials, quantities, color='#27ae60')
        ax.set_title('Top Material Usage', fontsize=14, fontweight='bold')
        ax.set_xlabel('Quantity')
        
    # Save chart to base64 string
    buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64