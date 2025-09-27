from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from .models import Customer, Loan
from .services import CreditScoringService


class CustomerModelTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="John",
            last_name="Doe",
            age=30,
            phone_number=9876543210,
            monthly_salary=Decimal('50000'),
            approved_limit=Decimal('1800000')
        )

    def test_customer_creation(self):
        self.assertEqual(self.customer.first_name, "John")
        self.assertEqual(self.customer.name, "John Doe")
        self.assertEqual(self.customer.monthly_salary, Decimal('50000'))

    def test_approved_limit_calculation(self):
        calculated_limit = self.customer.calculate_approved_limit()
        expected_limit = round((50000 * 36) / 100000) * 100000
        self.assertEqual(calculated_limit, expected_limit)


class LoanModelTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Jane",
            last_name="Smith",
            age=25,
            phone_number=9876543211,
            monthly_salary=Decimal('60000'),
            approved_limit=Decimal('2200000')
        )
        
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('10.5'),
            monthly_repayment=Decimal('8792.59'),
            start_date=date.today(),
            end_date=date.today() + relativedelta(months=12)
        )

    def test_loan_creation(self):
        self.assertEqual(self.loan.customer, self.customer)
        self.assertEqual(self.loan.loan_amount, Decimal('100000'))
        self.assertEqual(self.loan.tenure, 12)

    def test_repayments_left(self):
        self.loan.emis_paid_on_time = 5
        self.loan.save()
        self.assertEqual(self.loan.repayments_left, 7)

    def test_monthly_installment_calculation(self):
        calculated_emi = self.loan.calculate_monthly_installment()
        self.assertIsInstance(calculated_emi, float)
        self.assertGreater(calculated_emi, 0)


class CreditScoringServiceTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            age=35,
            phone_number=9876543212,
            monthly_salary=Decimal('75000'),
            approved_limit=Decimal('2700000')
        )

    def test_credit_score_new_customer(self):
        score = CreditScoringService.calculate_credit_score(self.customer.customer_id)
        self.assertEqual(score, 50)  # Default score for new customers

    def test_credit_score_with_loans(self):
        # Create a loan with good payment history
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('50000'),
            tenure=12,
            interest_rate=Decimal('12.0'),
            monthly_repayment=Decimal('4500'),
            emis_paid_on_time=12,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
        
        score = CreditScoringService.calculate_credit_score(self.customer.customer_id)
        self.assertGreater(score, 50)

    def test_loan_eligibility_high_score(self):
        # Mock a high credit score scenario
        approval, corrected_rate, emi, message = CreditScoringService.check_loan_eligibility(
            self.customer.customer_id, Decimal('100000'), Decimal('8.0'), 12
        )
        self.assertTrue(approval)
        self.assertEqual(corrected_rate, 8.0)


class APIEndpointsTest(APITestCase):
    def test_register_customer(self):
        url = reverse('register_customer')
        data = {
            'first_name': 'API',
            'last_name': 'Test',
            'age': 28,
            'monthly_income': 45000,
            'phone_number': 9876543213
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)
        self.assertEqual(response.data['name'], 'API Test')

    def test_register_customer_invalid_data(self):
        url = reverse('register_customer')
        data = {
            'first_name': '',  # Invalid: empty name
            'age': 15,  # Invalid: too young
            'monthly_income': 45000,
            'phone_number': 9876543213
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_eligibility_customer_not_found(self):
        url = reverse('check_eligibility')
        data = {
            'customer_id': 999,  # Non-existent customer
            'loan_amount': 100000,
            'interest_rate': 10.5,
            'tenure': 12
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_loan_not_found(self):
        url = reverse('view_loan', kwargs={'loan_id': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_loans_customer_not_found(self):
        url = reverse('view_loans_by_customer', kwargs={'customer_id': 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class IntegrationTest(APITestCase):
    def test_complete_loan_flow(self):
        # 1. Register customer
        register_url = reverse('register_customer')
        customer_data = {
            'first_name': 'Integration',
            'last_name': 'Test',
            'age': 32,
            'monthly_income': 80000,
            'phone_number': 9876543214
        }
        register_response = self.client.post(register_url, customer_data, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        customer_id = register_response.data['customer_id']

        # 2. Check eligibility
        eligibility_url = reverse('check_eligibility')
        eligibility_data = {
            'customer_id': customer_id,
            'loan_amount': 200000,
            'interest_rate': 11.0,
            'tenure': 24
        }
        eligibility_response = self.client.post(eligibility_url, eligibility_data, format='json')
        self.assertEqual(eligibility_response.status_code, status.HTTP_200_OK)

        # 3. Create loan (if eligible)
        if eligibility_response.data['approval']:
            create_loan_url = reverse('create_loan')
            loan_response = self.client.post(create_loan_url, eligibility_data, format='json')
            self.assertEqual(loan_response.status_code, status.HTTP_200_OK)
            
            if loan_response.data['loan_approved']:
                loan_id = loan_response.data['loan_id']
                
                # 4. View loan details
                view_loan_url = reverse('view_loan', kwargs={'loan_id': loan_id})
                loan_detail_response = self.client.get(view_loan_url)
                self.assertEqual(loan_detail_response.status_code, status.HTTP_200_OK)
                
                # 5. View customer loans
                view_loans_url = reverse('view_loans_by_customer', kwargs={'customer_id': customer_id})
                customer_loans_response = self.client.get(view_loans_url)
                self.assertEqual(customer_loans_response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(customer_loans_response.data), 1)
