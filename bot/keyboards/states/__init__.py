"""Импорт всех FSM состояний."""

from .flows import (
    RegistrationState,
    ProjectManagementState,
    AddExpenseState,
    PhotoReportState,
    ProjectReportState,
    SettingsState,
)

__all__ = [
    "RegistrationState",
    "ProjectManagementState",
    "AddExpenseState",
    "PhotoReportState",
    "ProjectReportState",
    "SettingsState",
]

