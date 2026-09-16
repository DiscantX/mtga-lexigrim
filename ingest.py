import argparse
import sys
from config.settings import Settings, settings
from core.timer import IngestionTimer
from embeddings.fastembed_provider import FastEmbedProvider
from ingestion.pipeline import IngestionPipeline
from vectorstores.qdrant import QdrantVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="MTGA Expert Data Ingestion CLI Runner")
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=settings.data_corpus_path,
        help="Path to the JSONL data corpus file",
    )
    args = parser.parse_args()

    app_settings = Settings()
    timer = IngestionTimer()
    vector_store = QdrantVectorStore()
    embedding_service = FastEmbedProvider()

    pipeline = IngestionPipeline(
        vector_store=vector_store,
        embedding_service=embedding_service,
        timer=timer,
        settings=app_settings,
    )

    pipeline.run(args.file)


if __name__ == "__main__":
    main()
