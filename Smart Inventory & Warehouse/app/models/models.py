from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship

from app.database import Base

# ENUMS
class UserRole(str, Enum):
    ADMIN = "Admin"
    INVENTORY_MANAGER = "Inventory Manager"
    WAREHOUSE_STAFF = "Warehouse Staff"


class EmploymentType(str, Enum):
    FULL_TIME = "Full Time"
    PART_TIME = "Part Time"
    CONTRACT = "Contract"


class ProductUnit(str, Enum):
    PIECE = "Piece"
    BOX = "Box"
    KG = "Kg"
    LITRE = "Litre"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"
    PARTIALLY_RECEIVED = "Partially Received"
    RECEIVED = "Received"
    CANCELLED = "Cancelled"


class SalesOrderStatus(str, Enum):
    DRAFT = "Draft"
    CONFIRMED = "Confirmed"
    PICKED = "Picked"
    PACKED = "Packed"
    DISPATCHED = "Dispatched"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class StockMovementType(str, Enum):
    PURCHASE_RECEIPT = "Purchase Receipt"
    SALE_DISPATCH = "Sale Dispatch"
    CUSTOMER_RETURN = "Customer Return"
    TRANSFER_OUT = "Transfer Out"
    TRANSFER_IN = "Transfer In"
    ADJUSTMENT = "Adjustment"


class ReturnStatus(str, Enum):
    REQUESTED = "Requested"
    INSPECTED = "Inspected"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REFUNDED = "Refunded"


class ReturnCondition(str, Enum):
    GOOD = "Good"
    DAMAGED = "Damaged"


class TransferStatus(str, Enum):
    PENDING = "Pending"
    IN_TRANSIT = "In Transit"
    RECEIVED = "Received"
    CANCELLED = "Cancelled"


class AdjustmentStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class AdjustmentReason(str, Enum):
    DAMAGED = "Damaged"
    LOST = "Lost"
    EXPIRED = "Expired"
    FOUND = "Found"
    COUNT_CORRECTION = "Count Correction"


# USER
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(150),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(String(255), nullable=False)

    role = Column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.WAREHOUSE_STAFF
    )

    employment_type = Column(
        SQLEnum(EmploymentType),
        nullable=False,
        default=EmploymentType.FULL_TIME
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    warehouse = relationship(
        "Warehouse",
        back_populates="staff",
        foreign_keys=[warehouse_id]
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="user"
    )


# CATEGORY
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)

    category_name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    products = relationship(
        "Product",
        back_populates="category"
    )


# PRODUCT
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String(150),
        nullable=False,
        index=True
    )

    sku = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    barcode = Column(
        String(100),
        unique=True,
        nullable=True,
        index=True
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False
    )

    unit = Column(
        SQLEnum(ProductUnit),
        nullable=False
    )

    cost_price = Column(
        Numeric(12, 2),
        nullable=False
    )

    selling_price = Column(
        Numeric(12, 2),
        nullable=False
    )

    reorder_level = Column(
        Integer,
        nullable=False,
        default=0
    )

    reorder_quantity = Column(
        Integer,
        nullable=False,
        default=0
    )

    preferred_supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    category = relationship(
        "Category",
        back_populates="products"
    )

    preferred_supplier = relationship(
        "Supplier",
        back_populates="preferred_products",
        foreign_keys=[preferred_supplier_id]
    )

    inventory = relationship(
        "Inventory",
        back_populates="product"
    )

    stock_movements = relationship(
        "StockMovement",
        back_populates="product"
    )

    purchase_order_items = relationship(
        "PurchaseOrderItem",
        back_populates="product"
    )

    sales_order_items = relationship(
        "SalesOrderItem",
        back_populates="product"
    )

    return_items = relationship(
        "ReturnItem",
        back_populates="product"
    )

    batches = relationship(
        "ProductBatch",
        back_populates="product"
    )


# WAREHOUSE
class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)

    warehouse_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    city = Column(
        String(100),
        nullable=False
    )

    address = Column(
        Text,
        nullable=False
    )

    capacity = Column(
        Integer,
        nullable=False
    )

    manager_id = Column(
        Integer,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    staff = relationship(
        "User",
        back_populates="warehouse",
        foreign_keys="User.warehouse_id"
    )

    inventory = relationship(
        "Inventory",
        back_populates="warehouse"
    )

    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="warehouse"
    )

    sales_orders = relationship(
        "SalesOrder",
        back_populates="warehouse"
    )

    outgoing_transfers = relationship(
        "StockTransfer",
        foreign_keys="StockTransfer.source_warehouse_id",
        back_populates="source_warehouse"
    )

    incoming_transfers = relationship(
        "StockTransfer",
        foreign_keys="StockTransfer.destination_warehouse_id",
        back_populates="destination_warehouse"
    )


# INVENTORY
class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    average_cost = Column(Numeric(12, 2), default=0)
    
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    quantity_on_hand = Column(
        Integer,
        nullable=False,
        default=0
    )

    quantity_reserved = Column(
        Integer,
        nullable=False,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name="uq_product_warehouse"
        ),
    )

    product = relationship(
        "Product",
        back_populates="inventory"
    )

    warehouse = relationship(
        "Warehouse",
        back_populates="inventory"
    )

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved


# STOCK MOVEMENT
class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    movement_type = Column(
        SQLEnum(StockMovementType),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    reference_id = Column(
        Integer,
        nullable=True
    )

    balance_after = Column(
        Integer,
        nullable=False
    )

    performed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    product = relationship(
        "Product",
        back_populates="stock_movements"
    )

    warehouse = relationship(
        "Warehouse"
    )

    user = relationship(
        "User"
    )


# SUPPLIER
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)

    supplier_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        nullable=False
    )

    phone = Column(
        String(10),
        nullable=False
    )

    gst_number = Column(
        String(15),
        unique=True,
        nullable=True
    )

    address = Column(
        Text,
        nullable=False
    )

    lead_time_days = Column(
        Integer,
        nullable=False,
        default=0
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="supplier"
    )

    preferred_products = relationship(
        "Product",
        back_populates="preferred_supplier",
        foreign_keys="Product.preferred_supplier_id"
    )


# PURCHASE ORDER
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)

    po_number = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    expected_delivery_date = Column(
        Date,
        nullable=True
    )

    received_at = Column(
        DateTime,
        nullable=True
    )

    total_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    status = Column(
        SQLEnum(PurchaseOrderStatus),
        nullable=False,
        default=PurchaseOrderStatus.DRAFT
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    supplier = relationship(
        "Supplier",
        back_populates="purchase_orders"
    )

    warehouse = relationship(
        "Warehouse",
        back_populates="purchase_orders"
    )

    items = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan"
    )


# PURCHASE ORDER ITEM
class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)

    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    quantity_ordered = Column(
        Integer,
        nullable=False
    )

    quantity_received = Column(
        Integer,
        nullable=False,
        default=0
    )

    unit_cost = Column(
        Numeric(12, 2),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    purchase_order = relationship(
        "PurchaseOrder",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="purchase_order_items"
    )


# CUSTOMER
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    customer_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        nullable=False
    )

    phone = Column(
        String(10),
        nullable=False
    )

    address = Column(
        Text,
        nullable=False
    )

    credit_limit = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    sales_orders = relationship(
        "SalesOrder",
        back_populates="customer"
    )


# SALES ORDER
class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)

    so_number = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    subtotal = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    tax_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    grand_total = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    status = Column(
        SQLEnum(SalesOrderStatus),
        nullable=False,
        default=SalesOrderStatus.DRAFT
    )

    courier_name = Column(
        String(100),
        nullable=True
    )

    tracking_number = Column(
        String(100),
        unique=True,
        nullable=True
    )

    dispatched_at = Column(
        DateTime,
        nullable=True
    )

    delivered_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    customer = relationship(
        "Customer",
        back_populates="sales_orders"
    )

    warehouse = relationship(
        "Warehouse",
        back_populates="sales_orders"
    )

    items = relationship(
        "SalesOrderItem",
        back_populates="sales_order",
        cascade="all, delete-orphan"
    )

    returns = relationship(
        "Return",
        back_populates="sales_order"
    )

    reservations = relationship(
        "StockReservation",
        back_populates="sales_order"
    )


# SALES ORDER ITEM
class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    id = Column(Integer, primary_key=True, index=True)

    sales_order_id = Column(
        Integer,
        ForeignKey("sales_orders.id"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    unit_price = Column(
        Numeric(12, 2),
        nullable=False
    )

    line_total = Column(
        Numeric(14, 2),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    sales_order = relationship(
        "SalesOrder",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="sales_order_items"
    )


# STOCK RESERVATION
class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True)

    sales_order_id = Column(
        Integer,
        ForeignKey("sales_orders.id"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    sales_order = relationship(
        "SalesOrder",
        back_populates="reservations"
    )

    product = relationship(
        "Product"
    )

    warehouse = relationship(
        "Warehouse"
    )


# RETURN
class Return(Base):
    __tablename__ = "returns"

    id = Column(Integer, primary_key=True, index=True)

    sales_order_id = Column(
        Integer,
        ForeignKey("sales_orders.id"),
        nullable=False
    )

    reason = Column(
        Text,
        nullable=False
    )

    status = Column(
        SQLEnum(ReturnStatus),
        nullable=False,
        default=ReturnStatus.REQUESTED
    )

    refund_amount = Column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00")
    )

    rejection_reason = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    sales_order = relationship(
        "SalesOrder",
        back_populates="returns"
    )

    items = relationship(
        "ReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan"
    )


# RETURN ITEM
class ReturnItem(Base):
    __tablename__ = "return_items"

    id = Column(Integer, primary_key=True, index=True)

    return_id = Column(
        Integer,
        ForeignKey("returns.id"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    condition = Column(
        SQLEnum(ReturnCondition),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    return_request = relationship(
        "Return",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="return_items"
    )


# NOTIFICATION
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    recipient_email = Column(
        String(150),
        nullable=False
    )

    subject = Column(
        String(255),
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    notification_type = Column(
        String(100),
        nullable=False
    )

    is_sent = Column(
        Boolean,
        default=False,
        nullable=False
    )

    error_message = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# AUDIT LOG
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    action = Column(
        String(50),
        nullable=False
    )

    entity_type = Column(
        String(100),
        nullable=False
    )

    entity_id = Column(
        Integer,
        nullable=True
    )

    old_value = Column(
        Text,
        nullable=True
    )

    new_value = Column(
        Text,
        nullable=True
    )

    timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="audit_logs"
    )


# PRODUCT BATCH - BONUS
class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    batch_number = Column(
        String(100),
        nullable=False
    )

    expiry_date = Column(
        Date,
        nullable=True
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=0
    )

    unit_cost = Column(
        Numeric(12, 2),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    product = relationship(
        "Product",
        back_populates="batches"
    )

    warehouse = relationship(
        "Warehouse"
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            "batch_number",
            name="uq_product_warehouse_batch"
        ),
    )


# STOCK TRANSFER - BONUS
class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id = Column(Integer, primary_key=True, index=True)

    transfer_number = Column(
        String(50),
        unique=True,
        nullable=False
    )

    source_warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    destination_warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    status = Column(
        SQLEnum(TransferStatus),
        nullable=False,
        default=TransferStatus.PENDING
    )

    dispatched_at = Column(
        DateTime,
        nullable=True
    )

    received_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    source_warehouse = relationship(
        "Warehouse",
        foreign_keys=[source_warehouse_id],
        back_populates="outgoing_transfers"
    )

    destination_warehouse = relationship(
        "Warehouse",
        foreign_keys=[destination_warehouse_id],
        back_populates="incoming_transfers"
    )

    items = relationship(
        "StockTransferItem",
        back_populates="transfer",
        cascade="all, delete-orphan"
    )


# STOCK TRANSFER ITEM - BONUS
class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"

    id = Column(Integer, primary_key=True, index=True)

    transfer_id = Column(
        Integer,
        ForeignKey("stock_transfers.id"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    quantity_received = Column(
        Integer,
        nullable=False,
        default=0
    )

    shortage_quantity = Column(
        Integer,
        nullable=False,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    transfer = relationship(
        "StockTransfer",
        back_populates="items"
    )

    product = relationship(
        "Product"
    )


# STOCK ADJUSTMENT - BONUS
class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    reason = Column(
        SQLEnum(AdjustmentReason),
        nullable=False
    )

    status = Column(
        SQLEnum(AdjustmentStatus),
        nullable=False,
        default=AdjustmentStatus.PENDING
    )

    remarks = Column(
        Text,
        nullable=True
    )

    rejection_reason = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        nullable=True
    )

    product = relationship(
        "Product"
    )

    warehouse = relationship(
        "Warehouse"
    )