from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, check_warehouse_access
from app.models.models import (
    User,
    UserRole,
    Product,
    Warehouse,
    Inventory,
    StockMovement,
    StockMovementType,
    StockAdjustment,
    AdjustmentStatus,
)
from app.schemas.schemas import (
    StockAdjustmentCreate,
    StockAdjustmentResponse,
)

router = APIRouter(
    prefix="/stock-adjustments",
    tags=["Stock Adjustments"]
)


# ---------------------------------------------------------
# CREATE STOCK ADJUSTMENT
# ---------------------------------------------------------

@router.post(
    "",
    response_model=StockAdjustmentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_stock_adjustment(
    adjustment_data: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check warehouse
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == adjustment_data.warehouse_id,
        Warehouse.is_active == True
    ).first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    # Check warehouse access
    check_warehouse_access(
        current_user,
        adjustment_data.warehouse_id
    )

    # Check product
    product = db.query(Product).filter(
        Product.id == adjustment_data.product_id,
        Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # Check inventory
    inventory = db.query(Inventory).filter(
        Inventory.product_id == adjustment_data.product_id,
        Inventory.warehouse_id == adjustment_data.warehouse_id
    ).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    # Negative adjustment cannot make stock negative
    if adjustment_data.quantity < 0:
        available_stock = (
            inventory.quantity_on_hand -
            inventory.quantity_reserved
        )

        if abs(adjustment_data.quantity) > available_stock:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Adjustment exceeds available stock. "
                    f"Available: {available_stock}"
                )
            )

    adjustment = StockAdjustment(
        product_id=adjustment_data.product_id,
        warehouse_id=adjustment_data.warehouse_id,
        quantity=adjustment_data.quantity,
        reason=adjustment_data.reason.value,
        status=AdjustmentStatus.PENDING.value,
        notes=adjustment_data.notes,
        created_by=current_user.id
    )

    db.add(adjustment)
    db.commit()
    db.refresh(adjustment)

    return adjustment


# ---------------------------------------------------------
# GET ALL ADJUSTMENTS
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[StockAdjustmentResponse]
)
def get_stock_adjustments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(StockAdjustment).order_by(
        StockAdjustment.created_at.desc()
    ).all()


# ---------------------------------------------------------
# GET ADJUSTMENT BY ID
# ---------------------------------------------------------

@router.get(
    "/{adjustment_id}",
    response_model=StockAdjustmentResponse
)
def get_stock_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    adjustment = db.query(StockAdjustment).filter(
        StockAdjustment.id == adjustment_id
    ).first()

    if not adjustment:
        raise HTTPException(
            status_code=404,
            detail="Stock adjustment not found"
        )

    return adjustment


# ---------------------------------------------------------
# APPROVE ADJUSTMENT
# ---------------------------------------------------------

@router.post(
    "/{adjustment_id}/approve",
    response_model=StockAdjustmentResponse
)
def approve_stock_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only Admin / Inventory Manager
    role = current_user.role

    if isinstance(role, UserRole):
        role = role.value

    if role not in [
        UserRole.ADMIN.value,
        UserRole.INVENTORY_MANAGER.value
    ]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Inventory Manager can approve adjustments"
        )

    adjustment = db.query(StockAdjustment).filter(
        StockAdjustment.id == adjustment_id
    ).first()

    if not adjustment:
        raise HTTPException(
            status_code=404,
            detail="Stock adjustment not found"
        )

    if adjustment.status != AdjustmentStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Adjustment cannot be approved because its status "
                f"is {adjustment.status}"
            )
        )

    # Check warehouse access
    check_warehouse_access(
        current_user,
        adjustment.warehouse_id
    )

    inventory = db.query(Inventory).filter(
        Inventory.product_id == adjustment.product_id,
        Inventory.warehouse_id == adjustment.warehouse_id
    ).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Inventory record not found"
        )

    # Check negative adjustment again
    if adjustment.quantity < 0:
        available_stock = (
            inventory.quantity_on_hand -
            inventory.quantity_reserved
        )

        if abs(adjustment.quantity) > available_stock:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Adjustment exceeds available stock. "
                    f"Available: {available_stock}"
                )
            )

    # Apply adjustment
    inventory.quantity_on_hand += adjustment.quantity

    # Create stock movement
    movement = StockMovement(
        product_id=adjustment.product_id,
        warehouse_id=adjustment.warehouse_id,
        movement_type=StockMovementType.ADJUSTMENT.value,
        quantity=adjustment.quantity,
        reference_id=adjustment.id,
        balance_after=inventory.quantity_on_hand,
        performed_by=current_user.id
    )

    db.add(movement)

    adjustment.status = AdjustmentStatus.APPROVED.value
    adjustment.approved_by = current_user.id

    db.commit()
    db.refresh(adjustment)

    return adjustment


# ---------------------------------------------------------
# REJECT ADJUSTMENT
# ---------------------------------------------------------

@router.post(
    "/{adjustment_id}/reject",
    response_model=StockAdjustmentResponse
)
def reject_stock_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role

    if isinstance(role, UserRole):
        role = role.value

    if role not in [
        UserRole.ADMIN.value,
        UserRole.INVENTORY_MANAGER.value
    ]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Inventory Manager can reject adjustments"
        )

    adjustment = db.query(StockAdjustment).filter(
        StockAdjustment.id == adjustment_id
    ).first()

    if not adjustment:
        raise HTTPException(
            status_code=404,
            detail="Stock adjustment not found"
        )

    if adjustment.status != AdjustmentStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Adjustment cannot be rejected because its status "
                f"is {adjustment.status}"
            )
        )

    adjustment.status = AdjustmentStatus.REJECTED.value
    adjustment.approved_by = current_user.id

    db.commit()
    db.refresh(adjustment)

    return adjustment