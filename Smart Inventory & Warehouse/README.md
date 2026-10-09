# Smart Inventory & Warehouse Management System

# Project Overview

The "Smart Inventory & Warehouse Management System" is a backend application developed using FastAPI and Python. It helps manage products, warehouses, inventory, suppliers, purchase orders, sales orders, stock reservations, dispatch, returns, reports, notifications, and audit logs.

The system provides RESTful APIs for inventory operations and uses JWT authentication and role-based access control to secure the application.

# Objectives

- Manage products and warehouses.
- Track inventory quantities and stock movements.
- Manage suppliers and purchase orders.
- Manage customers and sales orders.
- Reserve stock and dispatch sales orders.
- Handle product batches and expiry dates.
- Support product returns.
- Generate inventory and business reports.
- Provide authentication and authorization.
- Maintain database migrations and audit records.
- Test APIs using Swagger UI and automated tests.

# Technologies Used

- Python 3.9+
- FastAPI
- Pydantic
- SQLAlchemy
- MySQL
- Alembic
- JWT authentication
- Passlib with bcrypt
- SMTP email notification
- Uvicorn
- Pytest

# Project Structure

Smart Inventory & Warehouse/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   └── auth/
│
├── alembic/
├── alembic.ini
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── tests/


# Main Features

# Product Management
- Create and retrieve products.
- Maintain product information and pricing.
- Validate product data.

# Warehouse Management
- Create and manage warehouse information.
- Track inventory by warehouse.

# Inventory Management
- Track available stock.
- Receive and deduct stock.
- Maintain batch-wise quantities.
- Support stock reservations and stock movements.

# Supplier Management
- Register suppliers.
- Retrieve supplier information.
- Associate suppliers with purchase orders.

# Purchase Order Management
- Create purchase orders.
- Add products and quantities to orders.
- Approve purchase orders.
- Receive ordered stock into inventory.

# Customer Management
- Register customers.
- Retrieve customer information.
- Associate customers with sales orders.

# Sales Order Management
- Create sales orders.
- Calculate order totals.
- Confirm orders and reserve stock.
- Dispatch confirmed orders.

# Batch Management
- Create and retrieve product batches.
- Track batch numbers, quantities, unit costs, and expiry dates.
- Support FEFO (First Expiry, First Out) stock deduction where implemented.

# Returns Management
- Support product-return operations through the returns APIs.
- Validate return quantities and update inventory according to the implemented business rules.

# Security
- JWT-based authentication.
- Password hashing.
- Role-based access control for protected operations.

# Additional Modules
- Reports
- Notifications
- Audit logs

The availability of individual operations depends on the implemented routes and business logic.

# Installation and Setup

# Create a Virtual Environment

- python -m venv venv

- Activate it on Windows: venv\Scripts\activate

# Install Dependencies

pip install -r requirements.txt

# Configure the Database

- Create the MySQL database:
CREATE DATABASE smart_inventory_warehouse_db;

- Configure the database connection and JWT secret in the `.env` file. Use the variable names expected by your application.


# Apply Database Migrations
Run:
alembic upgrade head
This applies the available Alembic migrations to the database.

# Start the Application

* Run the following command from the project root:
uvicorn app.main:app --reload

* The application should start at:
http://127.0.0.1:8000

# API Documentation and Testing

Open Swagger UI:
**http://127.0.0.1:8000/docs**

- Swagger UI allows you to:
1. View available API endpoints.
2. Enter request data in JSON format.
3. Execute GET, POST, PUT, and DELETE requests where supported.
4. Inspect response status codes and response bodies.
5. Test authentication and protected endpoints.

- For JWT-protected endpoints:
1. Call the login endpoint.
2. Copy the returned access token.
3. Click **Authorize** in Swagger UI.
4. Enter the token in the format expected by the configured authentication scheme.
5. Execute the protected endpoints.


# API Workflow

1. Create a product.
2. Create a warehouse.
3. Register a supplier.
4. Create a purchase order.
5. Approve the purchase order.
6. Receive the purchase order and add stock.
7. Create a customer.
8. Create a sales order.
9. Confirm the sales order and reserve stock.
10. Dispatch the sales order.
11. Test the returns API if the return workflow is implemented.
12. Verify inventory and reports.

Use the IDs returned by your actual API responses. The exact endpoint paths and required JSON fields are available in Swagger UI.

# Database Migrations

- Alembic is used to manage database schema changes.

- Apply migrations: alembic upgrade head

- Check the current migration: alembic current

- View migration history: alembic history

When the SQLAlchemy models change, create and review a migration before applying it to the database.

## 10. Automated Testing

- Run the project's automated tests using: python -m pytest -v

API testing through Swagger and automated testing through Pytest are separate activities. Confirm the test results before reporting complete test coverage.

# Error Handling and Validation

The application uses FastAPI and Pydantic to validate API request data. HTTP status codes help identify successful operations and errors.

Common responses include:
- '200 OK' — request completed successfully.
- '201 Created' — resource created successfully.
- '400 Bad Request' — business-rule validation failure.
- '401 Unauthorized' — authentication required or invalid.
- '403 Forbidden' — insufficient permissions.
- '404 Not Found' — requested resource not found.
- '422 Unprocessable Entity' — request validation failed.
- '500 Internal Server Error' — unexpected server-side failure.

The exact status code depends on the endpoint implementation.

# Security Considerations

- Store database credentials in environment variables.
- Never commit secrets to version control.
- Hash passwords instead of storing plaintext passwords.
- Protect restricted endpoints using JWT authentication.
- Enforce role permissions on the backend.
- Validate incoming request data.
- Use database transactions for operations that modify related records.


# Conclusion

The Smart Inventory & Warehouse Management System provides a FastAPI backend for managing warehouse and inventory operations. It combines REST APIs, relational database management, data validation, authentication, database migrations, and business workflows such as purchase order receiving, sales order confirmation, stock reservation, and dispatch.

The project demonstrates practical backend development concepts using Python, FastAPI, SQLAlchemy, MySQL, Alembic, and JWT authentication.
