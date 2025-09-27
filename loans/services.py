from django.db.models import Sum, Count, Q
from datetime import datetime, date
from decimal import Decimal
from .models import Customer, Loan


class CreditScoringService:
    """Service class to calculate credit scores based on financial risk assessment"""
    
    @staticmethod
    def calculate_credit_score(customer_id):
        """
        Calculate credit score (0-100) based on:
        1. Past Loans paid on time
        2. Number of loans taken in past
        3. Loan activity in current year
        4. Loan approved volume
        5. If sum of current loans > approved limit, score = 0
        """
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return 0
        
        # Get all loans for this customer
        loans = Loan.objects.filter(customer=customer)
        
        if not loans.exists():
            return 50  # Default score for new customers
        
        # Check if current loans exceed approved limit
        current_loans_sum = loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')
        
        if current_loans_sum > customer.approved_limit:
            return 0
        
        # Initialize score components
        score = 0
        
        # 1. Past Loans paid on time (40 points max)
        total_emis = loans.aggregate(total=Sum('tenure'))['total'] or 0
        paid_on_time = loans.aggregate(total=Sum('emis_paid_on_time'))['total'] or 0
        
        if total_emis > 0:
            on_time_ratio = paid_on_time / total_emis
            score += min(40, on_time_ratio * 40)
        
        # 2. Number of loans taken (20 points max, fewer loans = better)
        loan_count = loans.count()
        if loan_count <= 2:
            score += 20
        elif loan_count <= 5:
            score += 15
        elif loan_count <= 10:
            score += 10
        else:
            score += 5
        
        # 3. Loan activity in current year (20 points max)
        current_year = datetime.now().year
        current_year_loans = loans.filter(start_date__year=current_year).count()
        
        if current_year_loans == 0:
            score += 20  # No new loans this year is good
        elif current_year_loans <= 2:
            score += 15
        elif current_year_loans <= 4:
            score += 10
        else:
            score += 5
        
        # 4. Loan approved volume vs limit (20 points max)
        if customer.approved_limit > 0:
            utilization_ratio = float(current_loans_sum) / float(customer.approved_limit)
            if utilization_ratio <= 0.3:
                score += 20
            elif utilization_ratio <= 0.5:
                score += 15
            elif utilization_ratio <= 0.7:
                score += 10
            else:
                score += 5
        
        return min(100, max(0, int(score)))
    
    @staticmethod
    def check_loan_eligibility(customer_id, loan_amount, interest_rate, tenure):
        """
        Check loan eligibility based on credit score and other criteria
        Returns: (approval, corrected_interest_rate, monthly_installment, message)
        """
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return False, interest_rate, 0, "Customer not found"
        
        credit_score = CreditScoringService.calculate_credit_score(customer_id)
        
        # Check if sum of all current EMIs > 50% of monthly salary
        current_emis = Loan.objects.filter(customer=customer).aggregate(
            total=Sum('monthly_repayment')
        )['total'] or Decimal('0')
        
        # Calculate proposed EMI
        principal = float(loan_amount)
        rate = float(interest_rate) / 100 / 12
        if rate == 0:
            proposed_emi = principal / tenure
        else:
            proposed_emi = principal * rate * ((1 + rate) ** tenure) / (((1 + rate) ** tenure) - 1)
        
        total_emis = float(current_emis) + proposed_emi
        
        if total_emis > (float(customer.monthly_salary) * 0.5):
            return False, interest_rate, proposed_emi, "Total EMIs exceed 50% of monthly salary"
        
        # Determine approval and corrected interest rate based on credit score
        if credit_score > 50:
            # Approve loan with any interest rate
            return True, interest_rate, proposed_emi, "Loan approved"
        elif credit_score > 30:
            # Approve loans with interest rate > 12%
            corrected_rate = max(interest_rate, 12.0)
            if corrected_rate != interest_rate:
                # Recalculate EMI with corrected rate
                rate = corrected_rate / 100 / 12
                if rate == 0:
                    proposed_emi = principal / tenure
                else:
                    proposed_emi = principal * rate * ((1 + rate) ** tenure) / (((1 + rate) ** tenure) - 1)
            return True, corrected_rate, proposed_emi, "Loan approved with corrected interest rate"
        elif credit_score > 10:
            # Approve loans with interest rate > 16%
            corrected_rate = max(interest_rate, 16.0)
            if corrected_rate != interest_rate:
                # Recalculate EMI with corrected rate
                rate = corrected_rate / 100 / 12
                if rate == 0:
                    proposed_emi = principal / tenure
                else:
                    proposed_emi = principal * rate * ((1 + rate) ** tenure) / (((1 + rate) ** tenure) - 1)
            return True, corrected_rate, proposed_emi, "Loan approved with corrected interest rate"
        else:
            # Don't approve any loans
            return False, interest_rate, proposed_emi, "Credit score too low for loan approval"
