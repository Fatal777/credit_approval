import pandas as pd
from celery import shared_task
from django.conf import settings
from datetime import datetime
from decimal import Decimal
import os

from .models import Customer, Loan


@shared_task
def ingest_customer_data():
    """
    Background task to ingest customer data from Excel file
    """
    try:
        # Path to the customer data file
        file_path = os.path.join(settings.BASE_DIR, 'customer_data.xlsx')
        
        if not os.path.exists(file_path):
            return f"Customer data file not found at {file_path}"
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Expected columns: customer_id, first_name, last_name, phone_number, monthly_salary, approved_limit, current_debt
        created_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            customer_id = row.get('Customer ID')
            
            # Check if customer already exists
            customer, created = Customer.objects.get_or_create(
                customer_id=customer_id,
                defaults={
                    'first_name': row.get('First Name', ''),
                    'last_name': row.get('Last Name', ''),
                    'phone_number': row.get('Phone Number', 0),
                    'monthly_salary': Decimal(str(row.get('Monthly Salary', 0))),
                    'approved_limit': Decimal(str(row.get('Approved Limit', 0))),
                    'current_debt': Decimal('0'),  # Default to 0 as not in Excel
                    'age': row.get('Age', 25)
                }
            )
            
            if created:
                created_count += 1
            else:
                # Update existing customer
                customer.first_name = row.get('First Name', customer.first_name)
                customer.last_name = row.get('Last Name', customer.last_name)
                customer.phone_number = row.get('Phone Number', customer.phone_number)
                customer.monthly_salary = Decimal(str(row.get('Monthly Salary', customer.monthly_salary)))
                customer.approved_limit = Decimal(str(row.get('Approved Limit', customer.approved_limit)))
                customer.current_debt = Decimal('0')
                customer.save()
                updated_count += 1
        
        return f"Customer data ingestion completed. Created: {created_count}, Updated: {updated_count}"
        
    except Exception as e:
        return f"Error ingesting customer data: {str(e)}"


@shared_task
def ingest_loan_data():
    """
    Background task to ingest loan data from Excel file
    """
    try:
        # Path to the loan data file
        file_path = os.path.join(settings.BASE_DIR, 'loan_data.xlsx')
        
        if not os.path.exists(file_path):
            return f"Loan data file not found at {file_path}"
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Expected columns: customer_id, loan_id, loan_amount, tenure, interest_rate, monthly_repayment, EMIs_paid_on_time, start_date, end_date
        created_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            try:
                customer_id = row.get('Customer ID')
                loan_id = row.get('Loan ID')
                
                # Get customer
                try:
                    customer = Customer.objects.get(customer_id=customer_id)
                except Customer.DoesNotExist:
                    continue  # Skip if customer doesn't exist
                
                # Parse dates
                start_date = pd.to_datetime(row.get('Date of Approval')).date()
                end_date = pd.to_datetime(row.get('End Date')).date()
                
                # Check if loan already exists
                loan, created = Loan.objects.get_or_create(
                    loan_id=loan_id,
                    defaults={
                        'customer': customer,
                        'loan_amount': Decimal(str(row.get('Loan Amount', 0))),
                        'tenure': int(row.get('Tenure', 0)),
                        'interest_rate': Decimal(str(row.get('Interest Rate', 0))),
                        'monthly_repayment': Decimal(str(row.get('Monthly payment', 0))),
                        'emis_paid_on_time': int(row.get('EMIs paid on Time', 0)),
                        'start_date': start_date,
                        'end_date': end_date
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    # Update existing loan
                    loan.customer = customer
                    loan.loan_amount = Decimal(str(row.get('Loan Amount', loan.loan_amount)))
                    loan.tenure = int(row.get('Tenure', loan.tenure))
                    loan.interest_rate = Decimal(str(row.get('Interest Rate', loan.interest_rate)))
                    loan.monthly_repayment = Decimal(str(row.get('Monthly payment', loan.monthly_repayment)))
                    loan.emis_paid_on_time = int(row.get('EMIs paid on Time', loan.emis_paid_on_time))
                    loan.start_date = start_date
                    loan.end_date = end_date
                    loan.save()
                    updated_count += 1
                    
            except Exception as e:
                continue  # Skip problematic rows
        
        return f"Loan data ingestion completed. Created: {created_count}, Updated: {updated_count}"
        
    except Exception as e:
        return f"Error ingesting loan data: {str(e)}"


@shared_task
def ingest_all_data():
    """
    Background task to ingest both customer and loan data
    """
    customer_result = ingest_customer_data()
    loan_result = ingest_loan_data()
    
    return f"Data ingestion completed.\nCustomers: {customer_result}\nLoans: {loan_result}"
