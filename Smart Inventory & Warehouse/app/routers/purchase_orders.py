from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
    Warehouse,
    Product,
    Inventory,
    StockMovement,
    User,
    UserRole,
    PurchaseOrderStatus,
    StockMovementType
)
from app.schemas.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
)
from app.auth.dependencies import (
    get_current_user,
    require_roles,
)


router = APIRouter(
    prefix="/purchase-orders",
    tags=["Purchase Orders"]
)


# CREATE PURCHASE ORDER
@router.post(
    "",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED
)
def create_purchase_order(
    po_data: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):

   
    # CHECK SUPPLIER
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == po_data.supplier_id,
            Supplier.is_active == True
        )
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Active supplier not found"
        )

   
    # CHECK WAREHOUSE
    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.id == po_data.warehouse_id,
            Warehouse.is_active == True
        )
        .first()
    )

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Active warehouse not found"
        )


    # GENERATE PO NUMBER
    last_po = (
        db.query(PurchaseOrder)
        .order_by(PurchaseOrder.id.desc())
        .first()
    )

    if last_po:
        next_number = last_po.id + 1
    else:
        next_number = 1

    po_number = f"PO-{next_number:04d}"


    # CREATE PURCHASE ORDER
    purchase_order = PurchaseOrder(
        po_number=po_number,
        supplier_id=po_data.supplier_id,
        warehouse_id=po_data.warehouse_id,
        status=PurchaseOrderStatus.DRAFT.value,
        total_amount=Decimal("0.00"),
        created_by=current_user.id
    )

    db.add(purchase_order)
    db.flush()


    # CREATE PURCHASE ORDER ITEMS
    total_amount = Decimal("0.00")

    for item in po_data.items:

        # Check product
        product = (
            db.query(Product)
            .filter(
                Product.id == item.product_id,
                Product.is_active == True
            )
            .first()
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Validate quantity
        if item.quantity_ordered <= 0:
            raise HTTPException(
                status_code=400,
                detail="Quantity ordered must be greater than zero"
            )

        # Validate unit cost
        if item.unit_cost < 0:
            raise HTTPException(
                status_code=400,
                detail="Unit cost cannot be negative"
            )

        subtotal = (
            Decimal(str(item.quantity_ordered))
            * Decimal(str(item.unit_cost))
        )

        po_item = PurchaseOrderItem(
            purchase_order_id=purchase_order.id,
            product_id=item.product_id,
            quantity_ordered=item.quantity_ordered,
            quantity_received=0,
            unit_cost=item.unit_cost
        )

        db.add(po_item)

        total_amount += subtotal

    # UPDATE TOTAL
    purchase_order.total_amount = total_amount

    db.commit()
    db.refresh(purchase_order)

    return purchase_order


# GET ALL PURCHASE ORDERS
@router.get(
    "",
    response_model=list[PurchaseOrderResponse]
)
def get_purchase_orders(
    status_filter: Optional[PurchaseOrderStatus] = Query(
        default=None,
        alias="status"
    ),
    supplier_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    page: int = Query(
        default=1,
        ge=1
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = db.query(PurchaseOrder)

    # Filter by status
    if status_filter:
        query = query.filter(
            PurchaseOrder.status == status_filter.value
        )

    # Filter by supplier
    if supplier_id:
        query = query.filter(
            PurchaseOrder.supplier_id == supplier_id
        )

    # Filter by warehouse
    if warehouse_id:
        query = query.filter(
            PurchaseOrder.warehouse_id == warehouse_id
        )

    # Pagination
    offset = (page - 1) * page_size

    purchase_orders = (
        query
        .order_by(PurchaseOrder.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return purchase_orders


# GET PURCHASE ORDER BY ID
@router.get(
    "/{purchase_order_id}",
    response_model=PurchaseOrderResponse
)
def get_purchase_order(
    purchase_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    purchase_order = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.id == purchase_order_id
        )
        .first()
    )

    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail="Purchase order not found"
        )

    return purchase_order


# APPROVE PURCHASE ORDER
@router.post(
    "/{purchase_order_id}/approve",
    response_model=PurchaseOrderResponse
)
def approve_purchase_order(
    purchase_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):

    purchase_order = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.id == purchase_order_id
        )
        .first()
    )

    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail="Purchase order not found"
        )

    # Only Draft orders can be approved
    if purchase_order.status != PurchaseOrderStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Only Draft purchase orders can be approved"
        )

    purchase_order.status = PurchaseOrderStatus.APPROVED.value

    db.commit()
    db.refresh(purchase_order)

    return purchase_order


# RECEIVE PURCHASE ORDER
@router.post(
    "/{purchase_order_id}/receive",
    response_model=PurchaseOrderResponse
)
def receive_purchase_order(
    purchase_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER,
            UserRole.WAREHOUSE_STAFF
        )
    )
):

    # GET PURCHASE ORDER
    purchase_order = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.id == purchase_order_id
        )
        .first()
    )

    if not purchase_order:
        raise HTTPException(
            status_code=404,
            detail="Purchase order not found"
        )

    # CHECK STATUS
    if purchase_order.status not in [
        PurchaseOrderStatus.APPROVED.value,
        PurchaseOrderStatus.PARTIALLY_RECEIVED.value
    ]:
        raise HTTPException(
            status_code=400,
            detail="Purchase order must be Approved before receiving"
        )

    # GET ITEMS
    items = (
        db.query(PurchaseOrderItem)
        .filter(
            PurchaseOrderItem.purchase_order_id
            == purchase_order.id
        )
        .all()
    )

    if not items:
        raise HTTPException(
            status_code=400,
            detail="Purchase order has no items"
        )

    # PROCESS EACH ITEM
    for item in items:

        product = (
            db.query(Product)
            .filter(
                Product.id == item.product_id,
                Product.is_active == True
            )
            .first()
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Remaining quantity to receive
        remaining_quantity = (
            item.quantity_ordered
            - item.quantity_received
        )

        if remaining_quantity <= 0:
            continue

        # FIND INVENTORY
        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == item.product_id,
                Inventory.warehouse_id
                == purchase_order.warehouse_id
            )
            .first()
        )

        # CREATE INVENTORY IF NOT EXISTS
        if not inventory:

            inventory = Inventory(
                product_id=item.product_id,
                warehouse_id=purchase_order.warehouse_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                average_cost=Decimal("0.00")
            )

            db.add(inventory)
            db.flush()

        # OLD VALUES
        old_quantity = Decimal(
            str(inventory.quantity_on_hand)
        )

        old_average_cost = Decimal(
            str(inventory.average_cost)
        )

        received_quantity = Decimal(
            str(remaining_quantity)
        )

        purchase_cost = Decimal(
            str(item.unit_cost)
        )

        # WEIGHTED AVERAGE COST
        old_stock_value = (
            old_quantity * old_average_cost
        )

        new_stock_value = (
            received_quantity * purchase_cost
        )

        total_quantity = (
            old_quantity + received_quantity
        )

        if total_quantity > 0:
            new_average_cost = (
                old_stock_value + new_stock_value
            ) / total_quantity
        else:
            new_average_cost = purchase_cost

        # UPDATE INVENTORY
        inventory.quantity_on_hand = int(
            total_quantity
        )

        inventory.average_cost = new_average_cost

        # UPDATE PO ITEM
        item.quantity_received = (
            item.quantity_ordered
        )

        # CREATE STOCK MOVEMENT
        movement = StockMovement(
            product_id=item.product_id,
            warehouse_id=purchase_order.warehouse_id,
            movement_type=StockMovementType.PURCHASE_RECEIPT.value,
            quantity=int(received_quantity),
            reference_id=purchase_order.id,
            balance_after=inventory.quantity_on_hand,
            performed_by=current_user.id
        )

        db.add(movement)

    # UPDATE PO STATUS
    purchase_order.status = (
        PurchaseOrderStatus.RECEIVED.value
    )

    db.commit()
    db.refresh(purchase_order)

    return purchase_order


# LOW STOCK
@router.post(
    "/auto-create-low-stock/{product_id}",
    status_code=status.HTTP_201_CREATED
)
def auto_create_low_stock_purchase_order(
    product_id: int,
    supplier_id: int,
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    # Check product
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if not product.is_active:
        raise HTTPException(
            status_code=400,
            detail="Product is inactive"
        )

    # Check supplier
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.is_active == True
        )
        .first()
    )

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Active supplier not found"
        )

    # Check warehouse
    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.id == warehouse_id,
            Warehouse.is_active == True
        )
        .first()
    )

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Active warehouse not found"
        )

    # Get current inventory
    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id
        )
        .first()
    )

    current_quantity = 0

    if inventory:
        current_quantity = inventory.quantity_on_hand

    # Check whether stock is actually low
    if current_quantity > product.reorder_level:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Stock is not low. "
                f"Current stock: {current_quantity}, "
                f"Reorder level: {product.reorder_level}"
            )
        )

    # Check whether an active draft PO already exists
    existing_po = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.warehouse_id == warehouse_id,
            PurchaseOrder.status == PurchaseOrderStatus.DRAFT
        )
        .first()
    )

    if existing_po:
      raise HTTPException(
        status_code=400,
        detail=(
            f"A draft purchase order already exists "
            f"for this supplier and warehouse. "
            f"PO: {existing_po.po_number}"
        )
    )

    # Generate PO number
    last_po = (
        db.query(PurchaseOrder)
        .order_by(PurchaseOrder.id.desc())
        .first()
    )

    if last_po:
        po_number = f"PO-{last_po.id + 1:04d}"
    else:
        po_number = "PO-0001"

    # Create new draft PO
    purchase_order = PurchaseOrder(
        po_number=po_number,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        status=PurchaseOrderStatus.DRAFT,
        total_amount=0,
        created_by=current_user.id
    )

    db.add(purchase_order)
    db.flush()

    # Determine reorder quantity
    reorder_quantity = product.reorder_quantity

    if reorder_quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Product reorder quantity must be greater than zero"
        )

    # Calculate subtotal
    unit_cost = product.cost_price
    subtotal = unit_cost * reorder_quantity

    # Create PO item
    po_item = PurchaseOrderItem(
        purchase_order_id=purchase_order.id,
        product_id=product.id,
        quantity_ordered=reorder_quantity,
        quantity_received=0,
        unit_cost=unit_cost,
        subtotal=subtotal
    )

    db.add(po_item)

    # Update total amount
    purchase_order.total_amount = subtotal

    db.commit()
    db.refresh(purchase_order)

    return {
        "message": "Low stock detected. Draft purchase order created.",
        "purchase_order_id": purchase_order.id,
        "po_number": purchase_order.po_number,
        "product_id": product.id,
        "product_name": product.product_name,
        "current_stock": current_quantity,
        "reorder_level": product.reorder_level,
        "reorder_quantity": reorder_quantity,
        "supplier_id": supplier_id,
        "warehouse_id": warehouse_id,
        "status": purchase_order.status
    }