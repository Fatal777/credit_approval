from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationSerializer,
    CustomerRegistrationResponseSerializer,
    LoanEligibilityRequestSerializer,
    LoanEligibilityResponseSerializer,
    LoanCreateRequestSerializer,
    LoanCreateResponseSerializer,
    LoanDetailSerializer,
    CustomerLoanSerializer
)
from .services import CreditScoringService


@api_view(['POST'])
def register_customer(request):
    """
    Register a new customer with approved limit based on salary
    """
    serializer = CustomerRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        customer = serializer.save()
        response_serializer = CustomerRegistrationResponseSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def check_eligibility(request):
    """
    Check loan eligibility based on credit score
    """
    serializer = LoanEligibilityRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    customer_id = data['customer_id']
    loan_amount = data['loan_amount']
    interest_rate = data['interest_rate']
    tenure = data['tenure']
    
    # Check if customer exists
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check eligibility using the service
    approval, corrected_rate, monthly_installment, message = CreditScoringService.check_loan_eligibility(
        customer_id, loan_amount, interest_rate, tenure
    )
    
    response_data = {
        'customer_id': customer_id,
        'approval': approval,
        'interest_rate': float(interest_rate),
        'corrected_interest_rate': float(corrected_rate),
        'tenure': tenure,
        'monthly_installment': round(monthly_installment, 2)
    }
    
    response_serializer = LoanEligibilityResponseSerializer(response_data)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_loan(request):
    """
    Process a new loan based on eligibility
    """
    serializer = LoanCreateRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    customer_id = data['customer_id']
    loan_amount = data['loan_amount']
    interest_rate = data['interest_rate']
    tenure = data['tenure']
    
    # Check if customer exists
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check eligibility
    approval, corrected_rate, monthly_installment, message = CreditScoringService.check_loan_eligibility(
        customer_id, loan_amount, interest_rate, tenure
    )
    
    loan_id = None
    
    if approval:
        # Create the loan
        start_date = date.today()
        end_date = start_date + relativedelta(months=tenure)
        
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=loan_amount,
            tenure=tenure,
            interest_rate=corrected_rate,
            monthly_repayment=Decimal(str(monthly_installment)),
            start_date=start_date,
            end_date=end_date
        )
        loan_id = loan.loan_id
        
        # Update customer's current debt
        customer.current_debt += loan_amount
        customer.save()
    
    response_data = {
        'loan_id': loan_id,
        'customer_id': customer_id,
        'loan_approved': approval,
        'message': message,
        'monthly_installment': round(monthly_installment, 2)
    }
    
    response_serializer = LoanCreateResponseSerializer(response_data)
    return Response(response_serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def view_loan(request, loan_id):
    """
    View loan details and customer details
    """
    try:
        loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response(
            {'error': 'Loan not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def view_loans_by_customer(request, customer_id):
    """
    View all current loan details by customer id
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    loans = Loan.objects.filter(customer=customer)
    serializer = CustomerLoanSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
