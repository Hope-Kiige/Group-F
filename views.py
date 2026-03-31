"""
Views for Bidii Builders Management System
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncDate
from django.http import JsonResponse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from datetime import datetime, timedelta

from .models import (
    Customer, BuildingProject, Estimate, Supplier, Material, 
    MaterialOrder, Invoice, Payment, JobSchedule, Equipment,
    Subcontractor, Employee, Task, ProgressReport, DashboardMetrics
)
from .forms import (
    CustomerForm, BuildingProjectForm, EstimateForm, MaterialOrderForm,
    InvoiceForm, PaymentForm, JobScheduleForm, ProgressReportForm
)
from .utils import (
    generate_invoice_pdf, send_estimate_email, send_invoice_email,
    get_dashboard_metrics, generate_project_report
)


@login_required
def dashboard(request):
    """Main dashboard view with charts and metrics"""
    today = timezone.now().date()
    
    # Get metrics
    metrics = get_dashboard_metrics()
    
    # Active projects
    active_projects = BuildingProject.objects.filter(
        status__in=['estimated', 'scheduled', 'in_progress']
    ).select_related('customer')
    
    # Overdue invoices
    overdue_invoices = Invoice.objects.filter(
        paid=False,
        due_date__lt=today
    ).select_related('project__customer')
    
    # Upcoming schedules
    upcoming_schedules = JobSchedule.objects.filter(
        scheduled_date__gte=today,
        start_confirmed=False
    ).select_related('project')[:10]
    
    # Recent payments
    recent_payments = Payment.objects.select_related(
        'invoice__project__customer'
    ).order_by('-payment_date')[:10]
    
    # Projects that need estimates within 3 days
    pending_estimates = Estimate.objects.filter(
        status='draft',
        visit_date__gte=today - timedelta(days=3)
    ).select_related('project__customer')
    
    context = {
        'metrics': metrics,
        'active_projects': active_projects,
        'overdue_invoices': overdue_invoices,
        'upcoming_schedules': upcoming_schedules,
        'recent_payments': recent_payments,
        'pending_estimates': pending_estimates,
        'today': today,
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def dashboard_charts(request):
    """API endpoint for dashboard charts"""
    # Project status distribution
    status_data = BuildingProject.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Monthly revenue
    monthly_revenue = Payment.objects.filter(
        payment_date__year=timezone.now().year
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total=Sum('amount_paid')
    ).order_by('month')
    
    # Material usage
    material_usage = MaterialOrder.objects.filter(
        order_date__month=timezone.now().month
    ).values('material__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:10]
    
    return JsonResponse({
        'status_distribution': list(status_data),
        'monthly_revenue': list(monthly_revenue),
        'material_usage': list(material_usage),
    })


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'core/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'core/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.building_projects.all()
        context['total_spent'] = self.object.get_total_spent()
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    success_url = reverse_lazy('customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer created successfully.')
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'core/customer_form.html'
    success_url = reverse_lazy('customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully.')
        return super().form_valid(form)


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'core/customer_confirm_delete.html'
    success_url = reverse_lazy('customer_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Customer deleted successfully.')
        return super().delete(request, *args, **kwargs)


class ProjectListView(LoginRequiredMixin, ListView):
    model = BuildingProject
    template_name = 'core/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by customer
        customer = self.request.GET.get('customer')
        if customer:
            queryset = queryset.filter(customer_id=customer)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(customer__name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = BuildingProject.STATUS_CHOICES
        context['customers'] = Customer.objects.all()
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = BuildingProject
    template_name = 'core/project_detail.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['material_orders'] = self.object.material_orders.all()
        context['tasks'] = self.object.tasks.all()
        context['progress_reports'] = self.object.progress_reports.all()[:5]
        
        if hasattr(self.object, 'estimate'):
            context['estimate'] = self.object.estimate
        
        if hasattr(self.object, 'schedule'):
            context['schedule'] = self.object.schedule
        
        if hasattr(self.object, 'invoice'):
            context['invoice'] = self.object.invoice
        
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = BuildingProject
    form_class = BuildingProjectForm
    template_name = 'core/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Project created successfully.')
        
        # Create associated schedule
        JobSchedule.objects.create(
            project=self.object,
            scheduled_date=self.object.start_date or timezone.now().date()
        )
        
        return response


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = BuildingProject
    form_class = BuildingProjectForm
    template_name = 'core/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Project updated successfully.')
        return super().form_valid(form)


@login_required
def project_report(request, pk):
    """Generate and download project report as PDF"""
    project = get_object_or_404(BuildingProject, pk=pk)
    pdf = generate_project_report(project)
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="project_{pk}_report.pdf"'
    return response


class EstimateListView(LoginRequiredMixin, ListView):
    model = Estimate
    template_name = 'core/estimate_list.html'
    context_object_name = 'estimates'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('project__customer')
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Estimate.STATUS_CHOICES
        return context


class EstimateDetailView(LoginRequiredMixin, DetailView):
    model = Estimate
    template_name = 'core/estimate_detail.html'
    context_object_name = 'estimate'


class EstimateCreateView(LoginRequiredMixin, CreateView):
    model = Estimate
    form_class = EstimateForm
    template_name = 'core/estimate_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        project_id = self.kwargs.get('project_id')
        if project_id:
            project = get_object_or_404(BuildingProject, pk=project_id)
            initial['project'] = project
            initial['outline_work'] = project.description
            initial['detailed_work'] = project.detailed_work
            initial['estimated_cost'] = project.estimated_cost
        return initial
    
    def get_success_url(self):
        return reverse_lazy('estimate_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Estimate created successfully.')
        return response


@login_required
def send_estimate(request, pk):
    """Send estimate to customer"""
    estimate = get_object_or_404(Estimate, pk=pk)
    
    if estimate.status == 'draft':
        if not estimate.is_within_deadline():
            messages.warning(
                request, 
                f'Warning: Estimate is being sent {estimate.days_since_visit()} days after visit '
                f'(should be within 3 days)'
            )
        
        estimate.send_estimate()
        send_estimate_email(estimate)
        messages.success(request, 'Estimate sent successfully.')
    else:
        messages.error(request, 'Estimate has already been sent.')
    
    return redirect('estimate_detail', pk=pk)


@login_required
def accept_estimate(request, pk):
    """Accept estimate and move to scheduling"""
    estimate = get_object_or_404(Estimate, pk=pk)
    
    if estimate.status == 'sent':
        estimate.accept_estimate()
        messages.success(request, 'Estimate accepted. You can now schedule the job.')
    else:
        messages.error(request, 'Cannot accept estimate in its current status.')
    
    return redirect('estimate_detail', pk=pk)


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'core/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('project__customer')
        
        # Filter by paid status
        paid = self.request.GET.get('paid')
        if paid is not None:
            queryset = queryset.filter(paid=paid == 'true')
        
        # Filter overdue
        overdue = self.request.GET.get('overdue')
        if overdue == 'true':
            queryset = queryset.filter(paid=False, due_date__lt=timezone.now().date())
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_outstanding'] = sum(
            inv.get_outstanding_balance() for inv in context['invoices'] if not inv.paid
        )
        return context


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'core/invoice_detail.html'
    context_object_name = 'invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all()
        context['outstanding'] = self.object.get_outstanding_balance()
        return context


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'core/invoice_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        project_id = self.kwargs.get('project_id')
        if project_id:
            project = get_object_or_404(BuildingProject, pk=project_id)
            initial['project'] = project
            initial['actual_cost'] = project.get_total_actual_cost()
        return initial
    
    def get_success_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update project status
        self.object.project.status = 'invoiced'
        self.object.project.save()
        
        messages.success(self.request, 'Invoice created successfully.')
        return response


@login_required
def send_invoice(request, pk):
    """Send invoice to customer"""
    invoice = get_object_or_404(Invoice, pk=pk)
    send_invoice_email(invoice)
    messages.success(request, f'Invoice {invoice.invoice_number} sent successfully.')
    return redirect('invoice_detail', pk=pk)


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'core/payment_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        invoice_id = self.kwargs.get('invoice_id')
        if invoice_id:
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            initial['invoice'] = invoice
        return initial
    
    def get_success_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.object.invoice.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Payment recorded successfully.')
        return response


class ScheduleListView(LoginRequiredMixin, ListView):
    model = JobSchedule
    template_name = 'core/schedule_list.html'
    context_object_name = 'schedules'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('project__customer')
        
        # Filter by confirmed status
        confirmed = self.request.GET.get('confirmed')
        if confirmed is not None:
            queryset = queryset.filter(start_confirmed=confirmed == 'true')
        
        return queryset


class ScheduleDetailView(LoginRequiredMixin, DetailView):
    model = JobSchedule
    template_name = 'core/schedule_detail.html'
    context_object_name = 'schedule'


@login_required
def confirm_schedule(request, pk):
    """Confirm job start date"""
    schedule = get_object_or_404(JobSchedule, pk=pk)
    
    if not schedule.start_confirmed:
        schedule.confirm_start()
        messages.success(request, 'Start date confirmed. Materials can now be ordered.')
    else:
        messages.warning(request, 'Start date has already been confirmed.')
    
    return redirect('schedule_detail', pk=pk)


class MaterialOrderListView(LoginRequiredMixin, ListView):
    model = MaterialOrder
    template_name = 'core/material_order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('project', 'material')
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = MaterialOrder.ORDER_STATUS
        return context


class MaterialOrderCreateView(LoginRequiredMixin, CreateView):
    model = MaterialOrder
    form_class = MaterialOrderForm
    template_name = 'core/material_order_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        project_id = self.kwargs.get('project_id')
        if project_id:
            initial['project'] = get_object_or_404(BuildingProject, pk=project_id)
        return initial
    
    def get_success_url(self):
        return reverse_lazy('material_order_list')
    
    def form_valid(self, form):
        # Check if project schedule is confirmed
        project = form.cleaned_data['project']
        if hasattr(project, 'schedule') and not project.schedule.start_confirmed:
            messages.warning(
                self.request, 
                'Warning: Project start date not confirmed. Materials ordered may need to be rescheduled.'
            )
        
        response = super().form_valid(form)
        messages.success(self.request, 'Material order created successfully.')
        return response


@login_required
def mark_order_delivered(request, pk):
    """Mark material order as delivered"""
    order = get_object_or_404(MaterialOrder, pk=pk)
    
    if order.status == 'ordered':
        order.mark_delivered()
        messages.success(request, 'Order marked as delivered.')
    else:
        messages.error(request, f'Cannot mark order with status "{order.status}" as delivered.')
    
    return redirect('material_order_list')


@login_required
def analytics(request):
    """Advanced analytics and reporting view"""
    today = timezone.now().date()
    
    # Revenue analytics
    revenue_data = Payment.objects.filter(
        payment_date__year=today.year
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(
        total=Sum('amount_paid')
    ).order_by('month')
    
    # Project completion rate
    total_projects = BuildingProject.objects.count()
    completed_projects = BuildingProject.objects.filter(
        status__in=['completed', 'paid']
    ).count()
    completion_rate = (completed_projects / total_projects * 100) if total_projects > 0 else 0
    
    # Average estimate turnaround time
    estimates_sent = Estimate.objects.filter(status='sent')
    avg_turnaround = estimates_sent.aggregate(
        avg_days=Avg('sent_date', field='sent_date - visit_date')
    )['avg_days']
    
    # Green tech usage
    green_projects = BuildingProject.objects.filter(green_tech_used=True).count()
    green_percentage = (green_projects / total_projects * 100) if total_projects > 0 else 0
    
    # Material cost breakdown
    material_costs = MaterialOrder.objects.filter(
        order_date__year=today.year
    ).values('material__name').annotate(
        total_cost=Sum('quantity') * Sum('unit_price_at_order')
    ).order_by('-total_cost')[:10]
    
    context = {
        'revenue_data': list(revenue_data),
        'completion_rate': round(completion_rate, 2),
        'avg_turnaround': round(avg_turnaround or 0, 2),
        'green_percentage': round(green_percentage, 2),
        'material_costs': list(material_costs),
        'total_projects': total_projects,
        'completed_projects': completed_projects,
    }
    
    return render(request, 'core/analytics.html', context)