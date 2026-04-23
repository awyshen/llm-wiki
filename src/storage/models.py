"""
数据模型
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import uuid
from datetime import datetime

Base = declarative_base()


class ProcessingStatus(enum.Enum):
    """处理状态"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """文档模型"""

    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    title = Column(String)
    filename = Column(String)
    file_path = Column(String)
    file_type = Column(String)
    extracted_text = Column(Text)
    processing_status = Column(String, default=ProcessingStatus.PENDING.value)
    processing_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    wiki_page_id = Column(String, ForeignKey("wiki_pages.id"))

    wiki_page = relationship("WikiPage", back_populates="document")


class WikiPage(Base):
    """Wiki页面模型"""

    __tablename__ = "wiki_pages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    slug = Column(String, unique=True)
    content = Column(Text)
    summary = Column(Text)
    file_path = Column(String)
    category = Column(String)
    page_metadata = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="wiki_page")
    tags = relationship("Tag", secondary="wiki_page_tags", back_populates="wiki_pages")


class Tag(Base):
    """标签模型"""

    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    wiki_pages = relationship(
        "WikiPage", secondary="wiki_page_tags", back_populates="tags"
    )


class WikiPageTag(Base):
    """Wiki页面标签关联表"""

    __tablename__ = "wiki_page_tags"

    wiki_page_id = Column(String, ForeignKey("wiki_pages.id"), primary_key=True)
    tag_id = Column(String, ForeignKey("tags.id"), primary_key=True)


class Entity(Base):
    """实体模型"""

    __tablename__ = "entities"

    id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    relationships_as_subject = relationship("EntityRelationship", foreign_keys="EntityRelationship.subject_id", back_populates="subject")
    relationships_as_object = relationship("EntityRelationship", foreign_keys="EntityRelationship.object_id", back_populates="object")


class EntityRelationship(Base):
    """实体关系模型"""

    __tablename__ = "entity_relationships"

    id = Column(String, primary_key=True)
    subject_id = Column(String, ForeignKey("entities.id"))
    object_id = Column(String, ForeignKey("entities.id"))
    predicate = Column(String)  # 关系类型
    confidence = Column(Integer, default=0)  # 置信度
    source = Column(String)  # 关系来源
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    subject = relationship("Entity", foreign_keys=[subject_id], back_populates="relationships_as_subject")
    object = relationship("Entity", foreign_keys=[object_id], back_populates="relationships_as_object")


class Feedback(Base):
    """用户反馈模型"""

    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String)
    feedback_type = Column(String)
    content = Column(Text)
    feedback_metadata = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
