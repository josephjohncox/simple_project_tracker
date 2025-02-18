# mypy: ignore_missing_imports
import datetime
from typing import List, Dict, Any, cast
from collections import defaultdict
import project_tracker.theme as theme
import pandas as pd
import plotly.express as px  # type: ignore
from project_tracker.employee_management import EmployeeManager
from nicegui import ui
from project_tracker.db import get_connection, init_db

# Create a new project
def add_project(project_name: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects(name) VALUES (?)", (project_name,))
    conn.commit()
    conn.close()

def fetch_projects() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM projects")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1]} for row in rows]

def get_project_id(project_name: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else -1

# Fetch only projects that do not have a "Done" log entry
def fetch_not_done_projects() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name FROM projects WHERE id NOT IN (SELECT project_id FROM project_status WHERE status = 'Done')"
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1]} for row in rows]

# Add a new project log entry using projected end date
def add_log(employee: str, project_id: int, status: str, projected_end_date: datetime.date) -> None:
    now: str = datetime.datetime.now().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO project_status(employee, project_id, status, commit_time, projected_end_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (employee, project_id, status, now, projected_end_date.isoformat()),
    )
    conn.commit()
    conn.close()

# Delete a project log entry by id
def delete_log(log_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_status WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

# Fetch all project log entries
def fetch_all_logs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT project_status.id, employee, projects.name, status, commit_time, projected_end_date 
        FROM project_status 
        JOIN projects ON project_status.project_id = projects.id 
        ORDER BY commit_time ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    logs: List[Dict[str, Any]] = []
    for row in rows:
        logs.append({
                "id": row[0],
                "employee": row[1],
                "project_name": row[2],
                "status": row[3],
                "commit_time": row[4],
                "projected_end_date": row[5],
            })
    return logs

# Compute summary for completed projects (where status is 'Done') by computing durations in hours
def compute_summary(logs: List[Dict[str, Any]]) -> str:
    project_groups: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for log in logs:
        key = (log["employee"], log["project_name"])
        project_groups[key].append(log)
    
    summary_lines: List[str] = []
    for (employee, project), records in project_groups.items():
        done_records = [r for r in records if r["status"] == "Done"]
        if done_records:
            start = min(datetime.datetime.fromisoformat(r["commit_time"]) for r in records)
            finish = max(datetime.datetime.fromisoformat(r["commit_time"]) for r in done_records)
            actual_duration = (finish - start).total_seconds() / 3600.0

            # Compute projected duration as hours from start to the projected end date.
            projected_date = datetime.date.fromisoformat(records[0]["projected_end_date"])
            projected_dt = datetime.datetime.combine(projected_date, datetime.time.min)
            projected_duration = (projected_dt - start).total_seconds() / 3600.0

            line = (
                f"Employee: {employee}, Project: {project}, "
                f"Projected: {projected_duration:.2f} hrs, Actual: {actual_duration:.2f} hrs"
            )
            summary_lines.append(line)
    return "\n".join(summary_lines) if summary_lines else "No completed projects yet."

# Helper function to decorate status with icons
def decorate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    icon = {
        "Blocked": "⛔",
        "At Risk": "⚠️",
        "Off Track": "🚫",
        "Not Started": "⏸",
        "In Progress": "🔄",
        "Canceled": "❌",
        "Done": "✅",
    }.get(record["status"], "")
    record["status"] = f"{icon} {record['status']}"
    return record

# Helper function to get the start date from a Pandas Period representing a week
def get_period_start_date(period: pd.Period) -> datetime.date:
    return period.start_time.date()

# Create a Plotly bar chart of commits per week by status (aggregated by commit week)
def create_status_graph() -> Any:
    logs = fetch_all_logs()
    if logs:
        df = pd.DataFrame(logs)
        df["commit_dt"] = pd.to_datetime(df["commit_time"], errors="raise")  # type: ignore
        period_series = df["commit_dt"].dt.to_period("W")
        df["commit_week"] = period_series.apply(get_period_start_date)  # type: ignore
        grouped = df.groupby(["commit_week", "status"], as_index=False).agg(count=("status", "size"))  # type: ignore
        fig = px.bar(
            grouped,
            x="commit_week",
            y="count",
            color="status",
            barmode="group",
            title="Commits per Week by Status"  # type: ignore
        )  # type: ignore
        fig.update_xaxes(title="Commit Week")  # type: ignore
        fig.update_yaxes(title="Count")  # type: ignore
        return fig
    else:
        return px.bar()  # type: ignore

# Create a Plotly scatter plot comparing actual vs. projected durations for completed projects
def create_time_vs_projected_graph() -> Any:
    logs = fetch_all_logs()
    groups: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for log in logs:
        key = (log["employee"], log["project_name"])
        groups[key].append(log)
    records = []
    for (employee, project), recs in groups.items():
        done_recs = [r for r in recs if r["status"] == "Done"]
        if done_recs:
            start = min(datetime.datetime.fromisoformat(str(r["commit_time"])) for r in recs)
            finish = max(datetime.datetime.fromisoformat(str(r["commit_time"])) for r in done_recs)
            actual_duration = (finish - start).total_seconds() / 3600.0

            # Compute projected duration from projected_end_date (difference from start)
            projected_date = datetime.date.fromisoformat(recs[0]["projected_end_date"])
            projected_dt = datetime.datetime.combine(projected_date, datetime.time.min)
            projected_duration = (projected_dt - start).total_seconds() / 3600.0

            records.append({
                "employee": employee,
                "project": project,
                "actual_duration": actual_duration,
                "projected_duration": projected_duration,
            })  # type: ignore
    scatter_func: Any = px.scatter  # type: ignore
    if records:
        df = pd.DataFrame(records)
        fig = scatter_func(
            df,
            x="projected_duration",
            y="actual_duration",
            color="employee",
            hover_data=["project"],  # type: ignore
            labels={
                "projected_duration": "Projected Duration (hrs)",
                "actual_duration": "Actual Duration (hrs)"
            },
        )  # type: ignore
        # Add an ideal line y = x
        fig.add_scatter(
            x=df["projected_duration"],
            y=df["projected_duration"],
            mode="lines",
            line=dict(dash="dash"),
            name="Ideal",
        )  # type: ignore
        fig.update_xaxes(title="Projected Duration (hrs)")  # type: ignore
        fig.update_yaxes(title="Actual Duration (hrs)")  # type: ignore
        return fig
    else:
        return scatter_func()  # type: ignore

# Create an HTML table of weekly commit statuses
def create_commit_table() -> str:
    logs = fetch_all_logs()
    employees = [emp["name"] for emp in EmployeeManager.fetch_employees()]
    week_list: List[datetime.date] = []
    if logs:
        df = pd.DataFrame(logs)
        df["commit_dt"] = pd.to_datetime(df["commit_time"], errors="raise")  # type: ignore
        period_series = df["commit_dt"].dt.to_period("W")
        df["commit_week"] = period_series.apply(get_period_start_date)  # type: ignore
        start_week: datetime.date = pd.to_datetime(df["commit_week"].min()).date()  # type: ignore
        end_week: datetime.date = pd.to_datetime(df["commit_week"].max()).date()  # type: ignore
        current: datetime.date = cast(datetime.date, start_week)
        while current <= end_week:
            week_list.append(current)  # type: ignore
            current += datetime.timedelta(days=7)
    else:
        today = datetime.date.today()
        week_list = [today]

    # Build dictionary mapping (employee, week) to list of statuses
    status_by_emp_week: Dict[tuple[str, datetime.date], List[str]] = {}
    if logs:
        for _, row in df.iterrows():  # type: ignore
            employee_val: str = str(row["employee"])
            commit_week_val: datetime.date = pd.to_datetime(row["commit_week"]).date()  # type: ignore
            key: tuple[str, datetime.date] = (employee_val, commit_week_val)
            status_by_emp_week.setdefault(key, []).append(row["status"])  # type: ignore

    def determine_color(statuses: List[str]) -> str:
        if any(s in {"Blocked", "At Risk"} for s in statuses):
            return "red"
        elif any(s == "Off Track" for s in statuses):
            return "yellow"
        elif statuses and all(s in {"In Progress", "Done"} for s in statuses):
            return "green"
        else:
            return "white"

    # Build HTML table
    html = '<table style="border-collapse: collapse;">'
    html += '<tr><th style="border: 1px solid #ccc; padding: 4px;">Employee</th>'
    for week in week_list:
        html += f'<th style="border: 1px solid #ccc; padding: 4px;">{week.strftime("%Y-%m-%d")}</th>'
    html += '</tr>'

    for emp in employees:
        html += f'<tr><td style="border: 1px solid #ccc; padding: 4px;">{emp}</td>'
        for week in week_list:
            statuses = status_by_emp_week.get((emp, week), [])
            color = determine_color(statuses) if statuses else "lightgrey"
            html += f'<td style="border: 1px solid #ccc; padding: 4px; text-align: center;">'
            html += f'<div style="width: 20px; height: 20px; background-color: {color};"></div></td>'
        html += '</tr>'
    html += '</table>'
    return html

# Create a new function to build an HTML table of all projects
def create_project_table() -> str:
    """
    Build an HTML table listing all projects.
    """
    projects = fetch_projects()
    if not projects:
        return "<p>No projects available</p>"
    html = '<table style="border-collapse: collapse;">'
    html += (
        '<tr>'
        '<th style="border: 1px solid #ccc; padding: 4px;">ID</th>'
        '<th style="border: 1px solid #ccc; padding: 4px;">Project Name</th>'
        '</tr>'
    )
    for proj in projects:
        html += (
            f'<tr>'
            f'<td style="border: 1px solid #ccc; padding: 4px;">{proj["id"]}</td>'
            f'<td style="border: 1px solid #ccc; padding: 4px;">{proj["name"]}</td>'
            f'</tr>'
        )
    html += '</table>'
    return html

# --- Class-based UI ---

class ProjectTracker:
    def __init__(self) -> None:
        self.employee_select: Any = None
        self.project_select: Any = None
        self.status_select: Any = None
        self.projected_end_date_input: Any = None
        self.new_project_input: Any = None

        self.status_graph: Any = None
        self.time_graph: Any = None
        self.summary_label: Any = None
        self.commit_table: Any = None
        self.logs_container: Any = None
        self.project_table: Any = None

    @staticmethod
    def init_db() -> None:
        init_db()

    def update_employee_select(self) -> None:
        options = [emp["name"] for emp in EmployeeManager.fetch_employees()]
        if self.employee_select:
            self.employee_select.options = options
            self.employee_select.update()

    def update_project_select(self) -> None:
        if self.project_select:
            self.project_select.options = [p["name"] for p in fetch_not_done_projects()]
            self.project_select.update()

    def submit_log(self) -> None:
        assert self.employee_select is not None, "employee_select is not set"
        assert self.project_select is not None, "project_select is not set"
        assert self.status_select is not None, "status_select is not set"
        assert self.projected_end_date_input is not None, "projected_end_date_input is not set"

        emp: str = self.employee_select.value
        project_name: str = self.project_select.value
        stat: str = self.status_select.value
        try:
            proj_end_date: datetime.date = datetime.date.fromisoformat(self.projected_end_date_input.value)
        except Exception:
            ui.notify("Invalid projected end date", color="error")
            return

        proj_obj = next((p for p in fetch_not_done_projects() if p["name"] == project_name), None)
        if emp and project_name and proj_obj is not None:
            add_log(emp, proj_obj["id"], stat, proj_end_date)
            self.update_ui()
            self.update_project_select()
        else:
            ui.notify("Invalid log submission", color="warning")

    def submit_new_project(self) -> None:
        if self.new_project_input and self.new_project_input.value:
            add_project(self.new_project_input.value)
            self.new_project_input.value = ""
            ui.notify("Project created successfully", color="positive")
            self.update_project_select()
            self.update_project_table()
        else:
            ui.notify("Please enter a project name", color="warning")

    def update_commit_table(self) -> None:
        if self.commit_table:
            self.commit_table.content = create_commit_table()

    def update_project_table(self) -> None:
        if self.project_table:
            self.project_table.rows = fetch_projects()

    def update_summary(self) -> None:
        logs = fetch_all_logs()
        summary = compute_summary(logs)
        if self.summary_label:
            self.summary_label.content = summary

    def update_logs_table(self) -> None:
        if self.logs_container:
            self.logs_container.clear()
            logs = fetch_all_logs()
            with self.logs_container:
                for rec in logs:
                    drec = decorate_record(rec.copy())
                    with ui.row().classes("items-center q-pa-xs"):
                        ui.label(str(drec["id"])).classes("w-10")
                        ui.label(drec["employee"]).classes("w-20")
                        ui.label(drec["project_name"]).classes("w-40")
                        ui.label(drec["status"]).classes("w-30")
                        ui.label(drec["commit_time"]).classes("w-60")
                        ui.label(drec["projected_end_date"]).classes("w-20")
                        ui.button(
                            "Delete",
                            on_click=lambda e, rec_id=drec["id"]: self.delete_and_update(rec_id)
                        ).classes("bg-red text-white q-ml-md")

    def delete_and_update(self, rec_id: int) -> None:
        delete_log(rec_id)
        self.update_ui()

    def update_graphs(self) -> None:
        if self.status_graph:
            self.status_graph.figure = create_status_graph()
        if self.time_graph:
            self.time_graph.figure = create_time_vs_projected_graph()
        self.update_commit_table()

    def update_ui(self) -> None:
        self.update_graphs()
        self.update_summary()
        self.update_logs_table()
        self.update_project_table()

    def create_ui(self) -> None:
        with theme.frame("Project Tracker"):
            ui.label("Project Tracker").classes("text-h3 q-pa-md")
            with ui.row():
                with ui.column():
                    # --- Project Input Section ---
                    with ui.card().classes("q-pa-md"):
                        ui.label("Add New Log Entry").classes("text-h6")
                        self.employee_select = ui.select(
                            options=[emp["name"] for emp in EmployeeManager.fetch_employees()],
                            label="Employee",
                        )
                        self.project_select = ui.select(
                            options=[p["name"] for p in fetch_not_done_projects()],
                            label="Project",
                        )
                        self.status_select = ui.select(
                            options=["Blocked", "At Risk", "Off Track", "Not Started", "In Progress", "Canceled", "Done"],
                            value="Not Started",
                            label="Status",
                        )
                        self.projected_end_date_input = ui.date(datetime.date.today())
                        ui.button("Submit Log", on_click=self.submit_log).classes("q-mt-md")
                    with ui.card().classes("q-pa-md q-mt-md"):
                        ui.label("Create New Project").classes("text-h6")
                        self.new_project_input = ui.input("Project Name")
                        ui.button("Create Project", on_click=self.submit_new_project).classes("q-mt-md")
                    with ui.card().classes("q-pa-md q-mt-md"):
                        ui.label("Projects List").classes("text-h6")
                        self.project_table = ui.table(
                            rows=fetch_projects(),
                            columns=[
                                {"name": "id", "label": "ID", "field": "id", "align": "left"},
                                {"name": "name", "label": "Project Name", "field": "name", "align": "left"},
                            ],
                        ).classes("q-mt-md")
                with ui.column():
                    # --- Plots and Tables Section ---
                    with ui.card().classes("q-pa-md"):
                        ui.label("Project Results").classes("text-h6")
                        self.status_graph = ui.plotly(create_status_graph()).classes("q-mt-md")
                        self.time_graph = ui.plotly(create_time_vs_projected_graph()).classes("q-mt-md")
                        self.summary_label = ui.markdown("").classes("q-mt-md")
                    with ui.card().classes("q-pa-md q-mt-md"):
                        ui.label("Commit Table").classes("text-h6")
                        self.commit_table = ui.html(create_commit_table()).classes("q-mt-md")
                    with ui.card().classes("q-pa-md q-mt-md"):
                        ui.label("Project Logs").classes("text-h6")
                        self.logs_container = ui.column().classes("q-mt-md")
                        self.update_logs_table()

# Removed unified page; now splitting into two pages below.

def status_updates_page() -> None:
    tracker = ProjectTracker()
    ProjectTracker.init_db()
    with theme.frame("Project Tracker - Status Updates"):
        ui.label("Project Status Updates").classes("text-h3 q-pa-md")
        with ui.row():
            with ui.column():
                with ui.card().classes("q-pa-md"):
                    ui.label("Add New Log Entry").classes("text-h6")
                    tracker.employee_select = ui.select(
                        options=[emp["name"] for emp in EmployeeManager.fetch_employees()],
                        label="Employee"
                    )
                    tracker.project_select = ui.select(
                        options=[p["name"] for p in fetch_not_done_projects()],
                        label="Project"
                    )
                    tracker.status_select = ui.select(
                        options=["Blocked", "At Risk", "Off Track", "Not Started", "In Progress", "Canceled", "Done"],
                        value="Not Started",
                        label="Status"
                    )
                    tracker.projected_end_date_input = ui.date(datetime.date.today().isoformat())
                    ui.button("Submit Log", on_click=tracker.submit_log).classes("q-mt-md")
            with ui.column():
                with ui.card().classes("q-pa-md"):
                    ui.label("Project Results").classes("text-h6")
                    tracker.status_graph = ui.plotly(create_status_graph()).classes("q-mt-md")
                    tracker.time_graph = ui.plotly(create_time_vs_projected_graph()).classes("q-mt-md")
                    tracker.summary_label = ui.markdown("").classes("q-mt-md")
                with ui.card().classes("q-pa-md q-mt-md"):
                    ui.label("Commit Table").classes("text-h6")
                    tracker.commit_table = ui.html(create_commit_table()).classes("q-mt-md")
                with ui.card().classes("q-pa-md q-mt-md"):
                    ui.label("Project Logs").classes("text-h6")
                    tracker.logs_container = ui.column().classes("q-mt-md")
                    tracker.update_logs_table()

def project_list_page() -> None:
    tracker = ProjectTracker()
    ProjectTracker.init_db()
    with theme.frame("Project Tracker - Projects List"):
        ui.label("Projects List").classes("text-h3 q-pa-md")
        with ui.card().classes("q-pa-md"):
            ui.label("Create New Project").classes("text-h6")
            tracker.new_project_input = ui.input("Project Name")
            ui.button("Create Project", on_click=tracker.submit_new_project).classes("q-mt-md")
        with ui.card().classes("q-pa-md q-mt-md"):
            ui.label("Projects List").classes("text-h6")
            tracker.project_table = ui.table(
                rows=fetch_projects(),
                columns=[
                    {"name": "id", "label": "ID", "field": "id", "align": "left"},
                    {"name": "name", "label": "Project Name", "field": "name", "align": "left"},
                ],
            ).classes("q-mt-md")

