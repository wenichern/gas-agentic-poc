"""Swappable retrieval. LocalRetriever = zero-cost TF-IDF over ./data. BedrockKBRetriever = Bedrock Knowledge Base."""
import math, os, pathlib, re
from collections import Counter

DATA = pathlib.Path(__file__).parent / "data"
TOK = re.compile(r"[a-z0-9]+")


def chunk_markdown(text, source):
    """Split a markdown doc on '## ' headings. Chunk id = '<DOC> §<section>' (e.g. 'SOP-LS-01 §3.1')."""
    doc_id = re.match(r"#\s+(\S+)", text).group(1)
    chunks = []
    for part in re.split(r"(?m)^## ", text)[1:]:
        head, _, body = part.partition("\n")
        sec = head.split()[0]
        chunks.append({"id": f"{doc_id} §{sec}", "source": source, "heading": head.strip(), "text": body.strip()})
    return chunks


class LocalRetriever:
    def __init__(self, data_dir=DATA):
        self.kinds = {}
        for kind in ("regulations", "procedures"):
            chunks = []
            for p in sorted((data_dir / kind).glob("*.md")):
                chunks += chunk_markdown(p.read_text(), p.name)
            self.kinds[kind] = chunks
        allc = [c for v in self.kinds.values() for c in v]
        df = Counter(t for c in allc for t in set(TOK.findall((c["heading"] + " " + c["text"]).lower())))
        self.idf = {t: math.log((1 + len(allc)) / (1 + n)) + 1 for t, n in df.items()}

    def _vec(self, text):
        tf = Counter(TOK.findall(text.lower()))
        return {t: (1 + math.log(n)) * self.idf.get(t, 1.0) for t, n in tf.items()}

    def search(self, query, kind, k=3):
        q = self._vec(query)
        qn = math.sqrt(sum(v * v for v in q.values())) or 1
        out = []
        for c in self.kinds[kind]:
            d = self._vec(c["heading"] + " " + c["text"])
            dn = math.sqrt(sum(v * v for v in d.values())) or 1
            score = sum(q[t] * d.get(t, 0) for t in q) / (qn * dn)
            if score > 0:
                out.append({**c, "score": round(score, 3)})
        return sorted(out, key=lambda x: -x["score"])[:k]


class BedrockKBRetriever:
    """Needs a Knowledge Base whose S3 prefixes are regulations/ and procedures/ (see docs/KB_SETUP.md)."""

    def __init__(self, kb_id):
        import boto3
        self.kb_id = kb_id
        self.client = boto3.client("bedrock-agent-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))

    def search(self, query, kind, k=3):
        r = self.client.retrieve(knowledgeBaseId=self.kb_id, retrievalQuery={"text": query},
                                 retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": k * 3}})
        out = []
        for item in r["retrievalResults"]:
            uri = item.get("location", {}).get("s3Location", {}).get("uri", "")
            if f"/{kind}/" not in uri:
                continue
            text = item["content"]["text"]
            m = re.match(r"#\s+(\S+)", text)  # chunk may or may not include the doc title
            doc = m.group(1) if m else pathlib.PurePosixPath(uri).stem
            sec = re.search(r"(?m)^## (\S+)", text)
            cid = f"{doc} §{sec.group(1)}" if sec else doc
            out.append({"id": cid, "source": uri, "heading": "", "text": text[:1200], "score": round(item.get("score", 0), 3)})
        return out[:k]


def get_retriever():
    kb = os.getenv("KB_ID")
    return BedrockKBRetriever(kb) if kb else LocalRetriever()
