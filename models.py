# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


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
