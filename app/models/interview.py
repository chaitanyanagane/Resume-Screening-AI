"""SQLAlchemy model for interviews."""

from sqlalchemy import Column, Integer, String, Text, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    interviewer = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    scheduled_at = Column(Text, nullable=False)
    meeting_link = Column(Text, nullable=True)
    status = Column(Text, nullable=False)
    feedback = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('scheduled', 'completed', 'cancelled')", name="ck_interviews_status"),
    )

    application = relationship("Application", back_populates="interviews")
