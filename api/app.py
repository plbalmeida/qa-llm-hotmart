import json
import os
from flask import Flask, request, jsonify
from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec


app = Flask(__name__)

openai_api_key = os.getenv('OPENAI_API_KEY')
pinecone_api_key = os.getenv('PINECONE_API_KEY')

if not openai_api_key or not pinecone_api_key:
    raise ValueError("No OPENAI_API_KEY or PINECONE_API_KEY must be set.")

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


def retrieve(query, top_k, namespace, emb_model):
    """
    Recupera documentos do Pinecone com base em uma consulta usando embeddings.

    Args:
        query (str): A string de consulta.
        top_k (int): O número de principais documentos a serem recuperados.
        namespace (str): O namespace no índice do Pinecone.
        emb_model (str): O modelo de embedding a ser usado.

    Returns:
        list: Uma lista de documentos recuperados.
    """
    query_response = client.embeddings.create(
        input=query,
        model=emb_model
    )

    query_emb = query_response.data[0].embedding
    docs = index.query(vector=query_emb, top_k=top_k, namespace=namespace, include_metadata=True)

    retrieved_docs = []
    for doc in docs['matches']:
        retrieved_docs.append(doc['metadata']['text'])

    return retrieved_docs


def prompt_with_context_builder(query, docs):
    """
    Constrói um prompt com contexto para a API da OpenAI.

    Args:
        query (str): A consulta do usuário.
        docs (list): Uma lista de documentos a serem usados como contexto.

    Returns:
        str: O prompt construído.
    """
    delim = '\n\n---\n\n'
    prompt_start = 'Responda a questão baseado no contexto a seguir.\n\nContexto:\n'
    prompt_end = f'\n\nQuestão: {query}\nResposta:'

    prompt = prompt_start + delim.join(docs) + prompt_end
    return prompt


@app.route('/qa', methods=['POST'])
def qa():
    """
    Manipula a rota /qa para responder perguntas.

    Returns:
        flask.Response: A resposta JSON contendo a resposta ou uma mensagem de erro.
    """
    data = request.json
    question = data.get('question')

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    # consulta no Pinecone para encontrar embeddings relevantes
    documents = retrieve(
        query=question,
        top_k=3,
        namespace=index_name,
        emb_model="text-embedding-3-small"
    )

    if not documents:
        return jsonify({'error': 'No relevant embeddings found'}), 404

    prompt_with_context = prompt_with_context_builder(
        query=question,
        docs=documents
    )

    # usa o OpenAI para gerar a resposta
    sys_prompt = "Você é um assistente prestativo que sempre responde a perguntas."

    res = client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt_with_context}
        ],
        temperature=0
    )

    answer = res.choices[0].message.content.strip()
    response_json = json.dumps({'answer': answer}, ensure_ascii=False, indent=4)
    return app.response_class(response=response_json, status=200, mimetype='application/json')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
