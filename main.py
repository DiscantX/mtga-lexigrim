import argparse
import sys
from config.settings import Settings
from vectorstores.service_manager import QdrantServiceManager
from vectorstores.qdrant import QdrantVectorStore
from embeddings.fastembed_provider import FastEmbedProvider
from search.engine import CardSearchEngine
from search.cli import InteractiveSearchCLI
from ui.controller import LexiGrimSession
from ui.cli.app import InteractiveCLIShell
from ingestion.pipeline import IngestionPipeline
from ingestion.runner import IngestionRunner
from core.timer import IngestionTimer

def main() -> None:
    parser = argparse.ArgumentParser(description="LexiGrim: MTG Ingestion & Interactive Search CLI")
    parser.add_argument("-s", "--search", action="store_true", help="Launch interactive search REPL")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch unified interactive prompt_toolkit shell")
    parser.add_argument("-r", "--results", type=int, default=3, help="Default result limit for search")
    parser.add_argument("-d", "--deduplicate", action="store_true", help="Enable oracle card deduplication (hide reprint duplicates)")
    parser.add_argument("--corpus", type=str, help="Path to card corpus JSONL for ingestion")
    parser.add_argument("--rules", action="store_true", help="Ingest MTG Comprehensive Rules into mtg_rules collection")
    parser.add_argument("--force", action="store_true", help="Force re-creation or overwrite during ingestion")
    
    args = parser.parse_args()
    
    settings = Settings()
    
    try:
        if args.corpus:
            print(f"Starting data ingestion from {args.corpus}...")
            service_manager = QdrantServiceManager(host=settings.qdrant_host, port=settings.qdrant_port)
            service_manager.ensure_running()
            vector_store = QdrantVectorStore(host=settings.qdrant_host, port=settings.qdrant_port, collection_name=settings.qdrant_collection_name)
            vector_store.initialize_schema()
            embedding_service = FastEmbedProvider(model_name=settings.embedding_model_name)
            timer = IngestionTimer()
            pipeline = IngestionPipeline(vector_store, embedding_service, timer, settings)
            pipeline.run(args.corpus)
        elif args.rules:
            print("Starting MTG Comprehensive Rules ingestion...")
            runner = IngestionRunner(settings=settings)
            runner.run_rules(force=args.force)
        elif args.search:
            print("Launching interactive search REPL...")
            service_manager = QdrantServiceManager(host=settings.qdrant_host, port=settings.qdrant_port)
            service_manager.ensure_running()
            vector_store = QdrantVectorStore(host=settings.qdrant_host, port=settings.qdrant_port, collection_name=settings.qdrant_collection_name)
            embedding_service = FastEmbedProvider(model_name=settings.embedding_model_name)
            engine = CardSearchEngine(vector_store, embedding_service)
            cli = InteractiveSearchCLI(engine, default_limit=args.results, deduplicate_oracle=args.deduplicate)
            cli.run()
        elif args.interactive:
            service_manager = QdrantServiceManager(host=settings.qdrant_host, port=settings.qdrant_port)
            service_manager.ensure_running()
            vector_store = QdrantVectorStore(host=settings.qdrant_host, port=settings.qdrant_port, collection_name=settings.qdrant_collection_name)
            embedding_service = FastEmbedProvider(model_name=settings.embedding_model_name)
            engine = CardSearchEngine(vector_store, embedding_service)
            session = LexiGrimSession(engine, settings)
            session.deduplicate_oracle = args.deduplicate
            session.default_limit = args.results
            shell = InteractiveCLIShell(session)
            shell.run()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n[!] Exiting safely...")
        sys.exit(0)

if __name__ == "__main__":
    main()
