from django.contrib import admin
from .models import Customer, Loan


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'first_name', 'last_name', 'phone_number', 'monthly_salary', 'approved_limit', 'current_debt']
    list_filter = ['created_at', 'approved_limit']
    search_fields = ['first_name', 'last_name', 'phone_number']
    readonly_fields = ['customer_id', 'created_at', 'updated_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['loan_id', 'customer', 'loan_amount', 'interest_rate', 'tenure', 'monthly_repayment', 'start_date', 'end_date']
    list_filter = ['start_date', 'end_date', 'interest_rate']
    search_fields = ['customer__first_name', 'customer__last_name', 'loan_id']
    readonly_fields = ['loan_id', 'created_at', 'updated_at']
