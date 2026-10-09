from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import ProductBatch


def deduct_stock_using_fefo(
    db: Session,
    product_id: int,
    warehouse_id: int,
    quantity: int
):
    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero"
        )

    # Get available, non-expired batches.
    # Earliest expiry comes first.
    batches = (
        db.query(ProductBatch)
        .filter(
            ProductBatch.product_id == product_id,
            ProductBatch.warehouse_id == warehouse_id,
            ProductBatch.quantity > 0,
            ProductBatch.expiry_date >= date.today()
        )
        .order_by(ProductBatch.expiry_date.asc())
        .all()
    )

    total_available = sum(
        batch.quantity for batch in batches
    )

    if total_available < quantity:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient batch stock. "
                f"Available batch quantity: {total_available}"
            )
        )

    remaining = quantity
    deductions = []

    for batch in batches:
        if remaining == 0:
            break

        quantity_from_batch = min(
            batch.quantity,
            remaining
        )

        batch.quantity -= quantity_from_batch
        remaining -= quantity_from_batch

        deductions.append({
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
            "expiry_date": batch.expiry_date,
            "quantity": quantity_from_batch
        })

    return deductions