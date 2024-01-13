# app.py
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from database import engine, SessionLocal
from models import (Base, Employee, Task, EmployeeModel, TaskModel, AssignedTask, EmployeeWithTasks,
                    ImportantTaskResponse)
from crud import (create_employee, get_employees, delete_employee, create_task, get_tasks, delete_task,
                  get_employee_by_id, get_task_by_id, get_db)

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


# Операции CRUD для сотрудников
@app.post("/employees/", response_model=EmployeeModel)
def create_employee_handler(employee: EmployeeModel, db: Session = Depends(get_db)):
    return create_employee(db, employee.dict())


@app.get("/employees/", response_model=List[EmployeeModel])
def get_employees_handler(db: Session = Depends(get_db)):
    employees = get_employees(db)
    employee_models = [
        EmployeeModel(id=str(employee.id), name=employee.name, position=employee.position)
        for employee in employees
    ]
    return employee_models


@app.delete("/employees/{employee_id}")
def delete_employee_handler(employee_id: int, db: Session = Depends(get_db)):
    delete_employee(db, employee_id)
    return {"message": "Сотрудник удален"}


# Операции CRUD для задач
@app.post("/tasks/", response_model=TaskModel)
def create_task_handler(task: TaskModel, db: Session = Depends(get_db)):
    return create_task(db, task.dict())


@app.get("/tasks/", response_model=List[TaskModel])
def get_tasks_handler(db: Session = Depends(get_db)):
    tasks = get_tasks(db)
    task_models = [
        TaskModel(
            id=str(task.id),
            name=task.name,
            parent_task_id=task.parent_task_id,
            executor_id=task.executor_id,
            deadline=task.deadline,
            status=task.status,
            description=task.description,
        )
        for task in tasks
    ]

    return task_models


@app.delete("/tasks/{task_id}")
def delete_task_handler(task_id: int, db: Session = Depends(get_db)):
    delete_task(db, task_id)
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
                assigned_employees=[current_executor.name],
            )
        ]

    return response


@app.get("/busy_employees", response_model=List[EmployeeWithTasks])
def busy_employees(db: Session = Depends(get_db)):
    busy_employees = (
        db.query(Employee)
        .options(joinedload(Employee.tasks))
        .group_by(Employee.id)
        .order_by(func.count().desc())
        .all()
    )

    if not busy_employees:
        raise HTTPException(status_code=404, detail="Нет занятых сотрудников")

    employees_with_tasks = []
    for employee in sorted(busy_employees, key=lambda e: len(e.tasks), reverse=True):
        if employee.is_busy:
            tasks = [
                TaskModel(
                    id=str(task.id),
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
                id=str(employee.id),
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
