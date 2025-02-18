from nicegui import ui
from project_tracker.project_tracker import status_updates_page, project_list_page
from project_tracker.employee_management import employee_management_page

def create() -> None:
    ui.page('/')(status_updates_page)
    ui.page('/status-updates/')(status_updates_page)
    ui.page('/projects/')(project_list_page)
    ui.page('/employee-management/')(employee_management_page)

if __name__ == '__main__':
    create()