"""Database models and utilities for marketing automation tracking"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import json
from enum import Enum
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
    Numeric,
    Index,
    func,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import case

Base = declarative_base()


class TaskType(str, Enum):
    """Types of automation tasks"""

    CAMPAIGN_CREATION = "campaign_creation"
    BUDGET_OPTIMIZATION = "budget_optimization"
    AD_COPY_GENERATION = "ad_copy_generation"
    AUDIENCE_SEGMENTATION = "audience_segmentation"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    REPORT_GENERATION = "report_generation"
    EMAIL_CAMPAIGN = "email_campaign"
    A_B_TESTING = "a_b_testing"


class TaskStatus(str, Enum):
    """Status of automation tasks"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DecisionType(str, Enum):
    """Types of AI decisions"""

    BUDGET_ALLOCATION = "budget_allocation"
    BID_ADJUSTMENT = "bid_adjustment"
    AUDIENCE_TARGETING = "audience_targeting"
    CREATIVE_SELECTION = "creative_selection"
    CAMPAIGN_OPTIMIZATION = "campaign_optimization"


class Campaign(Base):
    """Campaign model to track marketing campaigns"""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)  # google_ads, facebook_ads, etc.
    status = Column(String(50), default="active")
    budget = Column(Numeric(10, 2), default=0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    automation_tasks = relationship("AutomationTask", back_populates="campaign")
    performance_metrics = relationship("PerformanceMetrics", back_populates="campaign")
    roi_tracking = relationship("ROITracking", back_populates="campaign")
    ai_decisions = relationship("AIDecisionHistory", back_populates="campaign")

    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign to dictionary"""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "name": self.name,
            "platform": self.platform,
            "status": self.status,
            "budget": float(self.budget) if self.budget else 0,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AutomationTask(Base):
    """Track individual automation tasks and their efficiency"""

    __tablename__ = "automation_tasks"

    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    task_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)

    # Foreign keys
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))

    # Time tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    manual_duration_minutes = Column(Float, default=0)  # Estimated manual time
    automated_duration_seconds = Column(Float, default=0)  # Actual automated time

    # Cost tracking
    hourly_rate = Column(Numeric(10, 2), default=50.00)  # Default $50/hour
    manual_cost = Column(Numeric(10, 2), default=0)
    automated_cost = Column(Numeric(10, 2), default=0)

    # Results
    result_data = Column(JSON)
    error_message = Column(Text)
    items_processed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="automation_tasks")

    @hybrid_property
    def time_saved_minutes(self) -> float:
        """Calculate time saved in minutes"""
        if self.manual_duration_minutes and self.automated_duration_seconds:
            return self.manual_duration_minutes - (self.automated_duration_seconds / 60)
        return 0

    @hybrid_property
    def cost_saved(self) -> Decimal:
        """Calculate cost saved"""
        if self.manual_cost and self.automated_cost:
            return self.manual_cost - self.automated_cost
        return Decimal("0")

    @hybrid_property
    def efficiency_gain_percentage(self) -> float:
        """Calculate efficiency gain as percentage"""
        if self.manual_duration_minutes > 0:
            automated_minutes = self.automated_duration_seconds / 60
            return (
                (self.manual_duration_minutes - automated_minutes)
                / self.manual_duration_minutes
            ) * 100
        return 0

    def calculate_savings(
        self, hourly_rate: Optional[float] = None
    ) -> Tuple[float, Decimal]:
        """
        Calculate time and cost savings
        Returns: (time_saved_minutes, cost_saved)
        """
        if hourly_rate:
            self.hourly_rate = Decimal(str(hourly_rate))

        # Calculate manual cost
        self.manual_cost = (
            Decimal(str(self.manual_duration_minutes)) / 60
        ) * self.hourly_rate

        # Calculate automated cost (assuming 10% of hourly rate for automation overhead)
        automation_overhead_rate = self.hourly_rate * Decimal("0.1")
        self.automated_cost = (
            Decimal(str(self.automated_duration_seconds)) / 3600
        ) * automation_overhead_rate

        time_saved = self.time_saved_minutes
        cost_saved = self.cost_saved

        return time_saved, cost_saved

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_type": self.task_type.value if self.task_type else None,
            "task_name": self.task_name,
            "status": self.status.value if self.status else None,
            "campaign_id": self.campaign_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "manual_duration_minutes": self.manual_duration_minutes,
            "automated_duration_seconds": self.automated_duration_seconds,
            "time_saved_minutes": self.time_saved_minutes,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate else 0,
            "manual_cost": float(self.manual_cost) if self.manual_cost else 0,
            "automated_cost": float(self.automated_cost) if self.automated_cost else 0,
            "cost_saved": float(self.cost_saved) if self.cost_saved else 0,
            "efficiency_gain_percentage": self.efficiency_gain_percentage,
            "items_processed": self.items_processed,
            "result_data": self.result_data,
            "error_message": self.error_message,
        }


class PerformanceMetrics(Base):
    """Track performance improvements from automation"""

    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True)
    metric_id = Column(String(100), unique=True, nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    metric_date = Column(DateTime, nullable=False, index=True)

    # Performance metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(Numeric(10, 2), default=0)
    cost = Column(Numeric(10, 2), default=0)

    # Calculated metrics
    ctr = Column(Float, default=0)  # Click-through rate
    conversion_rate = Column(Float, default=0)
    cpc = Column(Numeric(10, 2), default=0)  # Cost per click
    cpa = Column(Numeric(10, 2), default=0)  # Cost per acquisition
    roas = Column(Float, default=0)  # Return on ad spend

    # Automation impact
    is_automated = Column(Boolean, default=False)
    automation_applied = Column(JSON)  # List of automation types applied
    baseline_ctr = Column(Float)  # CTR before automation
    baseline_conversion_rate = Column(Float)  # Conversion rate before automation

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="performance_metrics")

    # Indexes for common queries
    __table_args__ = (Index("idx_campaign_date", "campaign_id", "metric_date"),)

    @hybrid_property
    def ctr_improvement(self) -> float:
        """Calculate CTR improvement percentage"""
        if self.baseline_ctr and self.baseline_ctr > 0:
            return ((self.ctr - self.baseline_ctr) / self.baseline_ctr) * 100
        return 0

    @hybrid_property
    def conversion_improvement(self) -> float:
        """Calculate conversion rate improvement percentage"""
        if self.baseline_conversion_rate and self.baseline_conversion_rate > 0:
            return (
                (self.conversion_rate - self.baseline_conversion_rate)
                / self.baseline_conversion_rate
            ) * 100
        return 0

    def calculate_metrics(self):
        """Calculate derived metrics"""
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100

        if self.clicks > 0:
            self.conversion_rate = (self.conversions / self.clicks) * 100
            self.cpc = self.cost / self.clicks

        if self.conversions > 0:
            self.cpa = self.cost / self.conversions

        if self.cost > 0:
            self.roas = float(self.revenue) / float(self.cost)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "id": self.id,
            "metric_id": self.metric_id,
            "campaign_id": self.campaign_id,
            "metric_date": self.metric_date.isoformat(),
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "revenue": float(self.revenue) if self.revenue else 0,
            "cost": float(self.cost) if self.cost else 0,
            "ctr": self.ctr,
            "conversion_rate": self.conversion_rate,
            "cpc": float(self.cpc) if self.cpc else 0,
            "cpa": float(self.cpa) if self.cpa else 0,
            "roas": self.roas,
            "is_automated": self.is_automated,
            "automation_applied": self.automation_applied,
            "ctr_improvement": self.ctr_improvement,
            "conversion_improvement": self.conversion_improvement,
        }


class ROITracking(Base):
    """Track ROI and cost savings from automation"""

    __tablename__ = "roi_tracking"

    id = Column(Integer, primary_key=True)
    roi_id = Column(String(100), unique=True, nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    tracking_period = Column(String(50))  # daily, weekly, monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Time savings
    total_time_saved_hours = Column(Float, default=0)
    tasks_automated = Column(Integer, default=0)

    # Cost savings
    labor_cost_saved = Column(Numeric(10, 2), default=0)
    performance_value_added = Column(
        Numeric(10, 2), default=0
    )  # Value from improved performance
    total_cost_saved = Column(Numeric(10, 2), default=0)

    # Performance improvements
    avg_ctr_improvement = Column(Float, default=0)
    avg_conversion_improvement = Column(Float, default=0)
    revenue_increase = Column(Numeric(10, 2), default=0)

    # ROI calculation
    automation_cost = Column(Numeric(10, 2), default=0)  # Cost of running automation
    net_benefit = Column(Numeric(10, 2), default=0)
    roi_percentage = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="roi_tracking")

    def calculate_roi(self):
        """Calculate ROI metrics"""
        # Total savings = labor cost saved + performance value added
        self.total_cost_saved = self.labor_cost_saved + self.performance_value_added

        # Net benefit = total savings - automation cost
        self.net_benefit = self.total_cost_saved - self.automation_cost

        # ROI percentage = (net benefit / automation cost) * 100
        if self.automation_cost > 0:
            self.roi_percentage = (
                float(self.net_benefit) / float(self.automation_cost)
            ) * 100
        else:
            self.roi_percentage = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert ROI tracking to dictionary"""
        return {
            "id": self.id,
            "roi_id": self.roi_id,
            "campaign_id": self.campaign_id,
            "tracking_period": self.tracking_period,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_time_saved_hours": self.total_time_saved_hours,
            "tasks_automated": self.tasks_automated,
            "labor_cost_saved": (
                float(self.labor_cost_saved) if self.labor_cost_saved else 0
            ),
            "performance_value_added": (
                float(self.performance_value_added)
                if self.performance_value_added
                else 0
            ),
            "total_cost_saved": (
                float(self.total_cost_saved) if self.total_cost_saved else 0
            ),
            "avg_ctr_improvement": self.avg_ctr_improvement,
            "avg_conversion_improvement": self.avg_conversion_improvement,
            "revenue_increase": (
                float(self.revenue_increase) if self.revenue_increase else 0
            ),
            "automation_cost": (
                float(self.automation_cost) if self.automation_cost else 0
            ),
            "net_benefit": float(self.net_benefit) if self.net_benefit else 0,
            "roi_percentage": self.roi_percentage,
        }


class AIDecisionHistory(Base):
    """Track AI decisions and their outcomes"""

    __tablename__ = "ai_decision_history"

    id = Column(Integer, primary_key=True)
    decision_id = Column(String(100), unique=True, nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    decision_type = Column(SQLEnum(DecisionType), nullable=False)
    decision_timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Decision details
    input_data = Column(JSON)  # Data used for decision
    decision_made = Column(JSON)  # The actual decision/recommendation
    confidence_score = Column(Float)  # AI confidence in the decision
    reasoning = Column(Text)  # AI explanation

    # Implementation
    was_implemented = Column(Boolean, default=False)
    implemented_at = Column(DateTime)
    implementation_result = Column(JSON)

    # Outcomes
    expected_impact = Column(JSON)  # Predicted outcomes
    actual_impact = Column(JSON)  # Actual outcomes
    impact_measured_at = Column(DateTime)
    success_score = Column(Float)  # How successful was the decision

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="ai_decisions")

    def calculate_success_score(self):
        """Calculate success score based on expected vs actual impact"""
        if not self.expected_impact or not self.actual_impact:
            return None

        scores = []
        for metric, expected in self.expected_impact.items():
            if metric in self.actual_impact and expected != 0:
                actual = self.actual_impact[metric]
                # Calculate percentage of expectation met
                score = min((actual / expected) * 100, 200)  # Cap at 200%
                scores.append(score)

        if scores:
            self.success_score = sum(scores) / len(scores)
        else:
            self.success_score = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert AI decision to dictionary"""
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "campaign_id": self.campaign_id,
            "decision_type": self.decision_type.value if self.decision_type else None,
            "decision_timestamp": self.decision_timestamp.isoformat(),
            "input_data": self.input_data,
            "decision_made": self.decision_made,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "was_implemented": self.was_implemented,
            "implemented_at": (
                self.implemented_at.isoformat() if self.implemented_at else None
            ),
            "implementation_result": self.implementation_result,
            "expected_impact": self.expected_impact,
            "actual_impact": self.actual_impact,
            "impact_measured_at": (
                self.impact_measured_at.isoformat() if self.impact_measured_at else None
            ),
            "success_score": self.success_score,
        }


# Database utilities
class DatabaseManager:
    """Manage database connections and operations"""

    def __init__(self, database_url: Optional[str] = None):
        if not database_url:
            database_url = os.getenv(
                "DATABASE_URL", "sqlite:///marketing_automation.db"
            )

        engine_kwargs: Dict[str, Any] = {"echo": False, "pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}

        self.engine = create_engine(database_url, **engine_kwargs)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self):
        """Get a database session"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_campaign(self, campaign_data: Dict[str, Any]) -> Campaign:
        """Create a new campaign"""
        with self.get_session() as session:
            campaign = Campaign(**campaign_data)
            session.add(campaign)
            session.flush()
            return campaign

    def track_automation_task(
        self,
        task_type: TaskType,
        task_name: str,
        manual_duration_minutes: float,
        hourly_rate: float = 50.0,
        campaign_id: Optional[int] = None,
    ) -> AutomationTask:
        """Start tracking an automation task"""
        with self.get_session() as session:
            task = AutomationTask(
                task_id=f"task_{datetime.utcnow().timestamp()}",
                task_type=task_type,
                task_name=task_name,
                manual_duration_minutes=manual_duration_minutes,
                hourly_rate=Decimal(str(hourly_rate)),
                campaign_id=campaign_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            session.add(task)
            session.flush()
            return task

    def complete_automation_task(
        self,
        task_id: str,
        automated_duration_seconds: float,
        result_data: Optional[Dict[str, Any]] = None,
        items_processed: int = 0,
    ) -> Tuple[float, Decimal]:
        """Complete an automation task and calculate savings"""
        with self.get_session() as session:
            task = session.query(AutomationTask).filter_by(task_id=task_id).first()
            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.completed_at = datetime.utcnow()
            task.automated_duration_seconds = automated_duration_seconds
            task.status = TaskStatus.COMPLETED
            task.result_data = result_data
            task.items_processed = items_processed

            # Calculate savings
            time_saved, cost_saved = task.calculate_savings()

            session.flush()
            return time_saved, cost_saved

    def record_performance_metrics(
        self,
        campaign_id: int,
        metrics: Dict[str, Any],
        is_automated: bool = False,
        automation_applied: Optional[List[str]] = None,
    ) -> PerformanceMetrics:
        """Record performance metrics for a campaign"""
        with self.get_session() as session:
            perf_metrics = PerformanceMetrics(
                metric_id=f"metric_{datetime.utcnow().timestamp()}",
                campaign_id=campaign_id,
                metric_date=datetime.utcnow(),
                is_automated=is_automated,
                automation_applied=automation_applied,
                **metrics,
            )
            perf_metrics.calculate_metrics()
            session.add(perf_metrics)
            session.flush()
            return perf_metrics

    def calculate_period_roi(
        self,
        period_start: datetime,
        period_end: datetime,
        campaign_id: Optional[int] = None,
    ) -> ROITracking:
        """Calculate ROI for a time period"""
        with self.get_session() as session:
            # Query automation tasks in period
            task_query = session.query(AutomationTask).filter(
                AutomationTask.completed_at >= period_start,
                AutomationTask.completed_at <= period_end,
                AutomationTask.status == TaskStatus.COMPLETED,
            )

            if campaign_id:
                task_query = task_query.filter_by(campaign_id=campaign_id)

            tasks = task_query.all()

            # Calculate aggregate metrics
            total_time_saved_hours = sum(task.time_saved_minutes for task in tasks) / 60
            labor_cost_saved = sum(task.cost_saved for task in tasks)
            tasks_automated = len(tasks)

            # Query performance improvements
            perf_query = session.query(PerformanceMetrics).filter(
                PerformanceMetrics.metric_date >= period_start,
                PerformanceMetrics.metric_date <= period_end,
                PerformanceMetrics.is_automated == True,
            )

            if campaign_id:
                perf_query = perf_query.filter_by(campaign_id=campaign_id)

            performances = perf_query.all()

            # Calculate average improvements
            ctr_improvements = [
                p.ctr_improvement for p in performances if p.ctr_improvement
            ]
            conversion_improvements = [
                p.conversion_improvement
                for p in performances
                if p.conversion_improvement
            ]

            avg_ctr_improvement = (
                sum(ctr_improvements) / len(ctr_improvements) if ctr_improvements else 0
            )
            avg_conversion_improvement = (
                sum(conversion_improvements) / len(conversion_improvements)
                if conversion_improvements
                else 0
            )

            # Estimate performance value added (simplified calculation)
            performance_value_added = Decimal("0")
            for perf in performances:
                if (
                    perf.baseline_conversion_rate
                    and perf.conversion_rate > perf.baseline_conversion_rate
                ):
                    additional_conversions = (
                        (perf.conversion_rate - perf.baseline_conversion_rate) / 100
                    ) * perf.clicks
                    # Assume average order value of $100
                    performance_value_added += Decimal(
                        str(additional_conversions * 100)
                    )

            # Create ROI tracking record
            roi_tracking = ROITracking(
                roi_id=f"roi_{datetime.utcnow().timestamp()}",
                campaign_id=campaign_id,
                tracking_period="custom",
                period_start=period_start,
                period_end=period_end,
                total_time_saved_hours=total_time_saved_hours,
                tasks_automated=tasks_automated,
                labor_cost_saved=labor_cost_saved,
                performance_value_added=performance_value_added,
                avg_ctr_improvement=avg_ctr_improvement,
                avg_conversion_improvement=avg_conversion_improvement,
                automation_cost=Decimal("100"),  # Default automation cost
            )

            roi_tracking.calculate_roi()
            session.add(roi_tracking)
            session.flush()

            return roi_tracking

    def record_ai_decision(
        self,
        decision_type: DecisionType,
        input_data: Dict[str, Any],
        decision_made: Dict[str, Any],
        confidence_score: float,
        reasoning: str,
        expected_impact: Dict[str, Any],
        campaign_id: Optional[int] = None,
        decision_id: Optional[str] = None,
    ) -> AIDecisionHistory:
        """Record an AI decision"""
        with self.get_session() as session:
            ai_decision = AIDecisionHistory(
                decision_id=decision_id or f"decision_{datetime.utcnow().timestamp()}",
                campaign_id=campaign_id,
                decision_type=decision_type,
                input_data=input_data,
                decision_made=decision_made,
                confidence_score=confidence_score,
                reasoning=reasoning,
                expected_impact=expected_impact,
            )
            session.add(ai_decision)
            session.flush()
            return ai_decision

    def update_ai_decision_outcome(
        self,
        decision_id: str,
        actual_impact: Dict[str, Any],
        implementation_result: Optional[Dict[str, Any]] = None,
    ):
        """Update AI decision with actual outcomes"""
        with self.get_session() as session:
            decision = (
                session.query(AIDecisionHistory)
                .filter_by(decision_id=decision_id)
                .first()
            )
            if not decision:
                raise ValueError(f"Decision {decision_id} not found")

            decision.actual_impact = actual_impact
            decision.impact_measured_at = datetime.utcnow()

            if implementation_result:
                decision.implementation_result = implementation_result
                decision.was_implemented = True
                decision.implemented_at = datetime.utcnow()

            decision.calculate_success_score()
            session.flush()

    def get_automation_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get automation summary for the last N days"""
        with self.get_session() as session:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Total tasks automated
            total_tasks = (
                session.query(func.count(AutomationTask.id))
                .filter(
                    AutomationTask.completed_at >= start_date,
                    AutomationTask.status == TaskStatus.COMPLETED,
                )
                .scalar()
            )

            # Total time saved
            total_time_saved = (
                session.query(
                    func.sum(
                        AutomationTask.manual_duration_minutes
                        - (AutomationTask.automated_duration_seconds / 60)
                    )
                )
                .filter(
                    AutomationTask.completed_at >= start_date,
                    AutomationTask.status == TaskStatus.COMPLETED,
                )
                .scalar()
                or 0
            )

            # Total cost saved
            total_cost_saved = (
                session.query(
                    func.sum(AutomationTask.manual_cost - AutomationTask.automated_cost)
                )
                .filter(
                    AutomationTask.completed_at >= start_date,
                    AutomationTask.status == TaskStatus.COMPLETED,
                )
                .scalar()
                or 0
            )

            # Average efficiency gain
            avg_efficiency = (
                session.query(
                    func.avg(
                        case(
                            (
                                AutomationTask.manual_duration_minutes > 0,
                                (
                                    (
                                        AutomationTask.manual_duration_minutes
                                        - (
                                            AutomationTask.automated_duration_seconds
                                            / 60
                                        )
                                    )
                                    / AutomationTask.manual_duration_minutes
                                )
                                * 100,
                            ),
                            else_=0,
                        )
                    )
                )
                .filter(
                    AutomationTask.completed_at >= start_date,
                    AutomationTask.status == TaskStatus.COMPLETED,
                )
                .scalar()
                or 0
            )

            # AI decision success rate
            successful_decisions = (
                session.query(func.count(AIDecisionHistory.id))
                .filter(
                    AIDecisionHistory.decision_timestamp >= start_date,
                    AIDecisionHistory.success_score >= 80,
                )
                .scalar()
            )

            total_decisions = (
                session.query(func.count(AIDecisionHistory.id))
                .filter(
                    AIDecisionHistory.decision_timestamp >= start_date,
                    AIDecisionHistory.success_score.isnot(None),
                )
                .scalar()
                or 1
            )

            return {
                "period_days": days,
                "total_tasks_automated": total_tasks,
                "total_time_saved_hours": total_time_saved / 60,
                "total_cost_saved": float(total_cost_saved),
                "average_efficiency_gain": avg_efficiency,
                "ai_decision_success_rate": (successful_decisions / total_decisions)
                * 100,
                "summary_date": datetime.utcnow().isoformat(),
            }


# Create a global database manager instance
db = DatabaseManager()
