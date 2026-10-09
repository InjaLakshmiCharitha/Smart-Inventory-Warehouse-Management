from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.models import (
    UserRole,
    EmploymentType,
    ProductUnit,
    PurchaseOrderStatus,
    SalesOrderStatus,
    ReturnStatus,
    ReturnCondition,
    TransferStatus,
    AdjustmentStatus,
    AdjustmentReason,
)


# COMMON VALIDATORS
def validate_phone(value: str) -> str:
    if not value.isdigit() or len(value) != 10:
        raise ValueError("Phone number must contain exactly 10 digits")

    return value


def validate_positive_integer(value: int) -> int:
    if value <= 0:
        raise ValueError("Value must be greater than 0")

    return value


def validate_positive_decimal(value: Decimal) -> Decimal:
    if value <= 0:
        raise ValueError("Value must be greater than 0")

    return value


# AUTHENTICATION
class LoginRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=100
    )


class RegisterRequest(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=100
    )

    role: UserRole = UserRole.WAREHOUSE_STAFF

    employment_type: EmploymentType = EmploymentType.FULL_TIME

    warehouse_id: Optional[int] = None


class UserResponse(BaseModel):

    id: int

    name: str

    email: EmailStr

    role: UserRole

    employment_type: EmploymentType

    warehouse_id: Optional[int]

    is_active: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"


# CATEGORY
class CategoryCreate(BaseModel):

    category_name: str = Field(
        min_length=1,
        max_length=100
    )

    description: Optional[str] = None


class CategoryUpdate(BaseModel):

    category_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    description: Optional[str] = None

    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):

    id: int

    category_name: str

    description: Optional[str]

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# PRODUCT
class ProductCreate(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=150
    )

    sku: str = Field(
        min_length=1,
        max_length=100
    )

    barcode: Optional[str] = Field(
        default=None,
        max_length=100
    )

    category_id: int

    unit: ProductUnit

    cost_price: Decimal = Field(
        gt=0
    )

    selling_price: Decimal = Field(
        gt=0
    )

    reorder_level: int = Field(
        ge=0
    )

    reorder_quantity: int = Field(
        ge=0
    )

    preferred_supplier_id: Optional[int] = None

    is_active: bool = True

    @model_validator(mode="after")
    def validate_prices(self):

        if self.selling_price < self.cost_price:
            raise ValueError(
                "Selling price must be greater than or equal to cost price"
            )

        return self


class ProductUpdate(BaseModel):

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    barcode: Optional[str] = Field(
        default=None,
        max_length=100
    )

    category_id: Optional[int] = None

    unit: Optional[ProductUnit] = None

    cost_price: Optional[Decimal] = Field(
        default=None,
        gt=0
    )

    selling_price: Optional[Decimal] = Field(
        default=None,
        gt=0
    )

    reorder_level: Optional[int] = Field(
        default=None,
        ge=0
    )

    reorder_quantity: Optional[int] = Field(
        default=None,
        ge=0
    )

    preferred_supplier_id: Optional[int] = None

    is_active: Optional[bool] = None


class ProductStockResponse(BaseModel):

    warehouse_id: int

    warehouse_name: str

    quantity_on_hand: int

    quantity_reserved: int

    quantity_available: int


class ProductResponse(BaseModel):

    id: int

    name: str

    sku: str

    barcode: Optional[str]

    category_id: int

    unit: ProductUnit

    cost_price: Decimal

    selling_price: Decimal

    reorder_level: int

    reorder_quantity: int

    preferred_supplier_id: Optional[int]

    is_active: bool

    created_at: datetime

    updated_at: datetime

    stock: List[ProductStockResponse] = []

    total_stock: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )


# WAREHOUSE
class WarehouseCreate(BaseModel):

    warehouse_code: str = Field(
        min_length=1,
        max_length=50
    )

    name: str = Field(
        min_length=1,
        max_length=150
    )

    city: str = Field(
        min_length=1,
        max_length=100
    )

    address: str = Field(
        min_length=1
    )

    capacity: int = Field(
        gt=0
    )

    manager_id: Optional[int] = None

    is_active: bool = True


class WarehouseUpdate(BaseModel):

    warehouse_code: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50
    )

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    city: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    address: Optional[str] = None

    capacity: Optional[int] = Field(
        default=None,
        gt=0
    )

    manager_id: Optional[int] = None

    is_active: Optional[bool] = None


class WarehouseResponse(BaseModel):

    id: int

    warehouse_code: str

    name: str

    city: str

    address: str

    capacity: int

    manager_id: Optional[int]

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# INVENTORY
class InventoryResponse(BaseModel):

    id: int

    product_id: int

    warehouse_id: int

    quantity_on_hand: int

    quantity_reserved: int

    quantity_available: int

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# STOCK MOVEMENT
class StockMovementResponse(BaseModel):

    id: int

    product_id: int

    warehouse_id: int

    movement_type: str

    quantity: int

    reference_id: Optional[int]

    balance_after: int

    performed_by: Optional[int]

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# SUPPLIER
class SupplierCreate(BaseModel):

    supplier_code: str = Field(
        min_length=1,
        max_length=50
    )

    name: str = Field(
        min_length=1,
        max_length=150
    )

    email: EmailStr

    phone: str

    gst_number: Optional[str] = Field(
        default=None,
        min_length=15,
        max_length=15
    )

    address: str = Field(
        min_length=1
    )

    lead_time_days: int = Field(
        ge=0
    )

    is_active: bool = True

    @field_validator("phone")
    @classmethod
    def validate_supplier_phone(cls, value):
        return validate_phone(value)


class SupplierUpdate(BaseModel):

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    email: Optional[EmailStr] = None

    phone: Optional[str] = None

    gst_number: Optional[str] = Field(
        default=None,
        min_length=15,
        max_length=15
    )

    address: Optional[str] = None

    lead_time_days: Optional[int] = Field(
        default=None,
        ge=0
    )

    is_active: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_supplier_phone(cls, value):
        if value is None:
            return value

        return validate_phone(value)


class SupplierResponse(BaseModel):

    id: int

    supplier_code: str

    name: str

    email: EmailStr

    phone: str

    gst_number: Optional[str]

    address: str

    lead_time_days: int

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# PURCHASE ORDER
class PurchaseOrderItemCreate(BaseModel):

    product_id: int

    quantity_ordered: int = Field(
        gt=0
    )

    unit_cost: Decimal = Field(
        gt=0
    )


class PurchaseOrderCreate(BaseModel):

    supplier_id: int

    warehouse_id: int

    expected_delivery_date: Optional[date] = None

    items: List[PurchaseOrderItemCreate] = Field(
        min_length=1
    )


class PurchaseOrderItemResponse(BaseModel):

    id: int

    product_id: int

    quantity_ordered: int

    quantity_received: int

    unit_cost: Decimal

    model_config = ConfigDict(
        from_attributes=True
    )


class PurchaseOrderResponse(BaseModel):

    id: int

    po_number: str

    supplier_id: int

    warehouse_id: int

    expected_delivery_date: Optional[date]

    received_at: Optional[datetime]

    total_amount: Decimal

    status: PurchaseOrderStatus

    items: List[PurchaseOrderItemResponse]

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class PurchaseReceiveItem(BaseModel):

    item_id: int

    quantity_received: int = Field(
        gt=0
    )

    batch_number: Optional[str] = None

    expiry_date: Optional[date] = None


class PurchaseReceiveRequest(BaseModel):

    items: List[PurchaseReceiveItem] = Field(
        min_length=1
    )


# CUSTOMER
class CustomerCreate(BaseModel):

    customer_code: str = Field(
        min_length=1,
        max_length=50
    )

    name: str = Field(
        min_length=1,
        max_length=150
    )

    email: EmailStr

    phone: str

    address: str = Field(
        min_length=1
    )

    credit_limit: Decimal = Field(
        ge=0
    )

    is_active: bool = True

    @field_validator("phone")
    @classmethod
    def validate_customer_phone(cls, value):
        return validate_phone(value)


class CustomerUpdate(BaseModel):

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=150
    )

    email: Optional[EmailStr] = None

    phone: Optional[str] = None

    address: Optional[str] = None

    credit_limit: Optional[Decimal] = Field(
        default=None,
        ge=0
    )

    is_active: Optional[bool] = None

    @field_validator("phone")
    @classmethod
    def validate_customer_phone(cls, value):
        if value is None:
            return value

        return validate_phone(value)


class CustomerResponse(BaseModel):

    id: int

    customer_code: str

    name: str

    email: EmailStr

    phone: str

    address: str

    credit_limit: Decimal

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# SALES ORDER
class SalesOrderItemCreate(BaseModel):

    product_id: int

    quantity: int = Field(
        gt=0
    )


class SalesOrderCreate(BaseModel):

    customer_id: int

    warehouse_id: int

    items: List[SalesOrderItemCreate] = Field(
        min_length=1
    )


class SalesOrderItemResponse(BaseModel):

    id: int

    product_id: int

    quantity: int

    unit_price: Decimal

    line_total: Decimal

    model_config = ConfigDict(
        from_attributes=True
    )


class SalesOrderResponse(BaseModel):

    id: int

    so_number: str

    customer_id: int

    warehouse_id: int

    subtotal: Decimal

    tax_amount: Decimal

    grand_total: Decimal

    status: SalesOrderStatus

    courier_name: Optional[str]

    tracking_number: Optional[str]

    dispatched_at: Optional[datetime]

    delivered_at: Optional[datetime]

    items: List[SalesOrderItemResponse]

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class DispatchRequest(BaseModel):

    courier_name: str = Field(
        min_length=1,
        max_length=100
    )

    tracking_number: str = Field(
        min_length=1,
        max_length=100
    )


# RETURNS
class ReturnItemCreate(BaseModel):

    product_id: int

    quantity: int = Field(
        gt=0
    )


class ReturnCreate(BaseModel):

    items: List[ReturnItemCreate] = Field(
        min_length=1
    )

    reason: str = Field(
        min_length=1
    )


class ReturnInspectItem(BaseModel):

    item_id: int

    condition: ReturnCondition


class ReturnInspectRequest(BaseModel):

    items: List[ReturnInspectItem] = Field(
        min_length=1
    )


class ReturnRejectRequest(BaseModel):

    rejection_reason: str = Field(
        min_length=1
    )


class ReturnItemResponse(BaseModel):

    id: int

    product_id: int

    quantity: int

    condition: Optional[ReturnCondition]

    model_config = ConfigDict(
        from_attributes=True
    )


class ReturnResponse(BaseModel):

    id: int

    sales_order_id: int

    reason: str

    status: ReturnStatus

    refund_amount: Decimal

    rejection_reason: Optional[str]

    items: List[ReturnItemResponse]

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

# NOTIFICATIONS
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# AUDITLOG
class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    entity_type: str
    entity_id: int
    description: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

# STOCK TRANSFERS - BONUS
class StockTransferItemCreate(BaseModel):

    product_id: int

    quantity: int = Field(
        gt=0
    )


class StockTransferCreate(BaseModel):

    source_warehouse_id: int

    destination_warehouse_id: int

    items: List[StockTransferItemCreate] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_warehouses(self):

        if (
            self.source_warehouse_id
            == self.destination_warehouse_id
        ):
            raise ValueError(
                "Source and destination warehouses must be different"
            )

        return self


class StockTransferReceiveItem(BaseModel):

    item_id: int

    quantity_received: int = Field(
        gt=0
    )


class StockTransferReceiveRequest(BaseModel):

    items: List[StockTransferReceiveItem] = Field(
        min_length=1
    )


class StockTransferItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class StockTransferResponse(BaseModel):
    id: int
    transfer_number: str
    from_warehouse_id: int
    to_warehouse_id: int
    status: TransferStatus
    created_by: int
    created_at: datetime
    items: list[StockTransferItemResponse]

    model_config = ConfigDict(from_attributes=True)    


# STOCK ADJUSTMENTS - BONUS
class StockAdjustmentCreate(BaseModel):

    product_id: int

    warehouse_id: int

    quantity: int = Field(
        gt=0
    )

    reason: AdjustmentReason

    remarks: Optional[str] = None


class StockAdjustmentRejectRequest(BaseModel):

    rejection_reason: str = Field(
        min_length=1
    )


class StockAdjustmentResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    quantity: int
    reason: AdjustmentReason
    status: AdjustmentStatus
    notes: Optional[str]
    created_by: int
    approved_by: Optional[int]
    created_at: datetime
    approved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# PAGINATION
class PaginationParams(BaseModel):

    skip: int = Field(
        default=0,
        ge=0
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100
    )


# BATCH
class ProductBatchCreate(BaseModel):
    product_id: int
    warehouse_id: int
    batch_number: str = Field(min_length=1, max_length=100)
    manufacturing_date: Optional[date] = None
    expiry_date: date
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.manufacturing_date
            and self.expiry_date < self.manufacturing_date
        ):
            raise ValueError(
                "Expiry date must be after manufacturing date"
            )
        return self


class ProductBatchResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    batch_number: str
    expiry_date: Optional[date] = None
    quantity: int
    unit_cost: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)    