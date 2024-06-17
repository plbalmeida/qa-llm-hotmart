import os
import tempfile
import pytest
from flask import Flask  # noqa 401
from extractor.app import app


@pytest.fixture
def client():
    """
    Configura o cliente de teste do Flask para o aplicativo.
    """
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    client = app.test_client()

    yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


def test_extract_text(client, requests_mock):
    """
    Testa a extração de texto de uma URL válida e verifica se o conteúdo é salvo corretamente.
    """  # noqa 401
    test_url = 'http://example.com'
    requests_mock.get(test_url, text='<html><body><p>Example text</p></body></html>')  # noqa 401

    response = client.post('/extract', json={'url': test_url})
    assert response.status_code == 200
    assert response.json == {'status': 'text extraction saved'}

    with open('data/extracted_text.txt', 'r', encoding='utf-8') as f:
        extracted_text = f.read()

    assert extracted_text == 'Example text'


def test_extract_text_no_url(client):
    """
    Testa a extração de texto sem fornecer uma URL, esperando um erro 400.
    """
    response = client.post('/extract', json={})
    assert response.status_code == 400
    assert response.json == {'error': 'URL is required'}


def test_extract_text_invalid_url(client, requests_mock):
    """
    Testa a extração de texto com uma URL inválida, esperando um erro 500.
    """
    test_url = 'http://invalid-url.com'
    requests_mock.get(test_url, status_code=404, text='Not Found')

    response = client.post('/extract', json={'url': test_url})
    assert response.status_code == 500
    assert 'error' in response.json
