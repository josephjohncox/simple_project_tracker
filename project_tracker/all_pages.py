from nicegui import ui
from project_tracker.project_tracker import project_tracker_page
from project_tracker.employee_management import employee_management_page

def create() -> None:
    ui.page('/')(project_tracker_page)
    ui.page('/employee-management/')(employee_management_page)

if __name__ == '__main__':
    create()