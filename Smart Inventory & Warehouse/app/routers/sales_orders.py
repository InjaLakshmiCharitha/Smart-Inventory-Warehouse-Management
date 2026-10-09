
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.models import (
    SalesOrder,
    SalesOrderItem,
    Customer,
    Warehouse,
    Product,
    Inventory,
    User,
    SalesOrderStatus,
    StockMovement,
    StockMovementType,
    StockReservation,
)
from app.schemas.schemas import (
    SalesOrderCreate,
    SalesOrderResponse,
)
from app.services.fefo_service import deduct_stock_using_fefo


router = APIRouter(
    prefix="/sales-orders",
    tags=["Sales Orders"],
)


#  CREATE SALES ORDER
@router.post(
    "",
    response_model=SalesOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sales_order(
    order_data: SalesOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Check customer
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == order_data.customer_id,
                Customer.is_active == True,
            )
            .first()
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found or inactive",
            )

        # Check warehouse
        warehouse = (
            db.query(Warehouse)
            .filter(
                Warehouse.id == order_data.warehouse_id,
                Warehouse.is_active == True,
            )
            .first()
        )

        if warehouse is None:
            raise HTTPException(
                status_code=404,
                detail="Warehouse not found or inactive",
            )

        if not order_data.items:
            raise HTTPException(
                status_code=400,
                detail="At least one order item is required",
            )

        # Generate sales order number
        last_order = (
            db.query(SalesOrder)
            .order_by(SalesOrder.id.desc())
            .first()
        )

        next_number = last_order.id + 1 if last_order else 1
        order_number = f"SO-{next_number:04d}"

        # Create sales order
        sales_order = SalesOrder(
            so_number=order_number,
            customer_id=order_data.customer_id,
            warehouse_id=order_data.warehouse_id,
            status=SalesOrderStatus.DRAFT,
            subtotal=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            grand_total=Decimal("0.00"),
            created_by=current_user.id,
        )

        db.add(sales_order)
        db.flush()

        total_amount = Decimal("0.00")

        # Process each product in the order
        for item_data in order_data.items:
            if item_data.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Item quantity must be greater than zero",
                )

            # Find active product
            product = (
                db.query(Product)
                .filter(
                    Product.id == item_data.product_id,
                    Product.is_active == True,
                )
                .first()
            )

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item_data.product_id} not found or inactive",
                )

            # Find product inventory in the selected warehouse
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == product.id,
                    Inventory.warehouse_id == order_data.warehouse_id,
                )
                .first()
            )

            if inventory is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"No inventory found for product {product.id} in this warehouse",
                )

            # Check available stock
            available_stock = (
                inventory.quantity_on_hand
                - inventory.quantity_reserved
            )

            if item_data.quantity > available_stock:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient stock for {product.product_name}. "
                        f"Available: {available_stock}, "
                        f"Requested: {item_data.quantity}"
                    ),
                )

            # Calculate item amount
            unit_price = Decimal(str(product.selling_price))
            line_total = unit_price * item_data.quantity

            # Create sales order item
            order_item = SalesOrderItem(
                sales_order_id=sales_order.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                line_total=line_total,
                created_by=current_user.id,
            )

            db.add(order_item)
            total_amount += line_total

        # Save order totals
        sales_order.subtotal = total_amount
        sales_order.tax_amount = Decimal("0.00")
        sales_order.grand_total = total_amount

        db.commit()
        db.refresh(sales_order)

        return sales_order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


# GET ALL SALES ORDERS
@router.get(
    "",
    response_model=list[SalesOrderResponse],
)
def get_sales_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(SalesOrder)
        .order_by(SalesOrder.id.desc())
        .all()
    )


# GET SALES ORDER BY ID
@router.get(
    "/{order_id}",
    response_model=SalesOrderResponse,
)
def get_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(SalesOrder)
        .filter(SalesOrder.id == order_id)
        .first()
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Sales order not found",
        )

    return order


# CONFIRM SALES ORDER AND RESERVE STOCK
@router.post(
    "/{order_id}/confirm",
    response_model=SalesOrderResponse,
)
def confirm_sales_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sales_order = (
            db.query(SalesOrder)
            .filter(SalesOrder.id == order_id)
            .with_for_update()
            .first()
        )

        if sales_order is None:
            raise HTTPException(
                status_code=404,
                detail="Sales order not found",
            )

        if sales_order.status != SalesOrderStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail="Only Draft orders can be confirmed",
            )

        # Check stock for every item before reserving anything
        for item in sales_order.items:
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == sales_order.warehouse_id,
                )
                .with_for_update()
                .first()
            )

            if inventory is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inventory not found for product {item.product_id}",
                )

            available_stock = (
                inventory.quantity_on_hand
                - inventory.quantity_reserved
            )

            if item.quantity > available_stock:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Insufficient stock for product {item.product_id}. "
                        f"Available: {available_stock}, "
                        f"Requested: {item.quantity}"
                    ),
                )

        # Reserve stock after all items pass validation
        for item in sales_order.items:
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == item.product_id,
                    Inventory.warehouse_id == sales_order.warehouse_id,
                )
                .with_for_update()
                .first()
            )

            inventory.quantity_reserved += item.quantity

            reservation = StockReservation(
                sales_order_id=sales_order.id,
                product_id=item.product_id,
                warehouse_id=sales_order.warehouse_id,
                quantity=item.quantity,
            )

            db.add(reservation)

        sales_order.status = SalesOrderStatus.CONFIRMED

        db.commit()
        db.refresh(sales_order)

        return sales_order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


# DISPATCH SALES ORDER
@router.post(
    "/{order_id}/dispatch",
    response_model=SalesOrderResponse,
)
def dispatch_sales_order(
    order_id: int,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
):
    try:
        sales_order = (
            db.query(SalesOrder)
            .filter(SalesOrder.id == order_id)
            .with_for_update()
            .first()
        )

        if sales_order is None:
            raise HTTPException(
                status_code=404,
                detail="Sales order not found",
            )

        if sales_order.status != SalesOrderStatus.CONFIRMED:
            raise HTTPException(
                status_code=400,
                detail="Only Confirmed orders can be dispatched",
            )

        reservations = (
            db.query(StockReservation)
            .filter(
                StockReservation.sales_order_id == sales_order.id,
            )
            .all()
        )

        if not reservations:
            raise HTTPException(
                status_code=400,
                detail="No active stock reservations found",
            )

        # Verify all inventory before deducting stock
        for reservation in reservations:
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == reservation.product_id,
                    Inventory.warehouse_id == reservation.warehouse_id,
                )
                .with_for_update()
                .first()
            )

            if inventory is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inventory not found for product {reservation.product_id}",
                )

            if inventory.quantity_reserved < reservation.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reserved stock is insufficient for product {reservation.product_id}",
                )

            if inventory.quantity_on_hand < reservation.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Physical stock is insufficient for product {reservation.product_id}",
                )

        # Generate a tracking number
        tracking_number = f"TRK-{sales_order.id:06d}"

        # Dispatch each reservation
        for reservation in reservations:
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == reservation.product_id,
                    Inventory.warehouse_id == reservation.warehouse_id,
                )
                .with_for_update()
                .first()
            )

            # Deduct batches using FEFO
            deduct_stock_using_fefo(
                db=db,
                product_id=reservation.product_id,
                warehouse_id=reservation.warehouse_id,
                quantity=reservation.quantity,
            )

            # Update overall inventory
            inventory.quantity_on_hand -= reservation.quantity
            inventory.quantity_reserved -= reservation.quantity

            # Record stock movement
            movement = StockMovement(
                product_id=reservation.product_id,
                warehouse_id=reservation.warehouse_id,
                movement_type=StockMovementType.SALE_DISPATCH,
                quantity=reservation.quantity,
                reference_id=sales_order.id,
                balance_after=inventory.quantity_on_hand,
                performed_by=current_user.id,
            )

            db.add(movement)

            # Mark reservation as dispatched
            reservation.status = "Dispatched"

        # Update sales order
        sales_order.status = SalesOrderStatus.DISPATCHED
        sales_order.tracking_number = tracking_number

        db.commit()
        db.refresh(sales_order)

        return sales_order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
