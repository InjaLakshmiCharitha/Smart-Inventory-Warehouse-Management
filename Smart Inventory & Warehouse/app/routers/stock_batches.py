from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, check_warehouse_access
from app.database import get_db
from app.models.models import Product, ProductBatch, Warehouse, User
from app.schemas.schemas import ProductBatchCreate, ProductBatchResponse


router = APIRouter(
    prefix="/batches",
    tags=["Product Batches"]
)


@router.post(
    "",
    response_model=ProductBatchResponse,
    status_code=status.HTTP_201_CREATED
)
def create_batch(
    batch_data: ProductBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check warehouse access
    check_warehouse_access(
        current_user,
        batch_data.warehouse_id
    )

    # Check warehouse
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == batch_data.warehouse_id,
        Warehouse.is_active == True
    ).first()

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found or inactive"
        )

    # Check product
    product = db.query(Product).filter(
        Product.id == batch_data.product_id,
        Product.is_active == True
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found or inactive"
        )

    # Check expiry date
    if batch_data.expiry_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Expiry date cannot be in the past"
        )

    # Check duplicate batch
    existing_batch = db.query(ProductBatch).filter(
        ProductBatch.product_id == batch_data.product_id,
        ProductBatch.warehouse_id == batch_data.warehouse_id,
        ProductBatch.batch_number == batch_data.batch_number
    ).first()

    if existing_batch:
        raise HTTPException(
            status_code=400,
            detail="Batch already exists for this product and warehouse"
        )

    # Create batch
    batch = ProductBatch(
        product_id=batch_data.product_id,
        warehouse_id=batch_data.warehouse_id,
        batch_number=batch_data.batch_number,
        expiry_date=batch_data.expiry_date,
        quantity=batch_data.quantity,
        unit_cost=batch_data.unit_cost
    )

    db.add(batch)
    db.commit()
    db.refresh(batch)

    return batch


@router.get(
    "",
    response_model=list[ProductBatchResponse]
)
def get_batches(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    include_expired: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ProductBatch)

    if product_id is not None:
        query = query.filter(
            ProductBatch.product_id == product_id
        )

    if warehouse_id is not None:
        check_warehouse_access(
            current_user,
            warehouse_id
        )

        query = query.filter(
            ProductBatch.warehouse_id == warehouse_id
        )

    if not include_expired:
        query = query.filter(
            ProductBatch.expiry_date >= date.today()
        )

    return query.order_by(
        ProductBatch.expiry_date.asc()
    ).all()


@router.get(
    "/{batch_id}",
    response_model=ProductBatchResponse
)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    batch = db.query(ProductBatch).filter(
        ProductBatch.id == batch_id
    ).first()

    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Batch not found"
        )

    check_warehouse_access(
        current_user,
        batch.warehouse_id
    )

    return batch