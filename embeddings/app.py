
import json
import numpy as np
import openai
import os
from flask import Flask, request, jsonify


app = Flask(__name__)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("API key not found in environment variables.")
    raise ValueError("No API key provided. You can set your API key in code using 'openai.api_key = <API-KEY>', or you can set the environment variable OPENAI_API_KEY=<API-KEY>).")
else:
    print(f"API key found: {api_key[:5]}...{api_key[-5:]}")  # log de parte da chave para verificar

openai.api_key = api_key


def create_embeddings(text):
    """
    Cria embeddings para o texto fornecido usando a API da OpenAI.

    Args:
        text (str): Texto para o qual os embeddings serão criados.

    Returns:
        np.array: Embeddings gerados.
    """
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return np.array(response['data'][0]['embedding'])


def split_text_into_chunks(text, max_tokens=4000):
    """
    Divide o texto em partes menores para ficar dentro do limite de tokens do modelo.

    Args:
        text (str): Texto a ser dividido.
        max_tokens (int): Máximo de tokens por parte.

    Returns:
        List[str]: Lista de partes de texto.
    """
    words = text.split()
    chunks = []
    current_chunk = []

    current_chunk_length = 0
    for word in words:
        word_length = len(word)
        if current_chunk_length + word_length + 1 > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_chunk_length = word_length
        else:
            current_chunk.append(word)
            current_chunk_length += word_length + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


@app.route('/embed', methods=['POST'])
def embed_text():
    """
    Lê o arquivo de texto especificado e cria embeddings para o conteúdo,
    salvando-os em um arquivo JSON no diretório 'data'.

    Returns:
        json: JSON contendo os embeddings ou uma mensagem de erro.
    """
    data = request.json
    file_path = data.get('file_path')

    if not file_path:
        return jsonify({'error': 'file_path is required'}), 400

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    try:
        text_chunks = split_text_into_chunks(text, max_tokens=4000)
        embeddings = [create_embeddings(chunk) for chunk in text_chunks]

        # persiste os embeddings em um arquivo JSON no diretório 'data'
        embeddings_file_path = os.path.join('/app/data', 'embeddings.json')
        with open(embeddings_file_path, 'w', encoding='utf-8') as f:
            json.dump([embedding.tolist() for embedding in embeddings], f)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'embeddings saved', 'file_path': embeddings_file_path})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
