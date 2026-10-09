from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.models import (
    Return,
    ReturnItem,
    SalesOrder,
    SalesOrderItem,
    Inventory,
    StockMovement,
    User,
    UserRole,
    ReturnStatus,
    ReturnCondition,
    StockMovementType,
)
from app.schemas.schemas import (
    ReturnCreate,
    ReturnResponse,
)


router = APIRouter(
    prefix="/returns",
    tags=["Returns"]
)


@router.post(
    "",
    response_model=ReturnResponse,
    status_code=status.HTTP_201_CREATED
)
def create_return(
    return_data: ReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find sales order
    sales_order = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.id == return_data.sales_order_id
        )
        .first()
    )

    if sales_order is None:
        raise HTTPException(
            status_code=404,
            detail="Sales order not found"
        )

    # Order must have been dispatched
    if sales_order.status != "Dispatched":
        raise HTTPException(
            status_code=400,
            detail="Only dispatched orders can be returned"
        )

    # Check whether this return already exists
    existing_return = (
        db.query(Return)
        .filter(
            Return.sales_order_id == sales_order.id
        )
        .first()
    )

    if existing_return:
        raise HTTPException(
            status_code=400,
            detail="A return already exists for this sales order"
        )

    # Create return
    customer_id = sales_order.customer_id

    return_record = Return(
        sales_order_id=sales_order.id,
        customer_id=customer_id,
        status=ReturnStatus.REQUESTED,
        reason=return_data.reason,
        refund_amount=Decimal("0")
    )

    db.add(return_record)
    db.flush()

    refund_amount = Decimal("0")

    # Process each returned item
    for item_data in return_data.items:

        order_item = (
            db.query(SalesOrderItem)
            .filter(
                SalesOrderItem.sales_order_id == sales_order.id,
                SalesOrderItem.product_id == item_data.product_id
            )
            .first()
        )

        if order_item is None:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Product {item_data.product_id} "
                    "was not part of this order"
                )
            )

        # Check returned quantity
        if item_data.quantity > order_item.quantity:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Return quantity cannot exceed "
                    f"ordered quantity for product "
                    f"{item_data.product_id}"
                )
            )

        # Create return item
        return_item = ReturnItem(
            return_id=return_record.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            condition=item_data.condition
        )

        db.add(return_item)

        # Calculate refund
        item_refund = (
            order_item.unit_price
            * item_data.quantity
        )

        refund_amount += item_refund

        # Restore good-condition stock
        if item_data.condition == ReturnCondition.GOOD:

            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.product_id == item_data.product_id,
                    Inventory.warehouse_id == sales_order.warehouse_id
                )
                .first()
            )

            if inventory is None:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Inventory not found for "
                        f"product {item_data.product_id}"
                    )
                )

            inventory.quantity_on_hand += item_data.quantity

            # Create return stock movement
            movement = StockMovement(
                product_id=item_data.product_id,
                warehouse_id=sales_order.warehouse_id,
                movement_type=StockMovementType.CUSTOMER_RETURN,
                quantity=item_data.quantity,
                reference_id=return_record.id,
                balance_after=inventory.quantity_on_hand,
                performed_by=current_user.id
            )

            db.add(movement)

    # Save refund amount
    return_record.refund_amount = refund_amount

    db.commit()
    db.refresh(return_record)

    return return_record


@router.get(
    "",
    response_model=list[ReturnResponse]
)
def get_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(Return)
        .order_by(Return.id.desc())
        .all()
    )


@router.get(
    "/{return_id}",
    response_model=ReturnResponse
)
def get_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return_record = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if return_record is None:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    return return_record


@router.post(
    "/{return_id}/inspect",
    response_model=ReturnResponse
)
def inspect_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return_record = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if return_record is None:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != ReturnStatus.REQUESTED:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only Requested returns can be inspected. "
                f"Current status: {return_record.status}"
            )
        )

    return_record.status = ReturnStatus.INSPECTED

    db.commit()
    db.refresh(return_record)

    return return_record


@router.post(
    "/{return_id}/approve",
    response_model=ReturnResponse
)
def approve_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    return_record = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if return_record is None:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != ReturnStatus.INSPECTED:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only Inspected returns can be approved. "
                f"Current status: {return_record.status}"
            )
        )

    return_record.status = ReturnStatus.APPROVED

    db.commit()
    db.refresh(return_record)

    return return_record


@router.post(
    "/{return_id}/reject",
    response_model=ReturnResponse
)
def reject_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    return_record = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if return_record is None:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != ReturnStatus.INSPECTED:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only Inspected returns can be rejected. "
                f"Current status: {return_record.status}"
            )
        )

    return_record.status = ReturnStatus.REJECTED

    db.commit()
    db.refresh(return_record)

    return return_record


@router.post(
    "/{return_id}/refund",
    response_model=ReturnResponse
)
def process_refund(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    return_record = (
        db.query(Return)
        .filter(Return.id == return_id)
        .first()
    )

    if return_record is None:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != ReturnStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only Approved returns can be refunded. "
                f"Current status: {return_record.status}"
            )
        )

    if return_record.refund_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Refund amount must be greater than zero"
        )

    return_record.status = ReturnStatus.REFUNDED

    db.commit()
    db.refresh(return_record)

    return return_record