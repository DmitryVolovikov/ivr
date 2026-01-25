import argparse
import logging

from app.db.session import get_sessionmaker
from app.services import retrieval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval debug offline.")
    parser.add_argument("--query", required=True, help="Query text to search.")
    parser.add_argument("--limit", type=int, default=5, help="Number of hits to return.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    db = get_sessionmaker()()
    try:
        hits, retriever = retrieval._search_chunks_with_meta_internal(
            db,
            args.query,
            args.limit,
            debug=True,
        )
    finally:
        db.close()

    print(f"Retriever: {retriever}")
    for rank, (chunk_id, score) in enumerate(hits, start=1):
        print(f"{rank:02d}. chunk_id={chunk_id} score={score:.6f}")


if __name__ == "__main__":
    main()
