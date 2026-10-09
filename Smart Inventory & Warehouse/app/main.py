from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import router as auth_router
from app.routers.category import router as category_router
from app.routers.product import router as product_router
from app.routers.warehouse import router as warehouse_router
from app.routers.inventory import router as inventory_router
from app.routers.suppliers import router as suppliers_router
from app.routers.purchase_orders import router as purchase_orders_router
from app.routers.customers import router as customers_router
from app.routers.sales_orders import router as sales_orders_router
from app.routers.returns import router as returns_router
from app.routers.reports import router as reports_router
from app.routers.notifications import router as notifications_router
from app.routers.audit_logs import router as audit_logs_router
from app.routers.stock_transfers import router as stock_transfers_router
from app.routers.stock_adjustments import router as stock_adjustments_router
from app.routers.stock_batches import router as stock_batches_router

app = FastAPI(
    title="Smart Inventory & Warehouse Management System",
    description="Complete inventory and warehouse management backend",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(category_router)
app.include_router(product_router)
app.include_router(warehouse_router)
app.include_router(inventory_router)
app.include_router(suppliers_router)
app.include_router(purchase_orders_router)
app.include_router(customers_router)
app.include_router(sales_orders_router)
app.include_router(returns_router)
app.include_router(reports_router)
app.include_router(notifications_router)
app.include_router(audit_logs_router)
app.include_router(stock_transfers_router)
app.include_router(stock_adjustments_router)
app.include_router(stock_batches_router)

@app.get("/")
def root():
    return {
        "message": "Smart Inventory API is running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }