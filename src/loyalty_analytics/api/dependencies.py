from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from loyalty_analytics.database import get_db

PageNumber = Annotated[int, Query(ge=1, description="Page number")]
PageSize = Annotated[int, Query(ge=1, le=100, description="Items per page")]
DatabaseSession = Annotated[Session, Depends(get_db)]
