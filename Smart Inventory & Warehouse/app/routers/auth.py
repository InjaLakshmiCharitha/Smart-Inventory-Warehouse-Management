from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.auth import ( create_access_token, hash_password, verify_password )

from app.auth.dependencies import ( get_current_user, get_optional_current_user )

from app.database import get_db

from app.models.models import (
    User,
    UserRole,
    Warehouse
)

from app.schemas.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# REGISTER
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_optional_current_user
    )
):
    """
    Register a new user.

    First user:
        Can create the initial Admin account.

    After an Admin exists:
        Only an Admin can create new users.
    """

    # Check how many users already exist
    user_count = db.query(User).count()

    # FIRST USER
    if user_count == 0:

        # First user MUST be Admin
        if user_data.role != UserRole.ADMIN:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The first user must be an Admin"
            )

    # USERS AFTER FIRST ADMIN
    else:

        # Get the Authorization user separately
        # from the token dependency.
        #
        # For this version, registration after the first
        # user will be handled by a separate Admin check.

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an Admin can register additional users"
        )

    # Check duplicate email
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Warehouse validation
    if user_data.warehouse_id is not None:

        warehouse = db.query(Warehouse).filter(
            Warehouse.id == user_data.warehouse_id,
            Warehouse.is_active == True
        ).first()

        if warehouse is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found or inactive"
            )

    # Warehouse Staff must have a warehouse
    if (
        user_data.role == UserRole.WAREHOUSE_STAFF
        and user_data.warehouse_id is None
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse Staff must be assigned to a warehouse"
        )

    # Create user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        ),
        role=user_data.role,
        employment_type=user_data.employment_type,
        warehouse_id=user_data.warehouse_id,
        is_active=True
    )

    db.add(new_user)

    db.commit()

    db.refresh(new_user)

    return new_user


# LOGIN
@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):

    # Find user
    user = db.query(User).filter(
        User.email == login_data.email
    ).first()

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(
        login_data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check active status
    if not user.is_active:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create JWT
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


# CURRENT USER
@router.get(
    "/me",
    response_model=UserResponse
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):

    return current_user