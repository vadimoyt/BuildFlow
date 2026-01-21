from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    DateTime,
    Numeric,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FOREMAN = "foreman"
    CLIENT = "client"


class TransactionCategory(str, enum.Enum):
    MATERIALS = "materials"
    LABOR = "labor"
    OTHER = "other"


class ProjectStage(str, enum.Enum):
    DRAFT = "draft"
    ELECTRIC = "electric"
    FINISH = "finish"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", create_constraint=True),
        nullable=False,
        default=UserRole.FOREMAN,
    )

    # relationships (future use)
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.tg_id} role={self.role}>"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    budget: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # optional owner (foreman/admin) if needed later
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner: Mapped[User | None] = relationship(
        "User",
        back_populates="projects",
        lazy="joined",
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    progress_photos: Mapped[list["ProgressPhoto"]] = relationship(
        "ProgressPhoto",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[TransactionCategory] = mapped_column(
        Enum(TransactionCategory, name="transaction_category_enum", create_constraint=True),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="approved", nullable=False)  # approved, pending, rejected
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="transactions",
        lazy="joined",
    )
    created_by = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} "
            f"project_id={self.project_id} amount={self.amount} status={self.status}>"
        )


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    photo_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Telegram file_id
    stage: Mapped[ProjectStage] = mapped_column(
        Enum(ProjectStage, name="project_stage_enum", create_constraint=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="progress_photos",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProgressPhoto id={self.id} "
            f"project_id={self.project_id} stage={self.stage}>"
        )


# ============ НОВЫЕ МОДЕЛИ ДЛЯ v3.0 ============

class TransactionStatus(str, enum.Enum):
    """Статусы транзакций (для Change Orders)."""
    PENDING = "pending"  # Ожидает одобрения
    APPROVED = "approved"  # Одобрено заказчиком
    REJECTED = "rejected"  # Отклонено


class ChangeOrder(Base):
    """Модель для системы согласований (Change Orders)."""
    __tablename__ = "change_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status_enum", create_constraint=True),
        nullable=False,
        default=TransactionStatus.PENDING,
    )
    requested_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    transaction = relationship("Transaction", lazy="joined")
    requester = relationship("User", foreign_keys=[requested_by_id], lazy="joined")
    approver = relationship("User", foreign_keys=[approved_by_id], lazy="joined")

    def __repr__(self) -> str:
        return f"<ChangeOrder id={self.id} status={self.status}>"


class Task(Base):
    """Модель для простого списка задач на объекте."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_completed: Mapped[bool] = mapped_column(default=False, index=True)
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    project = relationship("Project", lazy="joined")
    assigned_to = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} completed={self.is_completed}>"
