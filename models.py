# models.py
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, MetaData
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base(metadata=MetaData())


class EmployeeModel(BaseModel):
    id: Optional[str] = None
    name: str
    position: str


class TaskModel(BaseModel):
    id: Optional[str] = None
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


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    parent_task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    executor_id = Column(Integer, ForeignKey('employees.id'))
    deadline = Column(DateTime)
    status = Column(String)
    description = Column(String)
    executor = relationship("Employee", back_populates="tasks")
    subtasks = relationship("Task", back_populates="parent_task", remote_side=[id])
    parent_task = relationship("Task", back_populates="subtasks", foreign_keys=[parent_task_id])


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    position = Column(String)
    is_busy = Column(Boolean, default=False)
    tasks = relationship("Task", back_populates="executor")
