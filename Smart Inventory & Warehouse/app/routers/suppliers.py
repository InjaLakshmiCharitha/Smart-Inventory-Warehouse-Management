from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Supplier, User, UserRole
from app.schemas.schemas import (
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.auth.dependencies import (
    get_current_user,
    require_roles,
)


router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"]
)


# CREATE SUPPLIER
@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED
)
def create_supplier(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    # Check duplicate email
    existing_supplier = (
        db.query(Supplier)
        .filter(Supplier.email == supplier_data.email)
        .first()
    )

    if existing_supplier:
        raise HTTPException(
            status_code=400,
            detail="Supplier with this email already exists"
        )

    supplier = Supplier(
        supplier_code=supplier_data.supplier_code,
        name=supplier_data.name,
        email=supplier_data.email,
        phone=supplier_data.phone,
        gst_number=supplier_data.gst_number,
        address=supplier_data.address,
        lead_time_days=supplier_data.lead_time_days,
        is_active=supplier_data.is_active
    )

    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    return supplier


# GET ALL SUPPLIERS
@router.get(
    "",
    response_model=list[SupplierResponse]
)
def get_suppliers(
    search: Optional[str] = Query(
        default=None
    ),
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
    query = (
        db.query(Supplier)
        .filter(Supplier.is_active == True)
    )

    # Search by supplier name
    if search:
        query = query.filter(
            Supplier.supplier_name.ilike(
                f"%{search}%"
            )
        )

    # Pagination
    offset = (page - 1) * page_size

    suppliers = (
        query
        .order_by(Supplier.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return suppliers


# GET SUPPLIER BY ID
@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse
)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.is_active == True
        )
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    return supplier


# UPDATE SUPPLIER
@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse
)
def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.is_active == True
        )
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    # Check email duplication
    if supplier_data.email:
        existing_supplier = (
            db.query(Supplier)
            .filter(
                Supplier.email == supplier_data.email,
                Supplier.id != supplier_id
            )
            .first()
        )

        if existing_supplier:
            raise HTTPException(
                status_code=400,
                detail="Another supplier already uses this email"
            )

    update_data = supplier_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)

    return supplier


# DELETE SUPPLIER 
@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_200_OK
)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    )
):
    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id)
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    supplier.is_active = False

    db.commit()

    return {
        "message": "Supplier deleted successfully"
    }