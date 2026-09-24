from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    total_projects: int
    total_sanction_amount: float
    total_expenditure: float
    high_risk_projects: int
    critical_projects: int
    active_alerts: int


class AlertItem(BaseModel):
    id: int
    project_id: Optional[int] = None
    alert_type: str
    severity: str
    title: str
    message: str
    project_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None


class ProjectDetail(BaseModel):
    id: int
    project_name: Optional[str]
    state: Optional[str]
    district: Optional[str]
    sanction_amount: Optional[float]
    expenditure: Optional[float]
    utilization_ratio: Optional[float]
    anomaly_score: Optional[float]
    final_risk_score: Optional[float]
    risk_level: Optional[str]
    status: Optional[str]
    reasons: List[str] = []
    alerts: List[str] = []


class DatasetUploadRequest(BaseModel):
    file_names: List[str] = Field(default_factory=list)
    mapping: Dict[str, str] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    code: str
    message: str
    suggested_mappings: Dict[str, str] = Field(default_factory=dict)


class ValidationResponse(BaseModel):
    valid: bool
    missing_fields: List[str] = Field(default_factory=list)
    issues: List[ValidationIssue] = Field(default_factory=list)
    suggested_mappings: Dict[str, str] = Field(default_factory=dict)
    detected_columns: List[str] = Field(default_factory=list)


class AuditCaseCreate(BaseModel):
    project_id: int
    title: str
    priority: str = 'MEDIUM'
    status: str = 'Pending Review'
    notes: Optional[str] = None


class AuditCaseOut(BaseModel):
    id: int
    project_id: int
    title: str
    priority: str
    status: str
    notes: Optional[str]
