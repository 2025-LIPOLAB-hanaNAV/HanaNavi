import os
import requests


def _base() -> str:
    return os.getenv("OPENSEARCH_URL", "https://opensearch:9200").rstrip("/")


def _auth():
    return (os.getenv("OPENSEARCH_USER", "admin"), os.getenv("OPENSEARCH_PASSWORD", "admin"))


def create_synonyms_set(set_id: str, lines: list[str]) -> None:
    url = f"{_base()}/_plugins/_synonyms/{set_id}"
    payload = {"synonyms_set": [ln for ln in lines if ln and not ln.strip().startswith("#")]}
    r = requests.put(url, json=payload, auth=_auth(), verify=False, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"Failed to create synonyms set: {r.status_code} {r.text}")


def recreate_posts_index() -> None:
    try:
        from app.indexer.index_opensearch import _client, ensure_index  # type: ignore
    except Exception as e:
        raise SystemExit(f"OpenSearch client not available: {e}")
    cli = _client()
    idx = os.getenv("OPENSEARCH_INDEX", "posts")
    try:
        if cli.indices.exists(index=idx):
            cli.indices.delete(index=idx)
    except Exception:
        pass
    ensure_index(idx)


def reindex_all() -> None:
    try:
        from app.tools.reindex_opensearch import main as reindex_main  # type: ignore
    except Exception as e:
        raise SystemExit(f"Reindex tool not available: {e}")
    reindex_main()


def main() -> None:
    syn_set = os.getenv("OPENSEARCH_SYNONYMS_SET", "ko_syn")
    syn_path = os.getenv("OPENSEARCH_SYNONYMS_FILE", "/app/config/opensearch/ko_synonyms.txt")
    if not os.path.exists(syn_path):
        raise SystemExit(f"Synonyms file not found: {syn_path}")
    with open(syn_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    print(f"Creating/updating synonyms set '{syn_set}' with {len(lines)} lines...")
    create_synonyms_set(syn_set, lines)
    print("Recreating 'posts' index with synonyms analyzer...")
    recreate_posts_index()
    print("Reindexing all posts from SQLite to OpenSearch...")
    reindex_all()
    print("Done.")


if __name__ == "__main__":
    main()

