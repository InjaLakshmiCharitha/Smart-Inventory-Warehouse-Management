from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.models import (
    Product,
    Warehouse,
    Inventory,
    StockMovement,
    StockMovementType,
    User,
    UserRole
)

from app.schemas.schemas import InventoryResponse

from app.auth.dependencies import (
    get_current_user,
    check_warehouse_access
)


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


# GET INVENTORY FOR A WAREHOUSE
@router.get(
    "/warehouse/{warehouse_id}",
    response_model=list[InventoryResponse]
)
def get_warehouse_inventory(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check warehouse access
    check_warehouse_access(
        current_user,
        warehouse_id
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.warehouse_id == warehouse_id
        )
        .order_by(Inventory.id)
        .all()
    )

    return inventory


# GET PRODUCT INVENTORY
@router.get(
    "/product/{product_id}",
    response_model=list[InventoryResponse]
)
def get_product_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Check product
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active == True
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id
        )
        .all()
    )

    # Warehouse access
    allowed_inventory = []

    for item in inventory:

        try:
            check_warehouse_access(
                current_user,
                item.warehouse_id
            )

            allowed_inventory.append(item)

        except HTTPException:
            continue

    return allowed_inventory


# GET SINGLE INVENTORY RECORD
@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse
)
def get_inventory(
    inventory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.id == inventory_id
        )
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found"
        )

    check_warehouse_access(
        current_user,
        inventory.warehouse_id
    )

    return inventory


# STOCK IN
@router.post(
    "/stock-in"
)
def stock_in(
    product_id: int,
    warehouse_id: int,
    quantity: int,
    unit_cost: float = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Quantity validation
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero"
        )

    # Validate unit cost
    if unit_cost < 0:
      raise HTTPException(
         status_code=status.HTTP_400_BAD_REQUEST,
         detail="Unit cost cannot be negative"
    )

    # Warehouse access
    check_warehouse_access(
        current_user,
        warehouse_id
    )

    # Product
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active == True
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Warehouse
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    # Find inventory
    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id
        )
        .first()
    )

    # Create inventory if it doesn't exist
    if inventory is None:

        inventory = Inventory(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_on_hand=0,
            quantity_reserved=0,
            average_cost=0
        )

        db.add(inventory)
        db.flush()

    # Weighted average cost
    old_quantity = inventory.quantity_on_hand
    old_average_cost = float(
        inventory.average_cost or 0
    )

    total_old_value = (
        old_quantity * old_average_cost
    )

    total_new_value = (
        quantity * unit_cost
    )

    new_quantity = old_quantity + quantity

    if new_quantity > 0:

        inventory.average_cost = (
            total_old_value + total_new_value
        ) / new_quantity

    inventory.quantity_on_hand = new_quantity

    # Stock movement
    movement = StockMovement(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=StockMovementType.PURCHASE_RECEIPT.value,
        quantity=quantity,
        balance_after=inventory.quantity_on_hand,
        performed_by=current_user.id
    )

    db.add(movement)

    db.commit()
    db.refresh(inventory)

    return {
        "message": "Stock added successfully",
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "quantity_added": quantity,
        "quantity_on_hand": inventory.quantity_on_hand,
        "quantity_reserved": inventory.quantity_reserved,
        "quantity_available": inventory.quantity_available,
        "average_cost": float(
            inventory.average_cost or 0
        )
    }


# STOCK OUT
@router.post(
    "/stock-out"
)
def stock_out(
    product_id: int,
    warehouse_id: int,
    quantity: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Quantity validation
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero"
        )    

    # warehouse access 
    check_warehouse_access(
        current_user,
        warehouse_id
    )

    # product 
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_active == True
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
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
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Warehouse not found"
    )
    # Inventory
    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == product_id,
            Inventory.warehouse_id == warehouse_id
        )
        .first()
    )

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No inventory found for this product in this warehouse"
        )

        # Check available stock
    available_quantity = (
        inventory.quantity_on_hand
        - inventory.quantity_reserved
    )

    if quantity > available_quantity:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock. "
                f"Available quantity: {available_quantity}"
            )
        )

    # Reduce stock
    inventory.quantity_on_hand -= quantity

    # Stock movement
    movement = StockMovement(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=StockMovementType.SALE_DISPATCH.value,
        quantity=quantity,
        balance_after=inventory.quantity_on_hand,
        performed_by=current_user.id
    )

    db.add(movement)

    db.commit()
    db.refresh(inventory)

    return {
        "message": "Stock removed successfully",
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "quantity_removed": quantity,
        "quantity_on_hand": inventory.quantity_on_hand,
        "quantity_reserved": inventory.quantity_reserved,
        "quantity_available": inventory.quantity_available
    }


# STOCK MOVEMENT HISTORY
@router.get(
    "/movements/{product_id}"
)
def get_stock_movements(
    product_id: int,
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Warehouse access
    check_warehouse_access(
        current_user,
        warehouse_id
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
         status_code=status.HTTP_404_NOT_FOUND,
         detail="Warehouse not found"
       )


    # Product check
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.product_id == product_id,
            StockMovement.warehouse_id == warehouse_id
        )
        .order_by(
            StockMovement.created_at.desc()
        )
        .all()
    )

    return movements   