import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock  # noqa 401
from flask import Flask  # noqa 401
from src.embeddings.app import app, encode_and_storage  # noqa 401


@pytest.fixture
def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    client = app.test_client()

    yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


@patch('src.embeddings.app.open')
@patch('src.embeddings.app.encode_and_storage')
def test_embed_text(mock_encode_and_storage, mock_open, client):
    """
    Testa a leitura de um arquivo de texto e verifica se os embeddings são salvos corretamente.
    """  # noqa 401
    mock_open.return_value.__enter__.return_value.read.return_value = "sample text content"  # noqa 401

    response = client.post('/embed', json={'file_path': 'data/extracted_text.txt'})  # noqa 401
    assert response.status_code == 200
    assert response.json == {'status': 'embeddings saved'}
    mock_encode_and_storage.assert_called_once()


def test_embed_text_no_file_path(client):
    """
    Testa a geração de embeddings sem fornecer o caminho do arquivo, esperando um erro 400.
    """  # noqa 401
    response = client.post('/embed', json={})
    assert response.status_code == 400
    assert response.json == {'error': 'file_path is required'}


def test_embed_text_file_not_found(client):
    """
    Testa a geração de embeddings com um caminho de arquivo inexistente, esperando um erro 404.
    """  # noqa 401
    response = client.post('/embed', json={'file_path': 'non_existent_file.txt'})  # noqa 401
    assert response.status_code == 404
    assert response.json == {'error': 'File not found'}
