# mypy: ignore_missing_imports

from nicegui import ui
from typing import List, Dict, Any, Optional
import sqlite3
from project_tracker.config import DATABASE
import app.theme as theme

class EmployeeManager:
    def __init__(self) -> None:
        self.employee_name_input: Optional[ui.input] = None
        self.employees_container: Optional[ui.column] = None

    @staticmethod
    def init_employees() -> None:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS employees(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.commit()
        conn.close()

    @staticmethod
    def add_employee(name: str) -> None:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO employees(name) VALUES (?)", (name,))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_employee(emp_id: int) -> None:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def fetch_employees() -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM employees ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": row[0], "name": row[1]} for row in rows]

    def update_employees_table(self) -> None:
        assert self.employees_container is not None, "employees_container is not set"
        self.employees_container.clear()
        for emp in EmployeeManager.fetch_employees():
            with self.employees_container:
                with ui.row().classes("items-center q-pa-xs"):
                    ui.label(str(emp["id"]).strip()).classes("w-10")
                    ui.label(emp["name"]).classes("w-40")
                    ui.button("Delete", on_click=lambda e, emp_id=emp["id"]: self.delete_employee_and_update(emp_id)).classes("bg-red text-white q-ml-md")

    def delete_employee_and_update(self, emp_id: int) -> None:
        EmployeeManager.delete_employee(emp_id)
        self.update_employees_table()

    def add_employee_and_update(self, name: str) -> None:
        if name:
            EmployeeManager.add_employee(name)
            if self.employee_name_input is not None:
                self.employee_name_input.value = ""
            self.update_employees_table()

    def create_ui(self) -> None:
        with theme.frame("Employee Management"):
            ui.label("Employee Management").classes("text-h3 q-pa-md")
            with ui.card().classes("q-pa-md q-mt-md"):
                ui.label("Manage Employees").classes("text-h6")
                self.employee_name_input = ui.input("New Employee Name")
                assert self.employee_name_input is not None, "employee_name_input must be set"
                temp_input = self.employee_name_input
                ui.button("Add Employee", on_click=lambda e: self.add_employee_and_update(temp_input.value)).classes("q-mt-md")
                with ui.column() as container:
                    self.employees_container = container
                self.update_employees_table()


def employee_management_page() -> None:
    manager = EmployeeManager()
    manager.create_ui()