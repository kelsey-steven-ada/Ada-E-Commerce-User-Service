import os
import boto3
import pytest
from app.db import db
from app import create_app
from dotenv import load_dotenv
from app.models.user import User
from flask.signals import request_finished
from moto import mock_aws

load_dotenv()

QUEUE_NAME = "test-orders.fifo"

@pytest.fixture
def aws_credentials():
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"


@pytest.fixture
def app(aws_credentials):
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": os.environ.get('SQLALCHEMY_TEST_DATABASE_URI')
    }

    app = create_app(test_config)

    @request_finished.connect_via(app)
    def expire_session(sender, response, **extra):
        db.session.remove()

    with app.app_context():
        db.create_all()
        yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def mock_aws_context(aws_credentials):
    with mock_aws():
        yield


@pytest.fixture
def sqs_queue(mock_aws_context):
    sqs = boto3.resource("sqs", region_name=os.environ["AWS_DEFAULT_REGION"])
    queue = sqs.create_queue(
        QueueName=QUEUE_NAME,
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "true",
        },
    )
    os.environ["QUEUE_URL"] = queue.url
    yield queue


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def one_user(app):
    user = User(first_name="Ada", last_name="Lovelace", email="ada@example.com")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_order(one_user):
    return {
        "id": 101,
        "user_id": one_user.id,
        "items": [
            {"product_name": "Widget", "quantity": 2, "product_price": 9.99},
            {"product_name": "Gadget", "quantity": 1, "product_price": 24.99},
        ],
    }


@pytest.fixture
def three_users(app):
    users = [
        User(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
        User(first_name="Grace", last_name="Hopper", email="grace@example.com"),
        User(first_name="Alan", last_name="Turing", email="alan@example.com"),
    ]
    db.session.add_all(users)
    db.session.commit()
    return users

