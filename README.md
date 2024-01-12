# Employee Task Management API

Employee Task Management API предоставляет серверное приложение для работы с базой данных
с задачами для сотрудников организации.

## Установка

1. Клонируйте репозиторий:

    ```bash
    git clone https://github.com/ваш-проект.git
    ```

2. Активируйте виртуальное окружение:

    ```bash
    source venv/bin/activate  # Для Unix/Mac
    venv\Scripts\activate  # Для Windows
    ```

3. Установите зависимости:

    ```bash
    pip install -r requirements.txt
    ```

4. Примените миграции для создания таблиц в базе данных:

    ```bash
    alembic upgrade head
    ```

5. Запустите FastAPI приложение:

    ```bash
    uvicorn main:app --reload
    ```


## Использование
1. Создание новой  родительской задачи:

Метод: POST


URL: http://127.0.0.1:8000/tasks/


Тело запроса:
```
{
  "name": "Название задачи",
  "deadline": "Срок выполнения",
  "status": "в ожидании",
  "description": "Описание задачи."
}

```
2. Назначение задачи сотруднику:

Метод: POST


URL: http://127.0.0.1:8000/assign_task/
Тело запроса:
```
{
  "task_id": <id задачи>,
  "employee_id": <id сотрудника>
}

```
3. Создание новой зависимой задачи:

Метод: POST


URL: http://127.0.0.1:8000/tasks/


Тело запроса:
```
{
  "name": "Название зависимой задачи",
  "parent_task_id": <id родительской задачи>,
  "deadline": "Срок выполнения",
  "status": "в ожидании",
  "description": "Описание."
}
```
4. Получение "Важных задач":

Метод: GET


URL: http://127.0.0.1:8000/important_tasks


5. Получение списка сотрудников с сортировкой по количеству задач:


Метод: GET


URL: http://127.0.0.1:8000/busy_employees