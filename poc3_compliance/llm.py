import json, os, re


def get_client(mock):
    if mock:
        return MockBedrock()
    import boto3
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))


class MockBedrock:
    """Offline stand-in. It really calls the retrieval tools and compares numbers, but it is regex logic, not reasoning."""

    def converse(self, **kw):
        msgs = kw["messages"]
        first_text = msgs[0]["content"][0]["text"]
        calls, results = {}, []
        for m in msgs:
            for b in m["content"] if isinstance(m["content"], list) else []:
                if "toolUse" in b: calls[b["toolUse"]["toolUseId"]] = b["toolUse"]
                if "toolResult" in b: results.append(b["toolResult"])
        reqs = re.findall(r"## (R\d+) ([^\n]+)\n([^\n#]+)", first_text)
        bid = re.search(r"#\s+(\S+)", first_text).group(1)

        if not results:
            tcs = []
            for rid, topic, _ in reqs:
                tcs += [("search_procedures", {"query": topic}), ("search_regulations", {"query": topic})]
            tcs.append(("get_deadlines", {}))
            return {"stopReason": "tool_use", "output": {"message": {"role": "assistant", "content": [
                {"toolUse": {"toolUseId": f"m{i}", "name": n, "input": a}} for i, (n, a) in enumerate(tcs)]}}}

        by_topic = {}
        deadlines = []
        for r in results:
            tu = calls[r["toolUseId"]]
            data = r["content"][0]["json"]
            if tu["name"] == "search_procedures":
                by_topic[tu["input"]["query"]] = data["results"]
            if tu["name"] == "get_deadlines":
                deadlines = data["items"]

        impacted, gaps, actions = [], [], []
        for rid, topic, text in reqs:
            hit = (by_topic.get(topic) or [None])[0]
            new = re.search(r"(\d+) (months?|years?)", text)
            cite_b = f"{bid} §{rid}"
            if not hit:
                gaps.append({"description": f"{rid} {topic}: no matching procedure found", "severity": "HIGH", "citations": [cite_b]})
                continue
            cur = re.search(r"(\d+) (months?|years?)", hit["text"])
            impacted.append({"procedure": hit["id"], "why": f"Covers '{topic}'", "citations": [cite_b, hit["id"]]})
            if cur and new and (cur.group(1), cur.group(2)) != (new.group(1), new.group(2)):
                d = f"{rid} {topic}: procedure says {cur.group(0)}, bulletin requires {new.group(0)}"
                gaps.append({"description": d, "severity": "HIGH", "citations": [cite_b, hit["id"]]})
                actions.append({"action": f"Revise {hit['id']} to {new.group(0)}", "owner_role": "Procedure owner",
                                "due": "before effective date", "citations": [cite_b, hit["id"]]})
        eff = re.search(r"Effective date: (\S+)", first_text); due = re.search(r"report due: (\S+)", first_text)
        dl = [{"item": "Rule effective", "date": eff.group(1), "source": f"{bid} §{reqs[0][0]}"}] if eff and reqs else []
        if due and reqs: dl.append({"item": "Compliance report due", "date": due.group(1), "source": f"{bid} §{reqs[0][0]}"})
        dl += [{"item": i["item"], "date": i["date"], "source": f"CAL: {i['item']}"} for i in deadlines]
        final = {"bulletin_summary": f"{bid}: {len(reqs)} requirements reviewed, {len(gaps)} gap(s) found (mock).",
                 "impacted_procedures": impacted, "gaps": gaps, "deadlines": dl, "draft_actions": actions,
                 "status": "DRAFT - requires compliance officer review"}
        return {"stopReason": "end_turn", "output": {"message": {"role": "assistant", "content": [{"text": json.dumps(final)}]}}}
