# app.py
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, aliased
from typing import List

import crud
import models
from database import engine
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
@app.post("/employees/", response_model=models.EmployeeModel)
def create_employee_handler(employee: models.EmployeeModel, db: Session = Depends(get_db)):
    created_employee = crud.create_employee(db, employee.dict())
    if created_employee is None:
        raise HTTPException(status_code=500, detail="Failed to create employee")

    return models.EmployeeModel(
        id=str(created_employee.id),
        name=created_employee.name,
        position=created_employee.position
    )


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


@app.post("/tasks/", response_model=TaskModel)
def create_task_handler(task: TaskModel, db: Session = Depends(get_db)):
    task_data = task.dict()

    # Получаем id последней созданной задачи
    last_task = (
        db.query(Task)
        .order_by(Task.id.desc())
        .first()
    )

    # Проверяем, что parent_task_id не совпадает с id последней созданной задачи + 1
    if 'parent_task_id' in task_data and last_task and task_data['parent_task_id'] == last_task.id + 1:
        raise HTTPException(status_code=400, detail="Cannot assign task to itself")

    # Создаем новую задачу
    created_task = create_task(db, task_data)
    if created_task is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    return TaskModel(
        id=str(created_task.id),
        name=created_task.name,
        deadline=str(created_task.deadline),
        status=created_task.status,
        description=created_task.description,
        executor_id=created_task.executor_id,
        parent_task_id=created_task.parent_task_id,
    )


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
@app.get("/important_tasks/", response_model=List[models.ImportantTaskResponse])
def important_tasks(db: Session = Depends(get_db)):
    # Найти все родительские задачи без исполнителя
    parent_tasks = (
        db.query(models.Task)
        .filter(models.Task.parent_task_id.is_(None), models.Task.executor_id.is_(None),
                models.Task.status != "в работе")
        .all()
    )

    if not parent_tasks:
        raise HTTPException(status_code=404, detail="Родительские задачи не найдены")

    response = []

    for parent_task in parent_tasks:
        # Найти сотрудников, отсортированных по возрастанию количества задач
        employees = (
            db.query(models.Employee)
            .outerjoin(models.Employee.tasks)
            .group_by(models.Employee.id)
            .order_by(func.count(models.Task.id))
            .all()
        )

        # Найти сотрудника, который уже выполняет текущую родительскую задачу
        current_executor = (
            db.query(models.Employee)
            .join(models.Task, models.Task.executor_id == models.Employee.id)
            .first()
        )

        if current_executor is not None:
            if len(current_executor.tasks) - len(employees[0].tasks) > 2:
                current_executor = employees[0]
        else:
            current_executor = employees[0]

        # Назначаем текущего исполнителя для родительской задачи
        parent_task.executor_id = current_executor.id
        parent_task.status = "в работе"

        # Обновляем статус is_busy у сотрудника
        current_executor.is_busy = True

        db.commit()

        response.append(
            models.ImportantTaskResponse(
                name=parent_task.name,
                deadline=str(parent_task.deadline),
                assigned_employees=[current_executor.name],
            )
        )

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
            employees_with_tasks.append(employee_with_tasks)  # Переместить эту строку внутрь цикла

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
