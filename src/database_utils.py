"""Database utilities and helper functions for marketing automation tracking"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .database import (
    db, Campaign, AutomationTask, PerformanceMetrics, ROITracking,
    AIDecisionHistory, TaskType, TaskStatus, DecisionType
)

logger = logging.getLogger(__name__)


class AutomationTracker:
    """Helper class to track automation tasks with context manager support"""
    
    def __init__(
        self,
        task_type: TaskType,
        task_name: str,
        manual_duration_minutes: float,
        hourly_rate: float = 50.0,
        campaign_id: Optional[int] = None
    ):
        self.task_type = task_type
        self.task_name = task_name
        self.manual_duration_minutes = manual_duration_minutes
        self.hourly_rate = hourly_rate
        self.campaign_id = campaign_id
        self.task = None
        self.start_time = None
        self.result_data = {}
        self.items_processed = 0
    
    async def __aenter__(self):
        """Start tracking the automation task"""
        self.start_time = datetime.utcnow()
        self.task = db.track_automation_task(
            task_type=self.task_type,
            task_name=self.task_name,
            manual_duration_minutes=self.manual_duration_minutes,
            hourly_rate=self.hourly_rate,
            campaign_id=self.campaign_id
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Complete the automation task and calculate savings"""
        if self.task:
            end_time = datetime.utcnow()
            duration_seconds = (end_time - self.start_time).total_seconds()
            
            if exc_type is None:
                # Task completed successfully
                time_saved, cost_saved = db.complete_automation_task(
                    task_id=self.task.task_id,
                    automated_duration_seconds=duration_seconds,
                    result_data=self.result_data,
                    items_processed=self.items_processed
                )
                
                logger.info(
                    f"Task '{self.task_name}' completed. "
                    f"Time saved: {time_saved:.1f} minutes, "
                    f"Cost saved: ${cost_saved:.2f}"
                )
            else:
                # Task failed
                with db.get_session() as session:
                    task = session.query(AutomationTask).filter_by(task_id=self.task.task_id).first()
                    task.status = TaskStatus.FAILED
                    task.error_message = str(exc_val)
                    task.completed_at = end_time
                    task.automated_duration_seconds = duration_seconds
    
    def set_result(self, key: str, value: Any):
        """Set a result value"""
        self.result_data[key] = value
    
    def increment_items(self, count: int = 1):
        """Increment items processed counter"""
        self.items_processed += count


# Predefined task duration estimates (in minutes)
TASK_DURATION_ESTIMATES = {
    TaskType.CAMPAIGN_CREATION: 45,  # Manual campaign creation
    TaskType.BUDGET_OPTIMIZATION: 30,  # Manual budget analysis and adjustment
    TaskType.AD_COPY_GENERATION: 60,  # Manual copywriting
    TaskType.AUDIENCE_SEGMENTATION: 90,  # Manual audience analysis
    TaskType.PERFORMANCE_ANALYSIS: 60,  # Manual performance review
    TaskType.REPORT_GENERATION: 120,  # Manual report creation
    TaskType.EMAIL_CAMPAIGN: 90,  # Manual email campaign setup
    TaskType.A_B_TESTING: 45,  # Manual A/B test setup
}


def estimate_manual_duration(task_type: TaskType, complexity_factor: float = 1.0) -> float:
    """
    Estimate manual duration for a task type
    
    Args:
        task_type: Type of automation task
        complexity_factor: Multiplier for complexity (1.0 = normal, 2.0 = complex)
    
    Returns:
        Estimated duration in minutes
    """
    base_duration = TASK_DURATION_ESTIMATES.get(task_type, 30)
    return base_duration * complexity_factor


def calculate_hourly_rate(
    role: str = "marketing_manager",
    location: str = "US",
    experience_years: int = 5
) -> float:
    """
    Calculate hourly rate based on role and location
    
    This is a simplified calculation - in production, this could
    integrate with salary data APIs
    """
    base_rates = {
        "marketing_manager": 75,
        "marketing_specialist": 50,
        "marketing_coordinator": 35,
        "marketing_director": 100,
        "freelancer": 60
    }
    
    location_multipliers = {
        "US": 1.0,
        "UK": 0.9,
        "EU": 0.85,
        "APAC": 0.7,
        "OTHER": 0.8
    }
    
    base_rate = base_rates.get(role, 50)
    location_mult = location_multipliers.get(location, 1.0)
    
    # Add 5% for each year of experience above 3
    experience_mult = 1.0 + (max(0, experience_years - 3) * 0.05)
    
    return base_rate * location_mult * experience_mult


async def track_campaign_optimization(
    campaign_id: int,
    optimization_type: str,
    changes_made: Dict[str, Any],
    expected_impact: Dict[str, float]
) -> AIDecisionHistory:
    """
    Track a campaign optimization decision
    
    Args:
        campaign_id: Campaign being optimized
        optimization_type: Type of optimization (budget, targeting, creative)
        changes_made: Dictionary of changes made
        expected_impact: Expected impact metrics
    
    Returns:
        AIDecisionHistory record
    """
    decision_type_map = {
        "budget": DecisionType.BUDGET_ALLOCATION,
        "bid": DecisionType.BID_ADJUSTMENT,
        "targeting": DecisionType.AUDIENCE_TARGETING,
        "creative": DecisionType.CREATIVE_SELECTION,
        "general": DecisionType.CAMPAIGN_OPTIMIZATION
    }
    
    decision_type = decision_type_map.get(optimization_type, DecisionType.CAMPAIGN_OPTIMIZATION)
    
    # Get current campaign metrics as input data
    with db.get_session() as session:
        recent_metrics = session.query(PerformanceMetrics).filter_by(
            campaign_id=campaign_id
        ).order_by(PerformanceMetrics.metric_date.desc()).first()
        
        input_data = recent_metrics.to_dict() if recent_metrics else {}
    
    return db.record_ai_decision(
        decision_type=decision_type,
        input_data=input_data,
        decision_made=changes_made,
        confidence_score=0.85,  # Default confidence
        reasoning=f"Optimization based on performance analysis",
        expected_impact=expected_impact,
        campaign_id=campaign_id
    )


async def measure_optimization_impact(
    decision_id: str,
    measurement_period_days: int = 7
) -> Dict[str, Any]:
    """
    Measure the actual impact of an optimization decision
    
    Args:
        decision_id: ID of the AI decision to measure
        measurement_period_days: Days to measure impact over
    
    Returns:
        Dictionary with actual vs expected impact
    """
    with db.get_session() as session:
        decision = session.query(AIDecisionHistory).filter_by(decision_id=decision_id).first()
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        # Get performance metrics after implementation
        start_date = decision.implemented_at or decision.decision_timestamp
        end_date = start_date + timedelta(days=measurement_period_days)
        
        metrics_after = session.query(PerformanceMetrics).filter(
            PerformanceMetrics.campaign_id == decision.campaign_id,
            PerformanceMetrics.metric_date >= start_date,
            PerformanceMetrics.metric_date <= end_date
        ).all()
        
        # Calculate actual impact
        actual_impact = {}
        if metrics_after:
            # Average metrics over the period
            actual_impact = {
                "avg_ctr": sum(m.ctr for m in metrics_after) / len(metrics_after),
                "avg_conversion_rate": sum(m.conversion_rate for m in metrics_after) / len(metrics_after),
                "total_conversions": sum(m.conversions for m in metrics_after),
                "total_revenue": sum(float(m.revenue) for m in metrics_after),
                "avg_cpa": sum(float(m.cpa) for m in metrics_after if m.cpa) / len([m for m in metrics_after if m.cpa]),
                "avg_roas": sum(m.roas for m in metrics_after) / len(metrics_after)
            }
        
        # Update decision with actual impact
        db.update_ai_decision_outcome(
            decision_id=decision_id,
            actual_impact=actual_impact
        )
        
        return {
            "decision_id": decision_id,
            "expected_impact": decision.expected_impact,
            "actual_impact": actual_impact,
            "measurement_period_days": measurement_period_days,
            "success_score": decision.success_score
        }


def generate_roi_report(
    start_date: datetime,
    end_date: datetime,
    campaign_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate a comprehensive ROI report for a time period
    
    Args:
        start_date: Report start date
        end_date: Report end date
        campaign_id: Optional specific campaign
    
    Returns:
        Dictionary with ROI metrics and insights
    """
    # Calculate ROI for the period
    roi_tracking = db.calculate_period_roi(start_date, end_date, campaign_id)
    
    # Get automation summary
    days = (end_date - start_date).days
    summary = db.get_automation_summary(days)
    
    # Get task breakdown by type
    with db.get_session() as session:
        completed_tasks = session.query(AutomationTask).filter(
            AutomationTask.completed_at >= start_date,
            AutomationTask.completed_at <= end_date,
            AutomationTask.status == TaskStatus.COMPLETED
        ).all()

    grouped: Dict[TaskType, Dict[str, float]] = {}
    for task in completed_tasks:
        bucket = grouped.setdefault(
            task.task_type,
            {"count": 0, "time_saved_minutes": 0.0, "cost_saved": 0.0},
        )
        bucket["count"] += 1
        bucket["time_saved_minutes"] += task.time_saved_minutes or 0.0
        bucket["cost_saved"] += float(task.cost_saved or 0.0)

    task_summary = [
        {
            "task_type": task_type.value,
            "count": values["count"],
            "time_saved_hours": values["time_saved_minutes"] / 60,
            "cost_saved": values["cost_saved"],
        }
        for task_type, values in grouped.items()
    ]
    
    return {
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'days': days
        },
        'roi_metrics': roi_tracking.to_dict(),
        'automation_summary': summary,
        'task_breakdown': task_summary,
        'insights': {
            'most_automated_task': max(task_summary, key=lambda x: x['count'])['task_type'] if task_summary else None,
            'highest_time_saving_task': max(task_summary, key=lambda x: x['time_saved_hours'])['task_type'] if task_summary else None,
            'automation_adoption_rate': f"{(summary['total_tasks_automated'] / max(1, days * 10)) * 100:.1f}%",  # Assuming 10 tasks/day potential
            'roi_status': 'positive' if roi_tracking.roi_percentage > 0 else 'negative'
        }
    }


# Example usage for tracking automation with context manager
async def example_automation_tracking():
    """Example of using the automation tracker"""
    
    # Track a budget optimization task
    async with AutomationTracker(
        task_type=TaskType.BUDGET_OPTIMIZATION,
        task_name="Q4 Budget Reallocation",
        manual_duration_minutes=estimate_manual_duration(TaskType.BUDGET_OPTIMIZATION, complexity_factor=1.5),
        hourly_rate=calculate_hourly_rate("marketing_manager", "US", 7),
        campaign_id=1
    ) as tracker:
        # Simulate automation work
        tracker.set_result("campaigns_analyzed", 15)
        tracker.set_result("budget_changes", 8)
        tracker.set_result("expected_roi_increase", 25.5)
        tracker.increment_items(15)  # 15 campaigns processed
        
        # The actual automation work would happen here
        # When the context exits, time and cost savings are automatically calculated
