import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask  # noqa 401
from api.app import app, retrieve, prompt_with_context_builder  # noqa 401


@pytest.fixture
def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    client = app.test_client()

    yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


@patch('src.api.app.retrieve')
@patch('src.api.app.client.chat.completions.create')
def test_qa(mock_create, mock_retrieve, client):
    """
    Testa a rota de perguntas e respostas, verificando se a resposta é gerada corretamente.
    """  # noqa 401
    mock_retrieve.return_value = ["document 1", "document 2", "document 3"]
    mock_create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="Test answer"))])  # noqa 401

    response = client.post('/qa', json={'question': 'Test question'})
    assert response.status_code == 200
    assert response.json == {'answer': 'Test answer'}


def test_qa_no_question(client):
    """
    Testa a rota de perguntas e respostas sem fornecer uma pergunta, esperando um erro 400.
    """  # noqa 401
    response = client.post('/qa', json={})
    assert response.status_code == 400
    assert response.json == {'error': 'Question is required'}


@patch('src.api.app.retrieve')
def test_qa_no_relevant_embeddings(mock_retrieve, client):
    """
    Testa a rota de perguntas e respostas sem encontrar embeddings relevantes, esperando um erro 404.
    """  # noqa 401
    mock_retrieve.return_value = []

    response = client.post('/qa', json={'question': 'Test question'})
    assert response.status_code == 404
    assert response.json == {'error': 'No relevant embeddings found'}
