
# Langchain dependencies
from langchain.text_splitter import RecursiveCharacterTextSplitter # Importing text splitter from Langchain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document # Importing Document schema from Langchain
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import os # Importing os module for operating system functionalities
import shutil # Importing shutil module for high-level file operations
from langchain_community.document_loaders import PyPDFDirectoryLoader


from langchain_community.vectorstores import FAISS

from app.db_models import Assessment
DATA_PATH = "app/static/default_files"

def load_documents(assessment_id):
  

  #assessment = Assessment.query.filter_by(id=assessment_id).first()

  #documents = []
  #for file in assessment.files:
      #doc = Document(
          #page_content=file.content,
          #metadata={"source": file.filename, "file_id": file.id}
      #)
      #documents.append(doc)
  #return documents
  # Initialize PDF loader with specified directory
  document_loader = PyPDFDirectoryLoader(DATA_PATH)
  # Load PDF documents and return them as a list of Document objects
  docs = document_loader.load()
  with open ('debug.txt','a') as f:
    f.write(str(docs[0]))
    f.write('\n') 
  return document_loader.load()

def split_text(documents: list[Document]):
  """
  Split the text content of the given list of Document objects into smaller chunks.
  Args:
    documents (list[Document]): List of Document objects containing text content to split.
  Returns:
    list[Document]: List of Document objects representing the split text chunks.
  """
  # Initialize text splitter with specified parameters
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300, # Size of each chunk in characters
    chunk_overlap=100, # Overlap between consecutive chunks
    length_function=len, # Function to compute the length of the text
    add_start_index=True, # Flag to add start index to each chunk
  )

  # Split documents into smaller chunks using text splitter
  chunks = text_splitter.split_documents(documents)

  return chunks # Return the list of split text chunks

def create_vector_store(chunks):
    embedding_function = HuggingFaceEmbeddings()
    return FAISS.from_documents(chunks, embedding_function)


PROMPT_TEMPLATE = """
Answer the question based only on the following context:
{context}
- -
Question: Generate a {question_type} question based on this learning objective.'{learning_objective}' State the Question and the Answer
in a python dictionary format separating the question and answer. Make the answer have a limit of 5 sentences.
"""

def query_rag(question_type,learning_obj,assessment_id):
  """
  Query a Retrieval-Augmented Generation (RAG) system using Chroma database and OpenAI.
  Args:
    - query_text (str): The text to query the RAG system with.
  Returns:
    - formatted_response (str): Formatted response including the generated text and sources.
    - response_text (str): The generated response text.
  """

  documents = load_documents(assessment_id)
  chunks = split_text(documents)
  vector_store = create_vector_store(chunks)
  
  # Retrieving the context from the DB using similarity search
  results = vector_store.similarity_search_with_relevance_scores(learning_obj, k=3)

  # Check if there are any matching results or if the relevance score is too low
  if len(results) == 0 or results[0][1] < 0.7:
    print(f"Unable to find matching results.")

  print(f"NUMBER OF PAGES: {len(results)}")
  for doc,score in results:
    print(f"PAGE CONTENT: {doc.page_content} AND SCORE: {score}")

  # Combine context from matching documents
  context_text = "\n\n - -\n\n".join([doc.page_content for doc, _score in results])
  
  # Create prompt template using context and query text
  prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
  prompt = prompt_template.format(context=context_text, question_type=question_type,learning_objective=learning_obj)
  
  #repo_id = "Qwen/Qwen2-1.5B-Instruct"
  repo_id = "microsoft/Phi-3-mini-4k-instruct"
 
  llm = ChatOllama(model="phi3:mini", temperature=0.0) 

  # Generate response text based on the prompt
  response_text = llm.predict(prompt)

  # Get sources of the matching documents
  sources = [doc.metadata.get("source", None) for doc, _score in results]

  # Format and return response including generated text and sources
  formatted_response = f"Response: {response_text}\nSources: {sources}"

  return formatted_response, response_text
