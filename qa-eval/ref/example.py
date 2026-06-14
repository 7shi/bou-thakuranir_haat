# EmbeddingGemma prompt conventions (prepend to the input text):
#   Query (retrieval):    task: search result | query: {content}
#   Document (retrieval):  title: {title | "none"} | text: {content}
#       Providing a real title improves performance over "none".
#   Other query task types (replace "search result"):
#       question answering / fact checking / classification /
#       clustering / sentence similarity / code retrieval
# Notes: 768-d output (truncatable to 512/256/128 via MRL); 2K-token input limit.

from ollama import embed

documents = [
  'The sky is blue because of Rayleigh scattering.',
  'Blue light is scattered more than other colors.',
  'I like to eat pizza on Fridays.',
]

query = 'Why is the sky blue?'

doc_inputs = [f'title: "none" | text: {doc}' for doc in documents]
doc_response = embed(model='embeddinggemma', input=doc_inputs)
print('Documents:')
for i, embedding in enumerate(doc_response['embeddings']):
  print(f'  [{i}] dim={len(embedding)} first5={embedding[:5]}')

query_input = f'task: search result | query: {query}'
query_response = embed(model='embeddinggemma', input=query_input)
print('Query:')
print(f'  dim={len(query_response["embeddings"][0])} first5={query_response["embeddings"][0][:5]}')
