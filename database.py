import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, desc
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =========================================================
# MODELS
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    history = relationship("DocumentHistory", back_populates="user", cascade="all, delete-orphan")
    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")


class DocumentHistory(Base):
    __tablename__ = "document_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_name = Column(String(256), nullable=False)
    file_name = Column(String(256), nullable=False)
    file_type = Column(String(64), default="unknown")
    file_count = Column(Integer, default=1)
    documentation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="history")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query = Column(String(256), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="searches")


# =========================================================
# PASSWORD SECURITY
# =========================================================

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    )
    return key.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    )
    return secrets.compare_digest(key.hex(), expected_hash)


# =========================================================
# DATABASE OPERATIONS
# =========================================================

def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure default admin user exists
    db = SessionLocal()
    try:
        admin_username = os.getenv("APP_USERNAME", "admin")
        admin_password = os.getenv("APP_PASSWORD", "admin123")
        existing_admin = db.query(User).filter(User.username == admin_username).first()
        if not existing_admin:
            pwd_hash, salt = hash_password(admin_password)
            default_admin = User(
                username=admin_username,
                password_hash=pwd_hash,
                salt=salt,
            )
            db.add(default_admin)
            db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if verify_password(password, user.salt, user.password_hash):
            return {"id": user.id, "username": user.username}
        return None
    finally:
        db.close()


def register_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return False, "Username already exists. Please choose another."

        pwd_hash, salt = hash_password(password)
        new_user = User(
            username=username,
            password_hash=pwd_hash,
            salt=salt,
        )
        db.add(new_user)
        db.commit()
        return True, "User registered successfully."
    except Exception as e:
        db.rollback()
        return False, f"Registration failed: {str(e)}"
    finally:
        db.close()


def save_history(
    project_name: str,
    file_name: str,
    file_type: str,
    file_count: int,
    documentation: str,
    user_id: Optional[int] = None,
) -> Optional[int]:
    db = SessionLocal()
    try:
        entry = DocumentHistory(
            user_id=user_id,
            project_name=project_name,
            file_name=file_name,
            file_type=file_type,
            file_count=file_count,
            documentation=documentation,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.id
    except Exception as e:
        print(f"Failed to save history: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def get_user_history(user_id: Optional[int], limit: int = 50) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        query = db.query(DocumentHistory)
        if user_id is not None:
            query = query.filter(DocumentHistory.user_id == user_id)
        entries = query.order_by(DocumentHistory.created_at.desc()).limit(limit).all()

        return [
            {
                "id": e.id,
                "project_name": e.project_name,
                "file_name": e.file_name,
                "file_type": e.file_type,
                "file_count": e.file_count,
                "documentation": e.documentation,
                "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
            }
            for e in entries
        ]
    finally:
        db.close()


def get_history_item(history_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        query = db.query(DocumentHistory).filter(DocumentHistory.id == history_id)
        if user_id is not None:
            query = query.filter(DocumentHistory.user_id == user_id)
        e = query.first()
        if not e:
            return None
        return {
            "id": e.id,
            "project_name": e.project_name,
            "file_name": e.file_name,
            "file_type": e.file_type,
            "file_count": e.file_count,
            "documentation": e.documentation,
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
        }
    finally:
        db.close()


# =========================================================
# SEARCH & SUGGESTION OPERATIONS
# =========================================================

def save_search_query(user_id: int, query: str):
    query = query.strip()
    if not query:
        return
    db = SessionLocal()
    try:
        # Don't add duplicate if it was the most recent search
        last_search = (
            db.query(SearchHistory)
            .filter(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .first()
        )
        if last_search and last_search.query.lower() == query.lower():
            # Update timestamp
            last_search.created_at = datetime.utcnow()
            db.commit()
            return

        entry = SearchHistory(user_id=user_id, query=query)
        db.add(entry)
        db.commit()
    except Exception as e:
        print(f"Failed to save search: {e}")
        db.rollback()
    finally:
        db.close()


def get_recent_searches(user_id: int, limit: int = 8) -> List[str]:
    db = SessionLocal()
    try:
        searches = (
            db.query(SearchHistory.query)
            .filter(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
            .all()
        )
        # De-duplicate while preserving recency order
        seen = set()
        result = []
        for (q,) in searches:
            q_clean = q.strip()
            q_lower = q_clean.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                result.append(q_clean)
                if len(result) >= limit:
                    break
        return result
    finally:
        db.close()


def get_user_search_suggestions(user_id: int, prefix: str = "", limit: int = 8) -> List[Dict[str, str]]:
    """
    Returns suggestions including:
    - Previous searches matching the prefix
    - Previously uploaded file names & project names matching the prefix
    """
    db = SessionLocal()
    suggestions = []
    seen = set()
    prefix_clean = prefix.strip().lower()

    try:
        # 1. Past search queries
        query_searches = (
            db.query(SearchHistory.query)
            .filter(SearchHistory.user_id == user_id)
            .order_by(SearchHistory.created_at.desc())
        )
        for (q,) in query_searches.all():
            q_clean = q.strip()
            q_lower = q_clean.lower()
            if prefix_clean and prefix_clean not in q_lower:
                continue
            if q_lower not in seen:
                seen.add(q_lower)
                suggestions.append({"text": q_clean, "type": "recent"})
                if len(suggestions) >= limit:
                    return suggestions

        # 2. Uploaded file names and project names
        docs_query = (
            db.query(DocumentHistory.file_name, DocumentHistory.project_name)
            .filter(DocumentHistory.user_id == user_id)
            .order_by(DocumentHistory.created_at.desc())
        )
        for fname, pname in docs_query.all():
            for item in (fname, pname):
                if not item:
                    continue
                item_clean = item.strip()
                item_lower = item_clean.lower()
                if prefix_clean and prefix_clean not in item_lower:
                    continue
                if item_lower not in seen:
                    seen.add(item_lower)
                    suggestions.append({"text": item_clean, "type": "file"})
                    if len(suggestions) >= limit:
                        return suggestions

        return suggestions
    finally:
        db.close()


def search_user_history(user_id: int, query: str) -> List[Dict[str, Any]]:
    query_clean = query.strip().lower()
    if not query_clean:
        return get_user_history(user_id=user_id)

    db = SessionLocal()
    try:
        entries = (
            db.query(DocumentHistory)
            .filter(DocumentHistory.user_id == user_id)
            .order_by(DocumentHistory.created_at.desc())
            .all()
        )

        results = []
        for e in entries:
            # Match against project_name, file_name, or documentation text
            if (
                query_clean in (e.project_name or "").lower()
                or query_clean in (e.file_name or "").lower()
                or query_clean in (e.file_type or "").lower()
                or query_clean in (e.documentation or "").lower()
            ):
                results.append(
                    {
                        "id": e.id,
                        "project_name": e.project_name,
                        "file_name": e.file_name,
                        "file_type": e.file_type,
                        "file_count": e.file_count,
                        "documentation": e.documentation,
                        "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
                    }
                )
        return results
    finally:
        db.close()


def clear_search_history(user_id: int):
    db = SessionLocal()
    try:
        db.query(SearchHistory).filter(SearchHistory.user_id == user_id).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to clear search history: {e}")
    finally:
        db.close()
