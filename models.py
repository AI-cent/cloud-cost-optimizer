from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String, unique=True, index=True, nullable=False)
    resource_name = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)   # EBS Volume | EC2 Instance | Elastic IP | Load Balancer | Snapshot
    region = Column(String, nullable=False)
    monthly_cost_usd = Column(Float, nullable=False)
    status = Column(String, nullable=True)
    last_active_date = Column(DateTime, nullable=True)
    ingest_timestamp = Column(DateTime, default=datetime.utcnow)

    findings = relationship("Finding", back_populates="resource", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String, ForeignKey("resources.resource_id"), nullable=False)
    finding_type = Column(String, nullable=False)    # unattached_ebs | idle_ec2 | orphaned_eip | idle_alb | old_snapshot
    severity = Column(String, nullable=False)        # Critical | High | Medium | Low
    estimated_monthly_waste_usd = Column(Float, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="findings")
    remediation_commands = relationship("RemediationCommand", back_populates="finding", cascade="all, delete-orphan")


class RemediationCommand(Base):
    __tablename__ = "remediation_commands"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    command_type = Column(String, default="aws_cli")
    command_text = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("Finding", back_populates="remediation_commands")
