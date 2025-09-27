# Credit Approval System

A Django-based backend system for credit approval with automated credit scoring and loan management.

## Features

- **Customer Registration** with automatic credit limit calculation
- **Credit Scoring Algorithm** based on historical loan data
- **Loan Eligibility Check** with interest rate correction
- **Loan Creation and Management**
- **Background Data Ingestion** using Celery
- **Dockerized Application** with PostgreSQL and Redis

## Tech Stack

- **Backend**: Django 4+ with Django Rest Framework
- **Database**: PostgreSQL
- **Cache/Message Broker**: Redis
- **Background Tasks**: Celery
- **Containerization**: Docker & Docker Compose

## API Endpoints

### 1. Register Customer
- **URL**: `POST /register/`
- **Description**: Add a new customer with approved limit based on salary
- **Request Body**:
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": 9876543210
}
```

### 2. Check Eligibility
- **URL**: `POST /check-eligibility/`
- **Description**: Check loan eligibility based on credit score
- **Request Body**:
```json
{
    "customer_id": 1,
    "loan_amount": 100000,
    "interest_rate": 10.5,
    "tenure": 12
}
```

### 3. Create Loan
- **URL**: `POST /create-loan/`
- **Description**: Process a new loan based on eligibility
- **Request Body**:
```json
{
    "customer_id": 1,
    "loan_amount": 100000,
    "interest_rate": 10.5,
    "tenure": 12
}
```

### 4. View Loan Details
- **URL**: `GET /view-loan/{loan_id}/`
- **Description**: View specific loan details with customer information

### 5. View Customer Loans
- **URL**: `GET /view-loans/{customer_id}/`
- **Description**: View all loans for a specific customer

## Credit Scoring Algorithm

The system calculates credit scores (0-100) based on:

1. **Past Loans Paid on Time** (40 points max)
2. **Number of Loans Taken** (20 points max - fewer is better)
3. **Loan Activity in Current Year** (20 points max)
4. **Loan Approved Volume vs Limit** (20 points max)

### Approval Rules:
- **Credit Score > 50**: Approve with any interest rate
- **30 < Credit Score ≤ 50**: Approve with interest rate > 12%
- **10 < Credit Score ≤ 30**: Approve with interest rate > 16%
- **Credit Score ≤ 10**: Reject loan
- **Total EMIs > 50% of salary**: Reject loan

## Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Git

### Quick Start

1. **Clone the repository**:
```bash
git clone <repository-url>
cd credit_approval
```

2. **Place data files**:
   - Ensure `customer_data.xlsx` and `loan_data.xlsx` are in the project root

3. **Start the application**:
```powershell
docker-compose up -d
```

4. **Verify services are running**:
```powershell
docker-compose ps
```

5. **Test server connectivity**:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/admin/" -Method GET
```

6. **Ingest initial data using background workers**:
```powershell
docker-compose exec web python manage.py ingest_data
```

The application will be available at `http://localhost:8000`

### Manual Setup (Without Docker)

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL and Redis**:
   - Install PostgreSQL and create database `credit_approval`
   - Install and start Redis server

4. **Set environment variables**:
```bash
export DATABASE_URL=postgresql://postgres:password@localhost:5432/credit_approval
export REDIS_URL=redis://localhost:6379/0
```

5. **Run migrations**:
```bash
python manage.py migrate
```

6. **Start Celery worker** (in separate terminal):
```bash
celery -A credit_approval worker --loglevel=info
```

7. **Start Django server**:
```bash
python manage.py runserver
```

8. **Ingest data**:
```bash
python manage.py ingest_data
```

## Project Structure

```
credit_approval/
├── credit_approval/          # Main project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── loans/                    # Main application
│   ├── models.py            # Customer and Loan models
│   ├── views.py             # API endpoints
│   ├── serializers.py       # DRF serializers
│   ├── services.py          # Credit scoring logic
│   ├── tasks.py             # Celery background tasks
│   ├── admin.py             # Django admin configuration
│   └── management/commands/ # Custom management commands
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker services configuration
├── Dockerfile              # Docker image configuration
└── README.md               # This file
```

## Testing the API

### PowerShell Commands (Windows):

1. **Test existing customer with loan history (should be rejected)**:
```powershell
(Invoke-RestMethod -Uri "http://localhost:8000/check-eligibility/" -Method POST -Body (@{customer_id=1;loan_amount=100000;interest_rate=8.0;tenure=12} | ConvertTo-Json) -ContentType "application/json") | ConvertTo-Json
```

2. **Register new customer (no history)**:
```powershell
$newCustomer = Invoke-RestMethod -Uri "http://localhost:8000/register/" -Method POST -Body (@{first_name="Demo";last_name="Customer";age=35;monthly_income=80000;phone_number=9876543210} | ConvertTo-Json) -ContentType "application/json"
$newCustomer | ConvertTo-Json
$customerId = $newCustomer.customer_id
```

3. **Check eligibility for new customer**:
```powershell
$eligibility = Invoke-RestMethod -Uri "http://localhost:8000/check-eligibility/" -Method POST -Body (@{customer_id=$customerId;loan_amount=150000;interest_rate=9.0;tenure=18} | ConvertTo-Json) -ContentType "application/json"
$eligibility | ConvertTo-Json
```

4. **Create loan for approved customer**:
```powershell
$loan = Invoke-RestMethod -Uri "http://localhost:8000/create-loan/" -Method POST -Body (@{customer_id=$customerId;loan_amount=150000;interest_rate=12.0;tenure=18} | ConvertTo-Json) -ContentType "application/json"
$loan | ConvertTo-Json
$loanId = $loan.loan_id
```

5. **View created loan details**:
```powershell
(Invoke-RestMethod -Uri "http://localhost:8000/view-loan/$loanId/" -Method GET) | ConvertTo-Json
```

6. **View all loans for the customer**:
```powershell
(Invoke-RestMethod -Uri "http://localhost:8000/view-loans/$customerId/" -Method GET) | ConvertTo-Json
git s```

### Expected Results:
- **Customer 1**: Rejected due to poor credit history from historical data
- **New Customer**: Approved with corrected interest rate (demonstrates credit scoring)
- **Loan Creation**: Successfully creates loan for eligible customers
- **Loan Views**: Shows complete loan and customer information

### Demo Flow:
1. First command shows rejection for existing customer with poor history
2. Second command registers a fresh customer and returns their ID
3. Use that customer ID in subsequent commands
4. New customers typically get approved with corrected interest rates

### Using curl (Linux/Mac):
```bash
# Test existing customer eligibility
curl -X POST http://localhost:8000/check-eligibility/ \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "loan_amount": 100000, "interest_rate": 8.0, "tenure": 12}'

# Register new customer
curl -X POST http://localhost:8000/register/ \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Test", "last_name": "User", "age": 30, "monthly_income": 60000, "phone_number": 9876543210}'
```

## Monitoring

- **Django Admin**: `http://localhost:8000/admin/`
- **Database**: Connect to PostgreSQL on `localhost:5432`
- **Redis**: Connect to Redis on `localhost:6379`
- **Celery**: Monitor worker logs in the terminal

## Development Notes

- The application uses compound interest for EMI calculations
- Credit limits are rounded to the nearest lakh (100,000)
- All monetary values use Decimal for precision
- Background tasks handle large data ingestion operations
- Comprehensive error handling and validation included

## Troubleshooting

1. **Database connection issues**: Ensure PostgreSQL is running and credentials are correct
2. **Celery tasks not running**: Check Redis connection and ensure Celery worker is started
3. **Data ingestion fails**: Verify Excel files are in the correct format and location
4. **Docker issues**: Try `docker-compose down` and `docker-compose up --build`

## Future Enhancements

- Add authentication and authorization
- Implement loan repayment tracking
- Add email notifications for loan approvals
- Create dashboard for loan analytics
- Add API rate limiting
- Implement comprehensive logging
