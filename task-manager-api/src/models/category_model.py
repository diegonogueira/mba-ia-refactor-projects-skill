from src.models.database import PersistenceMixin, db
from src.utils.dates import utc_now

DEFAULT_COLOR = "#000000"
COLOR_LENGTH = 7  # "#RRGGBB"


class Category(PersistenceMixin, db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(COLOR_LENGTH), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utc_now)

    # deleting a category keeps its tasks and sets their category_id to NULL (SQLAlchemy default)
    tasks = db.relationship("Task", back_populates="category")
