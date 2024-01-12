# app.py
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from database import engine, SessionLocal
from models import Base, Employee, Task

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Employees_tasks_tracker",
    description="This application allows you to create tasks for employees, assign performers and define important "
                "tasks with the employee recommended for completion",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)

# Новый роутер для очистки
router = APIRouter()


@app.get("/items/", summary="Get a list of items", response_model=list)
async def read_items(skip: int = 0, limit: int = 10):
    # Your logic to retrieve items goes here
    items = [{"item_id": i, "item_name": f"Item {i}"} for i in range(skip, skip + limit)]
    return items


# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.delete("/cleanup")
def cleanup_tasks(db: Session = Depends(get_db)):
    # Удаление задач с определенным статусом (например, "completed")
    db.query(Task).filter(Task.status == "completed").delete()

    # Удаление всех связанных задач перед удалением сотрудников
    db.query(Task).delete()

    # Удаление всех сотрудников
    db.query(Employee).delete()

    db.commit()
    return {"message": "Очистка выполнена"}


app.include_router(router)


class EmployeeModel(BaseModel):
    name: str
    position: str


class TaskModel(BaseModel):
    name: str
    parent_task_id: Optional[int] = None
    executor_id: Optional[int] = None
    deadline: datetime
    status: str
    description: Optional[str] = None


class AssignedTask(BaseModel):
    employee_id: int
    task_id: int


class EmployeeWithTasks(EmployeeModel):
    tasks: List[TaskModel]  # Добавляем поле для хранения задач


class ImportantTaskResponse(BaseModel):
    name: str
    deadline: str
    assigned_employees: List[str]


# Операции CRUD для сотрудников
@app.post("/employees/", response_model=EmployeeModel)
def create_employee(employee: EmployeeModel, db: Session = Depends(get_db)):
    db_employee = Employee(**employee.dict())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee


@app.get("/employees/", response_model=List[EmployeeModel])
def get_employees(db: Session = Depends(get_db)):
    return db.query(Employee).all()


@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    db.query(Employee).filter(Employee.id == employee_id).delete()
    db.commit()
    return {"message": "Сотрудник удален"}


# Операции CRUD для задач
@app.post("/tasks/", response_model=TaskModel)
def create_task(task: TaskModel, db: Session = Depends(get_db)):
    db_task = Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.get("/tasks/", response_model=List[TaskModel])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db.query(Task).filter(Task.id == task_id).delete()
    db.commit()
    return {"message": "Задача удалена"}


# Эндпоинт для "Важных задач"
@app.get("/important_tasks/", response_model=List[ImportantTaskResponse])
def important_tasks(db: Session = Depends(get_db)):
    # Найти родительскую задачу без исполнителя
    parent_task = (
        db.query(Task)
        .filter(Task.parent_task_id.is_(None), Task.executor_id.is_(None), Task.status != "в работе")
        .first()
    )

    if not parent_task:
        raise HTTPException(status_code=404, detail="Родительская задача не найдена")

    # Найти сотрудников, отсортированных по возрастанию количества задач
    employees = (
        db.query(Employee)
        .outerjoin(Employee.tasks)
        .group_by(Employee.id)
        .order_by(func.count(Task.id))
        .all()
    )

    # Выбрать наименее и более загруженных сотрудников
    least_busy_employee = employees[0]

    # Найти сотрудника, который уже выполняет родительскую задачу
    current_executor = (
        db.query(Employee)
        .join(Employee.tasks)
        .filter(Task.id == parent_task.id)
        .first()
    )

    if current_executor and len(current_executor.tasks) + 2 <= len(least_busy_employee.tasks):
        # Если текущий исполнитель удовлетворяет условиям, то оставляем его
        response = [
            ImportantTaskResponse(
                name=parent_task.name,
                deadline=str(parent_task.deadline),
                assigned_employees=[current_executor.name],
            )
        ]
    else:
        # В противном случае, выбираем наименее загруженного сотрудника
        response = [
            ImportantTaskResponse(
                name=parent_task.name,
                deadline=str(parent_task.deadline),
                assigned_employees=[least_busy_employee.name],
            )
        ]

    return response


# Endpoint для "Занятых сотрудников" с сортировкой по количеству задач
@app.get("/busy_employees", response_model=List[EmployeeWithTasks])
def busy_employees(db: Session = Depends(get_db)):
    # Используем joinedload для загрузки связанных данных о задачах
    busy_employees = (
        db.query(Employee)
        .options(joinedload(Employee.tasks))
        .group_by(Employee.id)
        .order_by(func.count().desc())
        .all()
    )

    if not busy_employees:
        raise HTTPException(status_code=404, detail="Нет занятых сотрудников")

    # Создаем список для занятых сотрудников с задачами
    employees_with_tasks = []
    for employee in sorted(busy_employees, key=lambda e: len(e.tasks), reverse=True):
        # Проверяем, занят ли сотрудник
        if employee.is_busy:
            tasks = [
                TaskModel(
                    id=task.id,
                    name=task.name,
                    parent_task_id=task.parent_task_id,
                    executor_id=task.executor_id,
                    deadline=task.deadline,
                    status=task.status,
                    description=task.description,
                )
                for task in employee.tasks
            ]
            employee_with_tasks = EmployeeWithTasks(
                id=employee.id,
                name=employee.name,
                position=employee.position,
                tasks=tasks,
            )
        employees_with_tasks.append(employee_with_tasks)
    return employees_with_tasks


# Endpoint для назначения исполнителя задаче
@app.post("/assign_task", response_model=str)
def assign_task(assign_data: AssignedTask, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == assign_data.employee_id).first()
    task = db.query(Task).filter(Task.id == assign_data.task_id).first()

    if not employee or not task:
        raise HTTPException(status_code=404, detail="Сотрудник или задача не найдены")

    if task.status == "в работе":
        raise HTTPException(status_code=400, detail="Задача уже в работе")

    # Присвоение executor_id после назначения сотрудника
    task.executor_id = employee.id
    task.status = "в работе"
    db.commit()

    # Обновление is_busy у сотрудника
    employee.is_busy = True
    db.commit()

    # Формирование строки с сообщением
    assigned_task_message = f'У задачи "{task.name}" назначен исполнитель "{employee.name}"'
    return assigned_task_message
