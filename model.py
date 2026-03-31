"""
Complete models for Bidii Builders Management System
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class Customer(models.Model):
    """Customer who requests building services"""
    name = models.CharField(max_length=200, db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(max_length=100, blank=True)
    address = models.TextField()
    contact_notes = models.TextField(blank=True, help_text="Additional notes about customer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Customers"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_active_projects(self):
        """Get all active building projects for this customer"""
        return self.building_projects.filter(
            status__in=['enquiry', 'estimated', 'scheduled', 'in_progress']
        )
    
    def get_total_spent(self):
        """Calculate total amount spent by customer"""
        total = 0
        for project in self.building_projects.filter(status='paid'):
            if hasattr(project, 'invoice'):
                total += project.invoice.actual_cost
        return total


class BuildingProject(models.Model):
    """Main project entity representing a building or improvement job"""
    STATUS_CHOICES = [
        ('enquiry', 'Enquiry'),
        ('estimated', 'Estimate Sent'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='building_projects'
    )
    description = models.TextField(help_text="Outline of proposed work")
    detailed_work = models.TextField(blank=True, help_text="Detailed work description after property visit")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enquiry', db_index=True)
    start_date = models.DateField(null=True, blank=True)
    scheduled_start_date = models.DateField(null=True, blank=True)
    confirmed_start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    green_tech_used = models.BooleanField(default=False, help_text="Whether green technology is incorporated")
    green_tech_details = models.TextField(blank=True, help_text="Details of green technology used")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['customer', 'status']),
        ]
    
    def __str__(self):
        return f"Project {self.id}: {self.customer.name} - {self.description[:50]}"
    
    def get_total_estimated_cost(self):
        """Calculate total estimated cost including materials"""
        materials_total = sum(item.total_cost() for item in self.material_orders.all())
        return (self.estimated_cost or 0) + materials_total
    
    def get_total_actual_cost(self):
        """Calculate total actual cost including materials"""
        materials_total = sum(item.total_cost() for item in self.material_orders.all())
        return (self.actual_cost or 0) + materials_total
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        if hasattr(self, 'invoice'):
            return self.invoice.is_overdue()
        return False
    
    def days_since_completion(self):
        """Calculate days since project completion"""
        if self.end_date:
            return (timezone.now().date() - self.end_date).days
        return None
    
    def get_progress_percentage(self):
        """Calculate project progress percentage"""
        if self.status == 'completed':
            return 100
        elif self.status == 'paid':
            return 100
        elif self.status == 'invoiced':
            return 90
        elif self.status == 'in_progress':
            return 50
        elif self.status == 'scheduled':
            return 25
        elif self.status == 'estimated':
            return 10
        else:
            return 0
    
    def clean(self):
        """Validate model data"""
        if self.estimated_cost and self.estimated_cost < 0:
            raise ValidationError({'estimated_cost': 'Estimated cost cannot be negative'})
        if self.actual_cost and self.actual_cost < 0:
            raise ValidationError({'actual_cost': 'Actual cost cannot be negative'})
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date cannot be after end date')


class Estimate(models.Model):
    """Detailed estimate sent to customer"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    project = models.OneToOneField(
        BuildingProject, 
        on_delete=models.CASCADE, 
        related_name='estimate'
    )
    outline_work = models.TextField(help_text="Initial outline of work")
    detailed_work = models.TextField(help_text="Detailed work after property visit")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    visit_date = models.DateField(help_text="Date of property visit")
    estimate_date = models.DateField(auto_now_add=True)
    sent_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-estimate_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['visit_date']),
        ]
    
    def __str__(self):
        return f"Estimate for Project {self.project.id} - {self.estimated_cost}"
    
    def send_estimate(self):
        """Mark estimate as sent"""
        self.status = 'sent'
        self.sent_date = timezone.now().date()
        self.save()
        self.project.status = 'estimated'
        self.project.save()
        logger.info(f"Estimate sent for project {self.project.id}")
    
    def accept_estimate(self):
        """Mark estimate as accepted"""
        self.status = 'accepted'
        self.save()
        self.project.status = 'estimated'
        self.project.estimated_cost = self.estimated_cost
        self.project.save()
        logger.info(f"Estimate accepted for project {self.project.id}")
    
    def days_since_visit(self):
        """Check if estimate is within 3-day requirement"""
        if self.visit_date:
            return (self.estimate_date - self.visit_date).days
        return None
    
    def is_within_deadline(self):
        """Check if estimate was sent within 3 days of visit"""
        days = self.days_since_visit()
        return days is not None and days <= 3
    
    def days_until_deadline(self):
        """Calculate days remaining to send estimate"""
        if self.status == 'draft' and self.visit_date:
            days_elapsed = (timezone.now().date() - self.visit_date).days
            return max(0, 3 - days_elapsed)
        return None
    
    def clean(self):
        """Validate estimate data"""
        if self.estimated_cost and self.estimated_cost <= 0:
            raise ValidationError({'estimated_cost': 'Estimated cost must be greater than zero'})
        if self.visit_date and self.visit_date > timezone.now().date():
            raise ValidationError({'visit_date': 'Visit date cannot be in the future'})


class Supplier(models.Model):
    """Material supplier"""
    name = models.CharField(max_length=200, db_index=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=100, blank=True)
    address = models.TextField()
    is_preferred = models.BooleanField(default=False, help_text="Preferred supplier")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_preferred']),
        ]
    
    def __str__(self):
        return self.name


class Material(models.Model):
    """Building materials available from suppliers"""
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('bag', 'Bag'),
        ('meter', 'Meter'),
        ('kg', 'Kilogram'),
        ('litre', 'Litre'),
        ('box', 'Box'),
        ('roll', 'Roll'),
        ('sheet', 'Sheet'),
    ]
    
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='materials'
    )
    is_green = models.BooleanField(default=False, help_text="Is this a green/eco-friendly material?")
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Current stock quantity")
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Quantity that triggers reorder")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_green']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.unit_price} per {self.unit}"
    
    def needs_reorder(self):
        """Check if material needs to be reordered"""
        return self.stock_quantity <= self.reorder_level


class MaterialOrder(models.Model):
    """Materials ordered for a specific project"""
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    project = models.ForeignKey(
        BuildingProject, 
        on_delete=models.CASCADE, 
        related_name='material_orders'
    )
    material = models.ForeignKey(
        Material, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='orders'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    supplier_name = models.CharField(max_length=200, blank=True, help_text="Supplier name at time of order")
    materials_list = models.TextField(help_text="Comma-separated list of materials ordered")
    order_date = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending', db_index=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['project', 'status']),
        ]
    
    def __str__(self):
        return f"Order for Project {self.project.id} - {self.material.name if self.material else 'Materials'}"
    
    def total_cost(self):
        """Calculate total cost for this order"""
        return self.quantity * self.unit_price_at_order
    
    def mark_delivered(self):
        """Mark order as delivered"""
        self.status = 'delivered'
        self.delivery_date = timezone.now().date()
        self.save()
        
        # Update stock if material exists
        if self.material:
            self.material.stock_quantity += self.quantity
            self.material.save()
        
        logger.info(f"Materials delivered for project {self.project.id}")
    
    def mark_ordered(self):
        """Mark order as ordered"""
        self.status = 'ordered'
        self.save()
        logger.info(f"Materials ordered for project {self.project.id}")


class Invoice(models.Model):
    """Final invoice sent to customer"""
    project = models.OneToOneField(
        BuildingProject, 
        on_delete=models.CASCADE, 
        related_name='invoice'
    )
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2)
    sent_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    paid = models.BooleanField(default=False, db_index=True)
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    
    class Meta:
        ordering = ['-sent_date']
        indexes = [
            models.Index(fields=['paid']),
            models.Index(fields=['due_date']),
            models.Index(fields=['invoice_number']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} - {self.actual_cost}"
    
    def save(self, *args, **kwargs):
        """Auto-set due date to 30 days after sending and generate invoice number"""
        if not self.due_date and self.sent_date:
            self.due_date = self.sent_date + timedelta(days=30)
        
        if not self.invoice_number:
            year = timezone.now().year
            count = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{year}'
            ).count() + 1
            self.invoice_number = f'INV-{year}-{count:04d}'
        
        super().save(*args, **kwargs)
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        if not self.paid and self.due_date:
            return timezone.now().date() > self.due_date
        return False
    
    def get_outstanding_balance(self):
        """Calculate outstanding balance"""
        paid_amount = sum(payment.amount_paid for payment in self.payments.all())
        return self.actual_cost - paid_amount
    
    def mark_as_paid(self, payment_date=None):
        """Mark invoice as fully paid"""
        self.paid = True
        self.payment_date = payment_date or timezone.now().date()
        self.save()
        self.project.status = 'paid'
        self.project.save()
        logger.info(f"Invoice {self.invoice_number} marked as paid")


class Payment(models.Model):
    """Payment received for invoice"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('mobile_money', 'Mobile Money'),
        ('credit_card', 'Credit Card'),
    ]
    
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    reference_number = models.CharField(max_length=100, blank=True, help_text="Transaction reference")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_method']),
        ]
    
    def __str__(self):
        return f"Payment of {self.amount_paid} for Invoice {self.invoice.invoice_number}"
    
    def save(self, *args, **kwargs):
        """Update invoice paid status when full payment is received"""
        super().save(*args, **kwargs)
        
        # Check if invoice is now fully paid
        total_paid = sum(p.amount_paid for p in self.invoice.payments.all())
        if total_paid >= self.invoice.actual_cost and not self.invoice.paid:
            self.invoice.mark_as_paid(self.payment_date)
    
    def clean(self):
        """Validate payment amount"""
        if self.amount_paid <= 0:
            raise ValidationError({'amount_paid': 'Payment amount must be greater than zero'})
        
        outstanding = self.invoice.get_outstanding_balance()
        if self.amount_paid > outstanding:
            raise ValidationError(
                {'amount_paid': f'Payment amount cannot exceed outstanding balance of {outstanding}'}
            )


class JobSchedule(models.Model):
    """Job scheduling and timeline tracking"""
    project = models.OneToOneField(
        BuildingProject, 
        on_delete=models.CASCADE, 
        related_name='schedule'
    )
    scheduled_date = models.DateField()
    confirmed_date = models.DateField(null=True, blank=True)
    start_confirmed = models.BooleanField(default=False)
    confirmation_sent_date = models.DateField(null=True, blank=True)
    estimated_duration_days = models.IntegerField(default=30)
    actual_duration_days = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_date']
        indexes = [
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['start_confirmed']),
        ]
    
    def __str__(self):
        return f"Schedule for Project {self.project.id}"
    
    def confirm_start(self):
        """Confirm start date and send confirmation"""
        self.confirmed_date = timezone.now().date()
        self.start_confirmed = True
        self.confirmation_sent_date = timezone.now().date()
        self.save()
        self.project.confirmed_start_date = self.confirmed_date
        self.project.status = 'scheduled'
        self.project.save()
        logger.info(f"Start date confirmed for project {self.project.id}")
    
    def get_days_until_start(self):
        """Calculate days until scheduled start"""
        if self.scheduled_date:
            days = (self.scheduled_date - timezone.now().date()).days
            return max(0, days)
        return None
    
    def get_status(self):
        """Get schedule status"""
        if self.start_confirmed:
            return "Confirmed"
        elif self.get_days_until_start() == 0:
            return "Today"
        elif self.get_days_until_start() < 0:
            return "Overdue"
        else:
            return "Pending"


class Equipment(models.Model):
    """Equipment used in projects"""
    EQUIPMENT_STATUS = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    rental_cost_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_rented = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=EQUIPMENT_STATUS, default='available')
    purchase_date = models.DateField(null=True, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Equipment"
    
    def __str__(self):
        return self.name


class Subcontractor(models.Model):
    """Subcontractors hired for specific tasks"""
    name = models.CharField(max_length=200)
    trade = models.CharField(max_length=100, help_text="Trade or specialization")
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=100, blank=True)
    address = models.TextField()
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.trade}"


class Employee(models.Model):
    """Employees working on projects"""
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=100, help_text="Role or position")
    phone = models.CharField(max_length=20)
    email = models.EmailField(max_length=100, blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.role}"


class Task(models.Model):
    """Tasks assigned to employees or subcontractors"""
    TASK_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    project = models.ForeignKey(
        BuildingProject, 
        on_delete=models.CASCADE, 
        related_name='tasks'
    )
    description = models.TextField()
    assigned_to_employee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tasks'
    )
    assigned_to_subcontractor = models.ForeignKey(
        Subcontractor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tasks'
    )
    scheduled_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending')
    estimated_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"Task for Project {self.project.id} - {self.description[:50]}"
    
    def mark_complete(self):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_date = timezone.now().date()
        self.save()


class ProgressReport(models.Model):
    """Progress reports for ongoing projects"""
    project = models.ForeignKey(
        BuildingProject, 
        on_delete=models.CASCADE, 
        related_name='progress_reports'
    )
    report_date = models.DateField(auto_now_add=True)
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Overall progress percentage")
    work_completed = models.TextField(help_text="Description of work completed since last report")
    issues_faced = models.TextField(blank=True, help_text="Any issues or delays faced")
    next_steps = models.TextField(blank=True, help_text="Planned work for next period")
    reported_by = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-report_date']
        get_latest_by = 'report_date'
    
    def __str__(self):
        return f"Progress Report for Project {self.project.id} - {self.progress_percentage}%"
    
    def clean(self):
        """Validate progress percentage"""
        if self.progress_percentage < 0 or self.progress_percentage > 100:
            raise ValidationError({'progress_percentage': 'Progress must be between 0 and 100'})


class DashboardMetrics(models.Model):
    """For caching dashboard metrics (improves performance)"""
    metric_name = models.CharField(max_length=100, unique=True, db_index=True)
    metric_value = models.JSONField()
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Dashboard Metrics"
    
    def __str__(self):
        return self.metric_name
    
    @classmethod
    def get_or_calculate(cls, metric_name, calculator_func):
        """Get cached metric or calculate if expired"""
        try:
            metric = cls.objects.get(metric_name=metric_name)
            # Refresh if older than 5 minutes
            if (timezone.now() - metric.calculated_at).seconds > 300:
                metric.metric_value = calculator_func()
                metric.save()
            return metric.metric_value
        except cls.DoesNotExist:
            value = calculator_func()
            cls.objects.create(metric_name=metric_name, metric_value=value)
            return value