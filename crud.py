# crud.py
from sqlalchemy.orm import Session
from models import Employee, Task

from sqlalchemy.orm import Session
from database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_employee(db: Session, employee_data):
    db_employee = Employee(**employee_data)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee


def get_employees(db: Session):
    return db.query(Employee).all()


def delete_employee(db: Session, employee_id):
    db.query(Employee).filter(Employee.id == employee_id).delete()
    db.commit()


def create_task(db: Session, task_data):
    db_task = Task(**task_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_tasks(db: Session):
    return db.query(Task).all()


def delete_task(db: Session, task_id):
    db.query(Task).filter(Task.id == task_id).delete()
    db.commit()


def get_employee_by_id(db: Session, employee_id: int):
    return db.query(Employee).filter(Employee.id == employee_id).first()


def get_task_by_id(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id).first()
