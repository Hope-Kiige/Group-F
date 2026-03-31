from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('customers/', views.customer_list, name='customer_list'),
    path('projects/', views.project_list, name='project_list'),
    path('schedule/', views.job_schedule, name='job_schedule'),
    path('estimates/', views.estimate_list, name='estimate_list'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('green_tech/', views.green_tech_report, name='green_tech_report'),
    path('materials/', views.materials_list, name='materials_list'),
    path('reports/', views.reports_index, name='reports_index'),
]