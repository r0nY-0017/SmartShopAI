from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(String, index=True, nullable=False)
    role         = Column(String, nullable=False)
    content      = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())
