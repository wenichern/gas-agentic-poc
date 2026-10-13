import json, pathlib
from retriever import get_retriever, chunk_markdown, DATA

TOOL_SPEC = {"tools": [
    {"toolSpec": {"name": "search_regulations", "description": "Search the regulation corpus. Returns chunks with citable ids.",
      "inputSchema": {"json": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}},
    {"toolSpec": {"name": "search_procedures", "description": "Search internal SOPs/procedures. Returns chunks with citable ids.",
      "inputSchema": {"json": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}}},
    {"toolSpec": {"name": "get_deadlines", "description": "Internal compliance calendar items.",
      "inputSchema": {"json": {"type": "object", "properties": {}}}}},
]}


class Toolbox:
    """Holds the retriever and remembers every chunk id the model has actually seen (used to verify citations)."""

    def __init__(self, bulletin_text=None):
        self.retriever = get_retriever()
        self.seen = set()
        if bulletin_text:
            self.seen |= {c["id"] for c in chunk_markdown(bulletin_text, "bulletin")}

    def _search(self, kind, query):
        hits = self.retriever.search(query, kind)
        self.seen |= {h["id"] for h in hits}
        return {"results": [{"id": h["id"], "text": h["text"], "score": h["score"]} for h in hits]}

    def dispatch(self, name, args):
        try:
            if name == "search_regulations": return self._search("regulations", args["query"])
            if name == "search_procedures": return self._search("procedures", args["query"])
            if name == "get_deadlines":
                items = json.loads((DATA / "deadlines.json").read_text())
                self.seen |= {f"CAL: {i['item']}" for i in items}
                return {"items": items}
            return {"error": f"unknown tool {name}"}
        except Exception as e:
            return {"error": str(e)}
