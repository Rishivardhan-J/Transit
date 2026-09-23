from sqlalchemy import Column, String, Enum
import enum
from .base import Base

class Role(str, enum.Enum):
    manager = "manager"
    researcher = "researcher"
    admin = "admin"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), default=Role.manager, nullable=False)
