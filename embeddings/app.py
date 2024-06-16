import itertools
import numpy as np
import os
import pandas as pd
from flask import Flask, request, jsonify
from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from uuid import uuid4


app = Flask(__name__)

openai_api_key = os.getenv('OPENAI_API_KEY')
pinecone_api_key = os.getenv('PINECONE_API_KEY')

if not openai_api_key or not pinecone_api_key:
    raise ValueError("No OPENAI_API_KEY or PINECONE_API_KEY provided.")

client = OpenAI(api_key=openai_api_key)
pc = Pinecone(api_key=pinecone_api_key)

index_name = 'hotmart-blog-index'
if index_name not in pc.list_indexes().names():
    print(f"Creating index: {index_name}")
    pc.create_index(
        name=index_name,
        dimension=1536,
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )

index = pc.Index(index_name)    


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


def encode_and_storage(df):
    """
    Faz oembedding e grava os vetores no Pinecone.

    Args:
        df (pandas dataframe): O dataframe com chunks do texto original.
    """
    batch_limit = 100

    for batch in np.array_split(df, len(df) / batch_limit):

        metadatas = [{"text": row['text']} for _, row in batch.iterrows()]
        texts = batch['text'].tolist()

        ids = [str(uuid4()) for _ in range(len(texts))]

        # encode do texto com OpenAI
        response = client.embeddings.create(input=texts, model='text-embedding-3-small')
        embeds = [np.array(x.embedding) for x in response.data]

        # upsert dos vetores no Pinecone
        index.upsert(vectors=zip(ids, embeds, metadatas), namespace=index_name)


@app.route('/embed', methods=['POST'])
def embed_text():
    """
    Lê o arquivo de texto especificado e cria embeddings para o conteúdo,
    salvando-os no Pinecone.
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
        chunks_df = pd.DataFrame({"text": text_chunks})
        encode_and_storage(chunks_df)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'status': 'embeddings saved'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
