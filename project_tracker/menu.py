from nicegui import ui


def menu() -> None:
    ui.link('Tracker', '/').classes(replace='text-black')
    ui.link('Employee Management', '/employee-management/').classes(replace='text-black')
    ui.link('Projects', '/projects/').classes(replace='text-black')