from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import (
    get_current_user,
    check_warehouse_access,
)
from app.models.models import (
    User,
    UserRole,
    Warehouse,
    Product,
    Inventory,
    StockMovement,
    StockMovementType,
    StockTransfer,
    StockTransferItem,
    TransferStatus,
)
from app.schemas.schemas import (
    StockTransferCreate,
    StockTransferResponse,
)

router = APIRouter(
    prefix="/stock-transfers",
    tags=["Stock Transfers"]
)


# CREATE STOCK TRANSFER
@router.post(
    "",
    response_model=StockTransferResponse,
    status_code=status.HTTP_201_CREATED
)
def create_stock_transfer(
    transfer_data: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check source warehouse
    source_warehouse = db.query(Warehouse).filter(
        Warehouse.id == transfer_data.from_warehouse_id,
        Warehouse.is_active == True
    ).first()

    if not source_warehouse:
        raise HTTPException(
            status_code=404,
            detail="Source warehouse not found"
        )

    # Check destination warehouse
    destination_warehouse = db.query(Warehouse).filter(
        Warehouse.id == transfer_data.to_warehouse_id,
        Warehouse.is_active == True
    ).first()

    if not destination_warehouse:
        raise HTTPException(
            status_code=404,
            detail="Destination warehouse not found"
        )

    # Check warehouse permission
    check_warehouse_access(
        current_user,
        transfer_data.from_warehouse_id
    )

    # Check every product
    for item in transfer_data.items:

        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Check source inventory
        inventory = db.query(Inventory).filter(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == transfer_data.from_warehouse_id
        ).first()

        if not inventory:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No inventory found for product "
                    f"{item.product_id} in source warehouse"
                )
            )

        available_stock = (
            inventory.quantity_on_hand -
            inventory.quantity_reserved
        )

        if available_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient available stock for product "
                    f"{item.product_id}. "
                    f"Available: {available_stock}, "
                    f"Requested: {item.quantity}"
                )
            )

    # Create transfer
    transfer = StockTransfer(
        transfer_number="TEMP",
        from_warehouse_id=transfer_data.from_warehouse_id,
        to_warehouse_id=transfer_data.to_warehouse_id,
        status=TransferStatus.PENDING.value,
        created_by=current_user.id
    )

    db.add(transfer)
    db.flush()

    # Generate transfer number
    transfer.transfer_number = f"TRF-{transfer.id:06d}"

    # Add transfer items
    for item in transfer_data.items:

        transfer_item = StockTransferItem(
            transfer_id=transfer.id,
            product_id=item.product_id,
            quantity=item.quantity
        )

        db.add(transfer_item)

    db.commit()
    db.refresh(transfer)

    return transfer


# GET ALL STOCK TRANSFERS
@router.get(
    "",
    response_model=list[StockTransferResponse]
)
def get_stock_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transfers = db.query(StockTransfer).order_by(
        StockTransfer.created_at.desc()
    ).all()

    return transfers


# GET STOCK TRANSFER BY ID
@router.get(
    "/{transfer_id}",
    response_model=StockTransferResponse
)
def get_stock_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()

    if not transfer:
        raise HTTPException(
            status_code=404,
            detail="Stock transfer not found"
        )

    return transfer


# SEND STOCK TRANSFER
@router.post(
    "/{transfer_id}/send",
    response_model=StockTransferResponse
)
def send_stock_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()

    if not transfer:
        raise HTTPException(
            status_code=404,
            detail="Stock transfer not found"
        )

    # Only Pending transfers can be sent
    if transfer.status != TransferStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transfer cannot be sent because its status is "
                f"{transfer.status}"
            )
        )

    # Check source warehouse permission
    check_warehouse_access(
        current_user,
        transfer.from_warehouse_id
    )

    # Process each item
    for item in transfer.items:

        inventory = db.query(Inventory).filter(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == transfer.from_warehouse_id
        ).first()

        if not inventory:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Inventory not found for product "
                    f"{item.product_id}"
                )
            )

        available_stock = (
            inventory.quantity_on_hand -
            inventory.quantity_reserved
        )

        if available_stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient stock for product "
                    f"{item.product_id}. "
                    f"Available: {available_stock}, "
                    f"Requested: {item.quantity}"
                )
            )

        # Reduce source stock
        inventory.quantity_on_hand -= item.quantity

        # Create stock movement
        movement = StockMovement(
            product_id=item.product_id,
            warehouse_id=transfer.from_warehouse_id,
            movement_type=StockMovementType.TRANSFER_OUT.value,
            quantity=item.quantity,
            reference_id=transfer.id,
            balance_after=inventory.quantity_on_hand,
            performed_by=current_user.id
        )

        db.add(movement)

    # Change status
    transfer.status = TransferStatus.IN_TRANSIT.value

    db.commit()
    db.refresh(transfer)

    return transfer


# RECEIVE STOCK TRANSFER
@router.post(
    "/{transfer_id}/receive",
    response_model=StockTransferResponse
)
def receive_stock_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id
    ).first()

    if not transfer:
        raise HTTPException(
            status_code=404,
            detail="Stock transfer not found"
        )

    # Only In Transit transfers can be received
    if transfer.status != TransferStatus.IN_TRANSIT.value:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Transfer cannot be received because its status is "
                f"{transfer.status}"
            )
        )

    # Check destination warehouse permission
    check_warehouse_access(
        current_user,
        transfer.to_warehouse_id
    )

    # Process each item
    for item in transfer.items:

        inventory = db.query(Inventory).filter(
            Inventory.product_id == item.product_id,
            Inventory.warehouse_id == transfer.to_warehouse_id
        ).first()

        # If destination inventory doesn't exist,
        # create it.
        if not inventory:

            product = db.query(Product).filter(
                Product.id == item.product_id
            ).first()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item.product_id} not found"
                )

            inventory = Inventory(
                product_id=item.product_id,
                warehouse_id=transfer.to_warehouse_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                average_cost=product.cost_price
            )

            db.add(inventory)
            db.flush()

        # Increase destination stock
        inventory.quantity_on_hand += item.quantity

        # Create stock movement
        movement = StockMovement(
            product_id=item.product_id,
            warehouse_id=transfer.to_warehouse_id,
            movement_type=StockMovementType.TRANSFER_IN.value,
            quantity=item.quantity,
            reference_id=transfer.id,
            balance_after=inventory.quantity_on_hand,
            performed_by=current_user.id
        )

        db.add(movement)

    # Change status
    transfer.status = TransferStatus.RECEIVED.value

    db.commit()
    db.refresh(transfer)

    return transfer