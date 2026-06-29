# Import all the models, so that Base has them before being
# imported by Alembic or database initialization
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.zone import Zone  # noqa
from app.models.meter import Meter  # noqa
from app.models.reading import MeterReading  # noqa
from app.models.prediction import Prediction  # noqa
from app.models.alert import Alert  # noqa
from app.models.report import AnalyticsReport  # noqa
