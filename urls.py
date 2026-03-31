"""
URL patterns for core app
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/charts/', views.dashboard_charts, name='dashboard_charts'),
    
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    
    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/report/', views.project_report, name='project_report'),
    
    # Estimates
    path('estimates/', views.EstimateListView.as_view(), name='estimate_list'),
    path('estimates/<int:pk>/', views.EstimateDetailView.as_view(), name='estimate_detail'),
    path('estimates/create/<int:project_id>/', views.EstimateCreateView.as_view(), name='estimate_create'),
    path('estimates/<int:pk>/send/', views.send_estimate, name='send_estimate'),
    path('estimates/<int:pk>/accept/', views.accept_estimate, name='accept_estimate'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/create/<int:project_id>/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/send/', views.send_invoice, name='send_invoice'),
    
    # Payments
    path('payments/create/<int:invoice_id>/', views.PaymentCreateView.as_view(), name='payment_create'),
    
    # Schedules
    path('schedules/', views.ScheduleListView.as_view(), name='schedule_list'),
    path('schedules/<int:pk>/', views.ScheduleDetailView.as_view(), name='schedule_detail'),
    path('schedules/<int:pk>/confirm/', views.confirm_schedule, name='confirm_schedule'),
    
    # Material Orders
    path('materials/orders/', views.MaterialOrderListView.as_view(), name='material_order_list'),
    path('materials/orders/create/<int:project_id>/', views.MaterialOrderCreateView.as_view(), name='material_order_create'),
    path('materials/orders/<int:pk>/deliver/', views.mark_order_delivered, name='mark_order_delivered'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]