import itertools
import json
import os
from flask import Flask, request, jsonify
from openai import OpenAI


app = Flask(__name__)

openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("OPENAI_API_KEY key not found in environment variables.")
    raise ValueError("No OPENAI_API_KEY provided. You can set your OPENAI_API_KEY")
else:
    print(f"API key found: {openai_api_key[:5]}...{openai_api_key[-5:]}")  # log de parte da chave para verificar

client = OpenAI(api_key=openai_api_key)


def sliding_chunks(iterable, chunk_size, overlap):
    """
    Gera chunks sobrepostos de um iterável.

    Args:
        iterable (iterável): O iterável a partir do qual os chunks serão gerados.
        chunk_size (int): O tamanho de cada pedaço.
        overlap (int): O número de elementos que irão se sobrepor entre os chunks consecutivos.

    Returns:
        iterador: Um iterador que produz chunks sobrepostos do iterável original.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size deve ser maior que overlap")

    it = iter(iterable)
    chunk = tuple(itertools.islice(it, chunk_size))
    while len(chunk) == chunk_size:
        yield chunk
        chunk = chunk[overlap:] + tuple(itertools.islice(it, chunk_size - overlap))


def create_embeddings(text):
    """
    Cria embeddings para o texto fornecido usando a API da OpenAI.

    Args:
        text (str): Texto para o qual os embeddings serão criados.

    Returns:
        np.array: Embeddings gerados.
    """
    text = text.replace("\n", " ")

    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )

    return response.data[0].embedding


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
            lines = file.read().split()
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    try:
        text_chunks = [f"{' '.join(chunk)}" for chunk in sliding_chunks(lines, chunk_size=100, overlap=50)]
        embeddings = [create_embeddings(text_chunks[i]) for i in range(0, len(text_chunks))]

        # persiste os embeddings em um arquivo JSON no diretório 'data'
        embeddings_file_path = os.path.join('data', 'embeddings.json')
        with open(embeddings_file_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings, f)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'embeddings saved', 'file_path': embeddings_file_path})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
