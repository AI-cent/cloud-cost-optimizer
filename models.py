from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class SeverityEnum(str, enum.Enum):
    critical = "Critical"
    high = "High"
    medium = "Medium"
    low = "Low"


class FindingStatusEnum(str, enum.Enum):
    pending = "pending"
    remediated = "remediated"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    resources = relationship("Resource", back_populates="uploader")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String, index=True, nullable=False)
    resource_name = Column(String, nullable=True)
    resource_type = Column(String, nullable=False)  # EBS Volume / EC2 Instance / Elastic IP / Load Balancer / Snapshot
    region = Column(String, nullable=False)
    monthly_cost_usd = Column(Float, default=0.0)
    status = Column(String, nullable=True)
    last_active_date = Column(DateTime, nullable=True)
    ingest_timestamp = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    uploader = relationship("User", back_populates="resources")
    findings = relationship("Finding", back_populates="resource")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    finding_type = Column(String, nullable=False)  # unattached_ebs / idle_ec2 / orphaned_eip / idle_alb / old_snapshot
    severity = Column(String, nullable=False)       # Critical / High / Medium / Low
    estimated_monthly_waste_usd = Column(Float, default=0.0)
    status = Column(String, default="pending")      # pending / remediated / failed
    remediated_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)

    resource = relationship("Resource", back_populates="findings")
    remediation_commands = relationship("RemediationCommand", back_populates="finding")


class RemediationCommand(Base):
    __tablename__ = "remediation_commands"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    command_type = Column(String, default="aws_cli")
    command_text = Column(String, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("Finding", back_populates="remediation_commands")
