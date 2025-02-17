import threading

# Import DB initialization functions from our modules
from project_tracker.project_tracker import project_tracker_page
from project_tracker.employee_management import EmployeeManager

# Initialize the database and employees in separate threads
db_thread = threading.Thread(target=EmployeeManager.init_employees)
emp_thread = threading.Thread(target=EmployeeManager.init_employees)
db_thread.start()
emp_thread.start()
db_thread.join()
emp_thread.join()

import project_tracker.all_pages as all_pages
import project_tracker.theme as theme
from nicegui import ui


# # here we use our custom page decorator directly and just put the content creation into a separate function
# @ui.page('/')
# def index_page() -> None:
#     with theme.frame('Project Tracker'):
#         project_tracker_page()


# this call shows that you can also move the whole page creation into a separate file
all_pages.create()


ui.run(title='Project Tracker')