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
    Product,
    Category,
    User,
    UserRole
)
from app.schemas.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse
)
from app.auth.dependencies import (
    get_current_user,
    require_roles
)


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


# CREATE PRODUCT
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):

    # Check category
    category = (
        db.query(Category)
        .filter(
            Category.id == product_data.category_id,
            Category.is_active == True
        )
        .first()
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or inactive"
        )

    # Check duplicate SKU
    existing_sku = (
        db.query(Product)
        .filter(Product.sku == product_data.sku)
        .first()
    )

    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU already exists"
        )

    # Check duplicate barcode
    if product_data.barcode:

        existing_barcode = (
            db.query(Product)
            .filter(
                Product.barcode == product_data.barcode
            )
            .first()
        )

        if existing_barcode:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Barcode already exists"
            )

    # Create product
    product = Product(
        sku=product_data.sku,
        name=product_data.name,
        category_id=product_data.category_id,
        unit=product_data.unit.value,
        cost_price=product_data.cost_price,
        selling_price=product_data.selling_price,
        reorder_level=product_data.reorder_level,
        reorder_quantity=product_data.reorder_quantity,
        barcode=product_data.barcode,
        is_active=True,
        created_by=current_user.id
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# GET ALL PRODUCTS
@router.get(
    "",
    response_model=list[ProductResponse]
)
def get_products(
    search: Optional[str] = Query(
        default=None,
        description="Search by product name or SKU"
    ),
    category_id: Optional[int] = Query(
        default=None
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
        db.query(Product)
        .filter(Product.is_active == True)
    )

    # Search
    if search:

        search_value = f"%{search}%"

        query = query.filter(
            (Product.product_name.ilike(search_value))
            |
            (Product.sku.ilike(search_value))
        )

    # Category filter
    if category_id is not None:

        query = query.filter(
            Product.category_id == category_id
        )

    # Pagination
    offset = (page - 1) * limit

    products = (
        query
        .order_by(Product.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return products


# GET PRODUCT BY ID
@router.get(
    "/{product_id}",
    response_model=ProductResponse
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

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

    return product


# UPDATE PRODUCT
@router.put(
    "/{product_id}",
    response_model=ProductResponse
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.INVENTORY_MANAGER
        )
    )
):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update an inactive product"
        )

    # SKU
    if product_data.sku is not None:

        existing_sku = (
            db.query(Product)
            .filter(
                Product.sku == product_data.sku,
                Product.id != product_id
            )
            .first()
        )

        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="SKU already exists"
            )

        product.sku = product_data.sku

    # Product name
    if product_data.product_name is not None:
        product.product_name = product_data.product_name

    # Description
    if product_data.description is not None:
        product.description = product_data.description

    # Category
    if product_data.category_id is not None:

        category = (
            db.query(Category)
            .filter(
                Category.id == product_data.category_id,
                Category.is_active == True
            )
            .first()
        )

        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found or inactive"
            )

        product.category_id = product_data.category_id

    # Unit
    if product_data.unit is not None:
        product.unit = product_data.unit.value

    # Cost price
    if product_data.cost_price is not None:
        product.cost_price = product_data.cost_price

    # Selling price
    if product_data.selling_price is not None:
        product.selling_price = product_data.selling_price

    # Price validation
    if product.selling_price < product.cost_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price must be greater than or equal to cost price"
        )

    # Reorder level
    if product_data.reorder_level is not None:
        product.reorder_level = product_data.reorder_level

    # Reorder quantity
    if product_data.reorder_quantity is not None:
        product.reorder_quantity = product_data.reorder_quantity

    # Barcode
    if product_data.barcode is not None:

        existing_barcode = (
            db.query(Product)
            .filter(
                Product.barcode == product_data.barcode,
                Product.id != product_id
            )
            .first()
        )

        if existing_barcode:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Barcode already exists"
            )

        product.barcode = product_data.barcode

    # Active status
    if product_data.is_active is not None:
        product.is_active = product_data.is_active

    db.commit()
    db.refresh(product)

    return product


# DELETE PRODUCT
@router.delete(
    "/{product_id}"
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    )
):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is already inactive"
        )

    product.is_active = False

    db.commit()

    return {
        "message": "Product deleted successfully"
    }