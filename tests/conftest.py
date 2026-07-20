import pytest
from app.database import engine, Base


@pytest.fixture(autouse=True)
def create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
