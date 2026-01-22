"""CRUD операции для работы с моделями БД."""

from sqlalchemy.orm import Session
from datetime import datetime

from .models import (
    User, Project, Transaction, ProgressPhoto, 
    UserRole, TransactionCategory, ProjectStage,
    ChangeOrder, Task, TransactionStatus
)


# ============ USER CRUD ============

def get_user_by_tg_id(session: Session, tg_id: int) -> User | None:
    """Получить пользователя по Telegram ID."""
    return session.query(User).filter(User.tg_id == tg_id).one_or_none()


def create_user(
    session: Session,
    tg_id: int,
    name: str,
    role: UserRole = UserRole.FOREMAN,
) -> User:
    """Создать нового пользователя."""
    user = User(tg_id=tg_id, name=name, role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_or_create_user(
    session: Session,
    tg_id: int,
    name: str,
) -> User:
    """Получить существующего пользователя или создать нового."""
    user = get_user_by_tg_id(session, tg_id)
    if user is None:
        user = create_user(session, tg_id, name)
    return user


def update_user_role(
    session: Session,
    user_id: int,
    role: UserRole,
) -> User:
    """Обновить роль пользователя."""
    user = session.query(User).filter(User.id == user_id).one()
    user.role = role
    session.commit()
    session.refresh(user)
    return user


# ============ PROJECT CRUD ============

def get_project(session: Session, project_id: int) -> Project | None:
    """Получить проект по ID."""
    return session.query(Project).filter(Project.id == project_id).one_or_none()


def get_projects_by_user(session: Session, user_id: int) -> list[Project]:
    """Получить все проекты пользователя."""
    return session.query(Project).filter(Project.owner_id == user_id).all()


def get_user_projects(session: Session, user_id: int) -> list[Project]:
    """Получить все проекты пользователя (алиас для get_projects_by_user)."""
    return get_projects_by_user(session, user_id)


def create_project(
    session: Session,
    name: str,
    address: str,
    budget: float = 0.0,
    owner_id: int | None = None,
) -> Project:
    """Создать новый проект."""
    project = Project(
        name=name,
        address=address,
        budget=budget,
        owner_id=owner_id,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def get_project_budget_spent(session: Session, project_id: int) -> float:
    """Получить сумму потраченных средств по проекту."""
    transactions = session.query(Transaction).filter(
        Transaction.project_id == project_id
    ).all()
    return sum(float(t.amount) for t in transactions)


def get_project_report(session: Session, project_id: int) -> dict:
    """Получить краткий отчёт по проекту (План/Факт)."""
    project = get_project(session, project_id)
    if not project:
        return {}
    
    spent = get_project_budget_spent(session, project_id)
    remaining = float(project.budget) - spent
    
    return {
        "id": project.id,
        "name": project.name,
        "address": project.address,
        "budget_plan": float(project.budget),
        "budget_spent": spent,
        "budget_remaining": max(0, remaining),
        "transactions_count": len(project.transactions),
        "photos_count": len(project.progress_photos),
        "created_at": project.created_at,
    }


# ============ TRANSACTION CRUD ============

def create_transaction(
    session: Session,
    project_id: int,
    amount: float,
    category: TransactionCategory,
    description: str | None = None,
    photo_url: str | None = None,
    created_by_id: int | None = None,
) -> Transaction:
    """Создать новую операцию расходов."""
    transaction = Transaction(
        project_id=project_id,
        amount=amount,
        category=category,
        description=description,
        photo_url=photo_url,
        created_by_id=created_by_id,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


def get_project_transactions(session: Session, project_id: int) -> list[Transaction]:
    """Получить все операции расходов проекта."""
    return session.query(Transaction).filter(
        Transaction.project_id == project_id
    ).all()


def get_transactions_by_category(
    session: Session,
    project_id: int,
    category: TransactionCategory,
) -> list[Transaction]:
    """Получить операции расходов по категории."""
    return session.query(Transaction).filter(
        Transaction.project_id == project_id,
        Transaction.category == category,
    ).all()


# ============ PROGRESS PHOTO CRUD ============

def create_progress_photo(
    session: Session,
    project_id: int,
    photo_id: str,
    stage: ProjectStage,
) -> ProgressPhoto:
    """Создать новую фотографию прогресса."""
    photo = ProgressPhoto(
        project_id=project_id,
        photo_id=photo_id,
        stage=stage,
    )
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def get_project_photos_by_stage(
    session: Session,
    project_id: int,
    stage: ProjectStage,
) -> list[ProgressPhoto]:
    """Получить все фото проекта по этапу."""
    return session.query(ProgressPhoto).filter(
        ProgressPhoto.project_id == project_id,
        ProgressPhoto.stage == stage,
    ).all()


def get_all_project_photos(session: Session, project_id: int) -> list[ProgressPhoto]:
    """Получить все фото проекта."""
    return session.query(ProgressPhoto).filter(
        ProgressPhoto.project_id == project_id
    ).all()


# ============ РАСШИРЕННЫЕ СТАТИСТИКИ ============

def get_budget_by_category(session: Session, project_id: int) -> dict:
    """Получить разбор расходов по категориям."""
    transactions = get_project_transactions(session, project_id)
    
    stats = {
        "materials": 0.0,
        "labor": 0.0,
        "other": 0.0,
    }
    
    for t in transactions:
        stats[t.category.value] += float(t.amount)
    
    return stats


def get_daily_expenses(session: Session, project_id: int) -> dict:
    """Получить расходы по дням."""
    transactions = get_project_transactions(session, project_id)
    daily = {}
    
    for t in transactions:
        date_str = t.created_at.strftime("%d.%m.%Y")
        if date_str not in daily:
            daily[date_str] = 0.0
        daily[date_str] += float(t.amount)
    
    return daily


def get_project_progress(session: Session, project_id: int) -> dict:
    """Получить прогресс проекта по этапам."""
    photos = get_all_project_photos(session, project_id)
    
    stages = {
        "draft": 0,
        "electric": 0,
        "finish": 0,
    }
    
    for p in photos:
        stages[p.stage.value] += 1
    
    return stages


def delete_transaction(session: Session, transaction_id: int) -> bool:
    """Удалить операцию расхода."""
    try:
        transaction = session.query(Transaction).filter(
            Transaction.id == transaction_id
        ).one_or_none()
        
        if transaction:
            session.delete(transaction)
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        return False


def update_project_budget(session: Session, project_id: int, new_budget: float) -> bool:
    """Обновить бюджет проекта."""
    try:
        project = session.query(Project).filter(
            Project.id == project_id
        ).one_or_none()
        
        if project:
            project.budget = new_budget
            session.commit()
            return True
        return False
    except Exception:
        session.rollback()
        return False


# ============ CHANGE ORDER CRUD ============

def create_change_order(
    session: Session,
    transaction_id: int,
    requested_by_id: int,
) -> ChangeOrder:
    """Создать новый запрос на согласование (Change Order)."""
    change_order = ChangeOrder(
        transaction_id=transaction_id,
        status=TransactionStatus.PENDING,
        requested_by_id=requested_by_id,
    )
    session.add(change_order)
    session.commit()
    session.refresh(change_order)
    return change_order


def get_change_order(session: Session, change_order_id: int) -> ChangeOrder | None:
    """Получить Change Order по ID."""
    return session.query(ChangeOrder).filter(ChangeOrder.id == change_order_id).one_or_none()


def get_pending_change_orders(session: Session, user_id: int | None = None) -> list[ChangeOrder]:
    """Получить все ожидающие одобрения Change Orders."""
    query = session.query(ChangeOrder).filter(ChangeOrder.status == TransactionStatus.PENDING)
    if user_id:
        query = query.filter(ChangeOrder.approved_by_id == None)  # Не одобрены
    return query.all()


def get_change_orders_for_project(session: Session, project_id: int) -> list[ChangeOrder]:
    """Получить все Change Orders для проекта."""
    return (
        session.query(ChangeOrder)
        .join(Transaction, ChangeOrder.transaction_id == Transaction.id)
        .filter(Transaction.project_id == project_id)
        .all()
    )


def approve_change_order(
    session: Session,
    change_order_id: int,
    approved_by_id: int,
) -> ChangeOrder:
    """Одобрить Change Order."""
    change_order = get_change_order(session, change_order_id)
    if change_order:
        change_order.status = TransactionStatus.APPROVED
        change_order.approved_by_id = approved_by_id
        session.commit()
        session.refresh(change_order)
    return change_order


def reject_change_order(
    session: Session,
    change_order_id: int,
    approved_by_id: int,
    rejection_reason: str,
) -> ChangeOrder:
    """Отклонить Change Order."""
    change_order = get_change_order(session, change_order_id)
    if change_order:
        change_order.status = TransactionStatus.REJECTED
        change_order.approved_by_id = approved_by_id
        change_order.rejection_reason = rejection_reason
        session.commit()
        session.refresh(change_order)
    return change_order


# ============ TASK CRUD ============

def create_task(
    session: Session,
    project_id: int,
    title: str,
    description: str | None = None,
    assigned_to_id: int | None = None,
    due_date: datetime | None = None,
) -> Task:
    """Создать новую задачу."""
    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        assigned_to_id=assigned_to_id,
        due_date=due_date,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def get_task(session: Session, task_id: int) -> Task | None:
    """Получить задачу по ID."""
    return session.query(Task).filter(Task.id == task_id).one_or_none()


def get_project_tasks(
    session: Session,
    project_id: int,
    completed_only: bool = False,
) -> list[Task]:
    """Получить все задачи проекта."""
    query = session.query(Task).filter(Task.project_id == project_id)
    if completed_only:
        query = query.filter(Task.is_completed == True)
    return query.all()


def get_assigned_tasks(session: Session, user_id: int) -> list[Task]:
    """Получить все задачи, назначенные пользователю."""
    return (
        session.query(Task)
        .filter(Task.assigned_to_id == user_id, Task.is_completed == False)
        .all()
    )


def complete_task(session: Session, task_id: int) -> Task:
    """Отметить задачу как выполненную."""
    task = get_task(session, task_id)
    if task:
        task.is_completed = True
        session.commit()
        session.refresh(task)
    return task


def assign_task(
    session: Session,
    task_id: int,
    user_id: int,
) -> Task:
    """Назначить задачу пользователю."""
    task = get_task(session, task_id)
    if task:
        task.assigned_to_id = user_id
        session.commit()
        session.refresh(task)
    return task


def update_task(
    session: Session,
    task_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: datetime | None = None,
) -> Task:
    """Обновить задачу."""
    task = get_task(session, task_id)
    if task:
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if due_date is not None:
            task.due_date = due_date
        session.commit()
        session.refresh(task)
    return task


def delete_task(session: Session, task_id: int) -> bool:
    """Удалить задачу."""
    task = get_task(session, task_id)
    if task:
        session.delete(task)
        session.commit()
        return True
    return False