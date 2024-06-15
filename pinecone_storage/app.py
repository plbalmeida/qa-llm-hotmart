import json
import os
from flask import Flask, request, jsonify
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec


app = Flask(__name__)

pinecone_api_key = os.getenv('PINECONE_API_KEY')
if not pinecone_api_key:
    raise ValueError("PINECONE_API_KEY must be set.")

pc = Pinecone(api_key=pinecone_api_key)


@app.route('/store', methods=['POST'])
def store_embeddings():
    """
    Lê o arquivo embeddings.json especificado e armazena os embeddings no Pinecone.

    Returns:
        json: JSON contendo o status da operação ou uma mensagem de erro.
    """
    data = request.json
    file_path = data.get('file_path')

    if not file_path:
        return jsonify({'error': 'file_path is required'}), 400

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            embeddings = json.load(f)
    except FileNotFoundError:
        return jsonify({'error': 'embeddings.json file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    try:
        # cria ou conecta-se a um índice
        index_name = 'hotmart-blog-index'
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=len(embeddings[0]),
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
        index = pc.Index(index_name)

        # insere os embeddings no índice
        for i, embedding in enumerate(embeddings):
            index.upsert(vectors=[("text_chunk_" + str(i), embedding)])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'embeddings stored successfully'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
