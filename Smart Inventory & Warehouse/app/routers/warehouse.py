from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.models import (
    Warehouse,
    User,
    UserRole
)

from app.schemas.schemas import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse
)

from app.auth.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"]
)


# CREATE WAREHOUSE
@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED
)
def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):

    # Check duplicate warehouse name
    existing_warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.warehouse_code
            == warehouse_data.warehouse_code
        )
        .first()
    )

    if existing_warehouse:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse name already exists"
        )

    # Validate capacity
    if warehouse_data.capacity is not None:

        if warehouse_data.capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse capacity must be greater than zero"
            )

    # Create warehouse
    warehouse = Warehouse(
      warehouse_code=warehouse_data.warehouse_code,
      name=warehouse_data.name,
      city=warehouse_data.city,
      address=warehouse_data.address,
      manager_id=warehouse_data.manager_id,
      capacity=warehouse_data.capacity,
      is_active=warehouse_data.is_active
   )

    # Validate manager if provided
    if warehouse_data.manager_id is not None:

        manager = (
            db.query(User)
            .filter(
                User.id == warehouse_data.manager_id,
                User.is_active == True
            )
            .first()
        )

        if manager is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager user not found or inactive"
            )

    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)

    return warehouse


# GET ALL WAREHOUSES
@router.get(
    "",
    response_model=list[WarehouseResponse]
)
def get_warehouses(
    search: Optional[str] = Query(
        default=None,
        description="Search warehouse by name or location"
    ),
    page: int = Query(
        default=1,
        ge=1
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    query = (
        db.query(Warehouse)
        .filter(Warehouse.is_active == True)
    )

    # Search
    if search:

        search_value = f"%{search}%"

        query = query.filter(
            (Warehouse.warehouse_name.ilike(search_value))
            |
            (Warehouse.location.ilike(search_value))
        )

    # Pagination
    offset = (page - 1) * limit

    warehouses = (
        query
        .order_by(Warehouse.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return warehouses


# GET WAREHOUSE BY ID
@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse
)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

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

    return warehouse


# UPDATE WAREHOUSE
@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse
)
def update_warehouse(
    warehouse_id: int,
    warehouse_data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):

    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.id == warehouse_id
        )
        .first()
    )

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update an inactive warehouse"
        )

    # Warehouse name
    if warehouse_data.name is not None:

        existing_warehouse = (
            db.query(Warehouse)
            .filter(
                Warehouse.name
                == warehouse_data.name,
                Warehouse.id != warehouse_id
            )
            .first()
        )

        if existing_warehouse:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse name already exists"
            )

        warehouse.warehouse_name = (
            warehouse_data.warehouse_name
        )

    # Location
    if warehouse_data.location is not None:
        warehouse.location = warehouse_data.location

    # Manager
    if warehouse_data.manager_id is not None:

        manager = (
            db.query(User)
            .filter(
                User.id == warehouse_data.manager_id,
                User.is_active == True
            )
            .first()
        )

        if manager is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager user not found or inactive"
            )

        warehouse.manager_id = warehouse_data.manager_id

    # Capacity
    if warehouse_data.capacity is not None:

        if warehouse_data.capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse capacity must be greater than zero"
            )

        warehouse.capacity = warehouse_data.capacity

    # Active status
    if warehouse_data.is_active is not None:
        warehouse.is_active = warehouse_data.is_active

    db.commit()
    db.refresh(warehouse)

    return warehouse


# DELETE WAREHOUSE
@router.delete(
    "/{warehouse_id}"
)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    )
):

    warehouse = (
        db.query(Warehouse)
        .filter(
            Warehouse.id == warehouse_id
        )
        .first()
    )

    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found"
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse is already inactive"
        )

    warehouse.is_active = False

    db.commit()

    return {
        "message": "Warehouse deleted successfully"
    }