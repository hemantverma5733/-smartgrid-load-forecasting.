from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.base_class import Base

class AnalyticsReport(Base):
    id = Column(Integer, primary_key=True, index=True)
    generated_at = Column(DateTime, index=True, nullable=False)
    report_type = Column(String, nullable=False)  # "DAILY", "WEEKLY", "MONTHLY"
    data_json = Column(Text, nullable=False)  # JSON formatted analytics data
