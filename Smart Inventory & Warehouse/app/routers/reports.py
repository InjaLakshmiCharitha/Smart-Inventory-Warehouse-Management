from decimal import Decimal
from io import BytesIO

from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.models import (
    User,
    Product,
    Inventory,
    PurchaseOrder,
    PurchaseOrderItem,
    SalesOrder,
    SalesOrderItem,
    PurchaseOrderStatus,
    SalesOrderStatus,
    UserRole,
    Warehouse
)


router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


# INVENTORY SUMMARY
@router.get("/inventory-summary")
def inventory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .count()
    )

    total_inventory_records = (
        db.query(Inventory)
        .count()
    )

    total_stock = (
        db.query(
            func.coalesce(
                func.sum(Inventory.quantity_on_hand),
                0
            )
        )
        .scalar()
    )

    total_reserved = (
        db.query(
            func.coalesce(
                func.sum(Inventory.quantity_reserved),
                0
            )
        )
        .scalar()
    )

    total_available = total_stock - total_reserved

    return {
        "total_products": total_products,
        "total_inventory_records": total_inventory_records,
        "total_stock": total_stock,
        "total_reserved": total_reserved,
        "total_available": total_available
    }


# LOW STOCK REPORT
@router.get("/low-stock")
def low_stock_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Product.reorder_level,
            Product.reorder_quantity,
            Inventory.warehouse_id,
            Inventory.quantity_on_hand,
            Inventory.quantity_reserved
        )
        .join(
            Inventory,
            Inventory.product_id == Product.id
        )
        .filter(
            Product.is_active == True,
            Inventory.quantity_on_hand
            <= Product.reorder_level
        )
        .order_by(
            Inventory.quantity_on_hand.asc()
        )
        .all()
    )

    result = []

    for row in rows:
        available = (
            row.quantity_on_hand
            - row.quantity_reserved
        )

        result.append({
            "product_id": row.product_id,
            "sku": row.sku,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "quantity_on_hand": row.quantity_on_hand,
            "quantity_reserved": row.quantity_reserved,
            "quantity_available": available,
            "reorder_level": row.reorder_level,
            "reorder_quantity": row.reorder_quantity
        })

    return {
        "count": len(result),
        "items": result
    }


# SALES SUMMARY
@router.get("/sales-summary")
def sales_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    completed_statuses = [
        SalesOrderStatus.CONFIRMED,
        SalesOrderStatus.PICKED,
        SalesOrderStatus.PACKED,
        SalesOrderStatus.DISPATCHED,
        SalesOrderStatus.DELIVERED
    ]

    total_orders = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.status.in_(completed_statuses)
        )
        .count()
    )

    total_sales = (
        db.query(
            func.coalesce(
                func.sum(SalesOrder.total_amount),
                0
            )
        )
        .filter(
            SalesOrder.status.in_(completed_statuses)
        )
        .scalar()
    )

    total_items = (
        db.query(
            func.coalesce(
                func.sum(SalesOrderItem.quantity),
                0
            )
        )
        .join(
            SalesOrder,
            SalesOrder.id
            == SalesOrderItem.sales_order_id
        )
        .filter(
            SalesOrder.status.in_(completed_statuses)
        )
        .scalar()
    )

    return {
        "total_orders": total_orders,
        "total_sales": total_sales,
        "total_items_sold": total_items
    }


# PURCHASE SUMMARY
@router.get("/purchase-summary")
def purchase_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    completed_statuses = [
        PurchaseOrderStatus.APPROVED,
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
        PurchaseOrderStatus.RECEIVED
    ]

    total_orders = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.status.in_(completed_statuses)
        )
        .count()
    )

    total_purchase_value = (
        db.query(
            func.coalesce(
                func.sum(PurchaseOrder.total_amount),
                0
            )
        )
        .filter(
            PurchaseOrder.status.in_(completed_statuses)
        )
        .scalar()
    )

    total_items = (
        db.query(
            func.coalesce(
                func.sum(PurchaseOrderItem.quantity_received),
                0
            )
        )
        .join(
            PurchaseOrder,
            PurchaseOrder.id
            == PurchaseOrderItem.purchase_order_id
        )
        .filter(
            PurchaseOrder.status.in_(completed_statuses)
        )
        .scalar()
    )

    return {
        "total_purchase_orders": total_orders,
        "total_purchase_value": total_purchase_value,
        "total_items_received": total_items
    }


# INVENTORY VALUATION
@router.get("/inventory-valuation")
def inventory_valuation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Inventory.warehouse_id,
            Inventory.quantity_on_hand,
            Inventory.average_cost
        )
        .join(
            Inventory,
            Inventory.product_id == Product.id
        )
        .filter(
            Product.is_active == True
        )
        .all()
    )

    result = []
    total_value = Decimal("0")

    for row in rows:
        value = (
            Decimal(str(row.quantity_on_hand))
            * Decimal(str(row.average_cost))
        )

        total_value += value

        result.append({
            "product_id": row.product_id,
            "sku": row.sku,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "quantity_on_hand": row.quantity_on_hand,
            "average_cost": row.average_cost,
            "inventory_value": value
        })

    return {
        "total_inventory_value": total_value,
        "items": result
    }


# EXPORT INVENTORY EXCEL
@router.get("/inventory/export-excel")
def export_inventory_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    inventory_records = (
        db.query(
            Inventory,
            Product,
            Warehouse
        )
        .join(Product, Inventory.product_id == Product.id)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .all()
    )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Inventory Report"

    # Header row
    headers = [
        "Inventory ID",
        "Product ID",
        "SKU",
        "Product Name",
        "Warehouse ID",
        "Warehouse Name",
        "Quantity On Hand",
        "Quantity Reserved",
        "Quantity Available",
        "Average Cost",
        "Inventory Value"
    ]

    worksheet.append(headers)

    # Data rows
    for inventory, product, warehouse in inventory_records:

        quantity_available = (
            inventory.quantity_on_hand
            - inventory.quantity_reserved
        )

        inventory_value = (
            quantity_available
            * inventory.average_cost
        )

        worksheet.append([
            inventory.id,
            product.id,
            product.sku,
            product.product_name,
            warehouse.id,
            warehouse.warehouse_name,
            inventory.quantity_on_hand,
            inventory.quantity_reserved,
            quantity_available,
            float(inventory.average_cost),
            float(inventory_value)
        ])

    # Make columns wider
    column_widths = {
        "A": 15,
        "B": 12,
        "C": 20,
        "D": 25,
        "E": 15,
        "F": 25,
        "G": 20,
        "H": 20,
        "I": 20,
        "J": 18,
        "K": 20
    }

    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width

    # Save Excel file in memory
    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                "attachment; filename=inventory_report.xlsx"
        }
    )