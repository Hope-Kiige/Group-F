from rest_framework import serializers
from .model import Customer, BuildingProject, DashboardMetrics, Estimate, Invoice, JobSchedule, Payment, Material, Supplier, Task, MaterialOrder, Equipment, Subcontractor, Employee, ProgressReport

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer 
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only

class BuildingProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuildingProject
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class EstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estimate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class SubcontractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcontractor
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class JobScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSchedule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class ProgressReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressReport
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class JobScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSchedule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class MaterialOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialOrder
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
class DashboardMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardMetrics
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']  # Make 'id' read-only
    
