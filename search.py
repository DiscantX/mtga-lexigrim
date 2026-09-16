"""Legacy search bridge module. Launches interactive search REPL when run directly."""

if __name__ == "__main__":
    from search.cli import InteractiveSearchCLI
    from search.engine import CardSearchEngine
    from vectorstores.qdrant import QdrantVectorStore
    from embeddings.fastembed_provider import FastEmbedProvider
    from vectorstores.service_manager import QdrantServiceManager
    from config.settings import Settings

    settings = Settings()
    service_manager = QdrantServiceManager(host=settings.qdrant_host, port=settings.qdrant_port)
    service_manager.ensure_running()
    vector_store = QdrantVectorStore(host=settings.qdrant_host, port=settings.qdrant_port, collection_name=settings.qdrant_collection_name)
    embedding_service = FastEmbedProvider(model_name=settings.embedding_model_name)
    
    engine = CardSearchEngine(vector_store, embedding_service)
    cli = InteractiveSearchCLI(engine)
    cli.run()
