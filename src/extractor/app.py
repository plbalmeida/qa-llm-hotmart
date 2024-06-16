import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify


app = Flask(__name__)

if not os.path.exists('data'):
    os.makedirs('data')

@app.route('/extract', methods=['POST'])
def extract_text():
    """
    Extrai o texto de uma URL fornecida e salva em um arquivo na pasta 'data'.

    Args:
        url (str): URL da qual o texto será extraído.

    Returns:
        json: JSON contendo o texto extraído ou uma mensagem de erro.
    """
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

    soup = BeautifulSoup(response.content, "html.parser")
    text_content = soup.get_text(separator="\n", strip=True)

    filename = os.path.join('data', 'extracted_text.txt')
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(text_content)

    return jsonify({'text': text_content})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
