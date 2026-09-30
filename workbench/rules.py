"""Observable-only diagnostic baseline; never reads expected labels."""
import re
from urllib.parse import urlsplit
LABELS={"normal":"정상 주문 조회","address_mismatch":"접속 주소 불일치","dependency_unavailable":"의존 서비스 가용성 문제","latency":"의존 서비스 지연","insufficient":"근거 부족"}
def assessment(documents):
    joined="\n".join(d["content"] for d in documents if d["kind"] in ("log","configuration","trace"))
    if "code=ORDER_OK" in joined:return "normal"
    match=re.search(r"inventory\.endpoint=(\S+).*?expected_port=(\d+)",joined)
    mismatch=False
    if match:
        try:mismatch=urlsplit(match[1]).port!=int(match[2])
        except ValueError:pass
    if "code=INV_CONNECT" in joined and mismatch:return "address_mismatch"
    if "code=INV_CONNECT" in joined and "status=inactive" in joined and match and not mismatch:return "dependency_unavailable"
    if "code=INV_TIMEOUT" in joined and "status=active" in joined:return "latency"
    return "insufficient"
def evidence_result(documents,category=None):
    actual=assessment(documents);category=category or actual
    facts=[];citations=[];counter=[]
    def add(document,text,field):
        quote=document["content"][:350]
        field.append({"text":text,"source_ids":[document["id"]]})
        citation={"document_id":document["id"],"revision":document["revision"],"quote":quote,"title":document["title"]}
        if citation not in citations:citations.append(citation)
    for doc in documents:
        content=doc["content"]
        if doc["kind"]=="log" and "code=" in content:
            code=re.search(r"code=(\w+)",content)
            add(doc,"MES 주문 조회 로그의 오류 코드: "+code.group(1),facts)
        elif doc["kind"]=="configuration":
            match=re.search(r"inventory\.endpoint=(\S+).*?expected_port=(\d+)",content)
            if match:
                port=urlsplit(match[1]).port
                add(doc,"설정 포트 %s / 기준 포트 %s"%(port,match[2]),facts)
        elif doc["kind"]=="trace" and "inventory process status=" in content:
            active="status=active" in content
            add(doc,"의존 서비스 상태: "+("실행 중, 상태 조회 정상" if active else "비활성, 상태 조회 불가"),facts)
            if category in ("address_mismatch","latency") and active:add(doc,"실행 중인 정상 상태 조회는 서비스 전체 단절 가설의 반증입니다.",counter)
        if len(facts)>=3:break
    if not facts:
        for doc in documents[:3]:
            add(doc,"원문에 기록된 관측 내용을 검토해야 합니다.",facts)
    facts=observed_facts(documents)
    for fact in facts:
        observation=fact["observation"]
        document=next(d for d in documents if d["id"]==observation["document_id"])
        citation={"document_id":document["id"],"revision":document["revision"],"quote":document["content"][:350],"title":document["title"]}
        if citation not in citations:citations.append(citation)
    hypotheses=[]
    if category not in ("normal","insufficient"):
        ids=[c["document_id"] for c in citations]
        hypotheses=[{"text":LABELS[category]+" 가능성이 있습니다. 최종 원인은 추가 확인이 필요합니다.","source_ids":ids}]
    unknowns=["최종 근본 원인과 복구 결과는 확인되지 않았습니다."]
    if category=="insufficient":unknowns.insert(0,"확인할 근거가 부족합니다. 기술 로그와 상태 조회를 추가 확인하세요.")
    return {"summary":LABELS[category]+"의 관측 근거를 정리했습니다. 사람의 검토가 필요합니다.","facts":facts,"hypotheses":hypotheses,"counterevidence":counter,"unknowns":unknowns,"citations":citations,"metrics":{"assessment":category,"facts_origin":"deterministic_observations","synthetic":True}}

def observed_facts(documents):
    """Typed scalar facts with exact original spans and observation time."""
    facts=[]
    for doc in documents:
        if doc["kind"] not in ("log","configuration","trace"):continue
        content=doc["content"];values=[]
        if doc["kind"]=="log":
            for name,pattern,unit,convert in (
                ("mes-orders.code",r"code=(\w+)","code",str),
                ("mes-orders.http_status",r"http_status=(\d+)","http_status",int),
                ("mes-orders.duration_ms",r"duration_ms=([0-9.]+)","ms",float)):
                match=re.search(pattern,content)
                if match:values.append((name,convert(match[1]),unit,match[0]))
        elif doc["kind"]=="configuration":
            match=re.search(r"inventory\.endpoint=(\S+)",content)
            if match:
                try:port=urlsplit(match[1]).port
                except ValueError:port=None
                if port is not None:values.append(("inventory.configured_port",port,"port",match[0]))
            match=re.search(r"expected_port=(\d+)",content)
            if match:values.append(("inventory.expected_port",int(match[1]),"port",match[0]))
        elif doc["kind"]=="trace":
            match=re.search(r"inventory process status=(active|inactive)",content)
            if match:values.append(("inventory.process_status",match[1],"state",match[0]))
            match=re.search(r"health HTTP(\d+)",content)
            if match:values.append(("inventory.health_http_status",int(match[1]),"http_status",match[0]))
        for entity,value,unit,quote in values:
            observation={"entity":entity,"value":value,"unit":unit,"polarity":"affirmed","observed_at":doc["timestamp"],"document_id":doc["id"],"revision":doc["revision"],"quote":quote}
            facts.append({"text":fact_text(observation),"source_ids":[doc["id"]],"observation":observation})
    if not facts:
        for doc in documents[:3]:
            observation={"entity":"source.document","value":doc["id"],"unit":"identifier","polarity":"recorded","observed_at":doc["timestamp"],"document_id":doc["id"],"revision":doc["revision"],"quote":doc["content"][:350]}
            facts.append({"text":fact_text(observation),"source_ids":[doc["id"]],"observation":observation})
    return facts
def fact_text(observation):
    labels={"mes-orders.code":"MES 주문 조회 코드","mes-orders.http_status":"MES 응답 상태","mes-orders.duration_ms":"MES 관측 응답 시간","inventory.configured_port":"의존 서비스 설정 포트","inventory.expected_port":"의존 서비스 기준 포트","inventory.process_status":"의존 서비스 관측 상태","inventory.health_http_status":"의존 서비스 상태 조회","source.document":"접근 가능한 원문 문서"}
    return labels[observation["entity"]]+": "+str(observation["value"])+" ("+observation["unit"]+")"
