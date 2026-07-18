"""SQLAlchemy model for recruiter notes."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class RecruiterNote(Base):
    __tablename__ = "recruiter_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    recruiter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note_text = Column(Text, nullable=False)
    is_pinned = Column(Integer, default=0)
    mentions = Column(Text, nullable=True)                    # JSON string
    created_at = Column(Text, nullable=False)

    application = relationship("Application", back_populates="recruiter_notes")
    recruiter = relationship("User", back_populates="recruiter_notes")
