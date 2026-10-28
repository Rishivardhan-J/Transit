"""Run metrics, per-stop predictions, replay events

Revision ID: a1c4e9d2b7f0
Revises: 7f31df5271a9
"""
from alembic import op
import sqlalchemy as sa

revision = "a1c4e9d2b7f0"
down_revision = "7f31df5271a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, col in [
        ("parent_run_id", sa.Column("parent_run_id", sa.String(), nullable=True)),
        ("event", sa.Column("event", sa.JSON(), nullable=True)),
        ("metrics", sa.Column("metrics", sa.JSON(), nullable=True)),
        ("baseline_metrics", sa.Column("baseline_metrics", sa.JSON(), nullable=True)),
        ("unassigned", sa.Column("unassigned", sa.JSON(), nullable=True)),
        ("runtime_s", sa.Column("runtime_s", sa.Float(), nullable=True)),
        ("time_model", sa.Column("time_model", sa.String(), nullable=True)),
        ("error", sa.Column("error", sa.String(), nullable=True)),
    ]:
        op.add_column("optimizer_runs", col)
    op.create_index(op.f("ix_optimizer_runs_parent_run_id"), "optimizer_runs", ["parent_run_id"])
    op.add_column("routes", sa.Column("stop_slack_min", sa.JSON(), nullable=True))
    op.add_column("vehicles", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("predictions", sa.Column("optimizer_run_id", sa.String(), nullable=True))
    op.add_column("predictions", sa.Column("route_id", sa.String(), nullable=True))
    op.add_column("predictions", sa.Column("stop_index", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("meta", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_predictions_optimizer_run_id"), "predictions", ["optimizer_run_id"])
    op.create_index(op.f("ix_predictions_order_id"), "predictions", ["order_id"])
    op.create_table(
        "replay_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("optimizer_run_id", sa.String(), nullable=False),
        sa.Column("route_id", sa.String(), nullable=False),
        sa.Column("vehicle_id", sa.String(), nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("stop_index", sa.Integer(), nullable=False),
        sa.Column("planned_arrival", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("late", sa.Integer(), nullable=False),
    )
    op.create_index(op.f("ix_replay_events_optimizer_run_id"), "replay_events", ["optimizer_run_id"])


def downgrade() -> None:
    op.drop_table("replay_events")
    op.drop_index(op.f("ix_predictions_order_id"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_optimizer_run_id"), table_name="predictions")
    for c in ("meta", "stop_index", "route_id", "optimizer_run_id"):
        op.drop_column("predictions", c)
    op.drop_column("vehicles", "is_active")
    op.drop_column("routes", "stop_slack_min")
    op.drop_index(op.f("ix_optimizer_runs_parent_run_id"), table_name="optimizer_runs")
    for c in ("error", "time_model", "runtime_s", "unassigned", "baseline_metrics", "metrics", "event", "parent_run_id"):
        op.drop_column("optimizer_runs", c)
