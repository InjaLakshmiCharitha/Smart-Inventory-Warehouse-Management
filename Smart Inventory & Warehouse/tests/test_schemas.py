from decimal import Decimal
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.schemas import (
    ProductCreate,
    ProductBatchCreate,
    StockTransferCreate,
    StockAdjustmentCreate,
    SupplierCreate,
)
from app.models.models import (
    ProductUnit,
    AdjustmentReason,
)


def test_valid_product():

    product = ProductCreate(
        name="Laptop",
        sku="LAP-001",
        category_id=1,
        unit="Piece",
        cost_price=Decimal("50000"),
        selling_price=Decimal("55000"),
        reorder_level=10,
        reorder_quantity=20
    )

    assert product.name == "Laptop"


def test_selling_price_cannot_be_less_than_cost_price():

    with pytest.raises(ValidationError):

        ProductCreate(
            name="Laptop",
            sku="LAP-002",
            category_id=1,
            unit="Piece",
            cost_price=Decimal("50000"),
            selling_price=Decimal("40000"),
            reorder_level=10,
            reorder_quantity=20
        )


def test_quantity_must_be_positive():

    with pytest.raises(ValidationError):

        ProductCreate(
            name="Laptop",
            sku="LAP-003",
            category_id=1,
            unit="Piece",
            cost_price=Decimal("50000"),
            selling_price=Decimal("55000"),
            reorder_level=-1,
            reorder_quantity=20
        )


def test_product_create_valid():
    product = ProductCreate(
        sku="TEST-001",
        name="Test Product",
        category_id=1,
        unit=ProductUnit.PIECE,
        cost_price=100,
        selling_price=150,
        reorder_level=10,
        reorder_quantity=50
    )

    assert product.sku == "TEST-001"
    assert product.name == "Test Product"
    assert product.selling_price == Decimal("150")


def test_product_price_validation():
    with pytest.raises(ValidationError):
        ProductCreate(
            sku="TEST-002",
            name="Test Product",
            category_id=1,
            unit=ProductUnit.PIECE,
            cost_price=200,
            selling_price=100
        )


def test_stock_transfer_same_warehouse():
    with pytest.raises(ValidationError):
        StockTransferCreate(
            from_warehouse_id=1,
            to_warehouse_id=1,
            items=[
                {
                    "product_id": 1,
                    "quantity": 5
                }
            ]
        )


def test_stock_adjustment_zero_quantity():
    with pytest.raises(ValidationError):
        StockAdjustmentCreate(
            product_id=1,
            warehouse_id=1,
            quantity=0,
            reason=AdjustmentReason.DAMAGED
        )


def test_batch_expiry_before_manufacturing():
    with pytest.raises(ValidationError):
        ProductBatchCreate(
            product_id=1,
            warehouse_id=1,
            batch_number="BATCH-001",
            manufacturing_date=date(2026, 10, 10),
            expiry_date=date(2026, 10, 5),
            quantity=10,
            unit_cost=100
        )


def test_batch_valid():
    batch = ProductBatchCreate(
        product_id=1,
        warehouse_id=1,
        batch_number="BATCH-002",
        manufacturing_date=date(2026, 10, 1),
        expiry_date=date(2027, 10, 1),
        quantity=100,
        unit_cost=Decimal("50")
    )

    assert batch.quantity == 100
    assert batch.batch_number == "BATCH-002"        