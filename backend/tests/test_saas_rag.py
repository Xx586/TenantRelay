from mcp.knowledge_base import KnowledgeBase


class FakeCollection:
    def __init__(self):
        self.kwargs = None

    def query(self, **kwargs):
        self.kwargs = kwargs
        return {
            "documents": [["tenant-safe-content"]],
            "metadatas": [[{
                "title": "Private guide", "tenant_id": "tenant-a", "product": "AcmeCloud",
                "version": "v2", "source": "docs/private",
            }]],
            "distances": [[0.1]],
        }


def test_rag_query_contains_tenant_product_and_version_filters():
    kb = KnowledgeBase.__new__(KnowledgeBase)
    kb._collection = FakeCollection()
    result = kb.search("upload", filters={
        "tenant_id": "tenant-a", "product": "AcmeCloud", "version": "v2",
    })
    where = kb._collection.kwargs["where"]
    tenant_filter = {
        "$or": [
            {"tenant_id": "tenant-a"},
            {"$and": [{"tenant_id": "public"}, {"visibility": "public"}]},
        ]
    }
    assert tenant_filter in where["$and"]
    assert {"product": "AcmeCloud"} in where["$and"]
    assert {"version": "v2"} in where["$and"]
    assert result[0]["source"] == "docs/private"
