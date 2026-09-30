"""Small fixed heldout evaluation, real Ollama and observable baseline separated."""
import json,time,threading,hashlib,subprocess
from pathlib import Path
from workbench.core import Store
from scripts.model_readiness import snapshot
ROOT=Path(__file__).resolve().parents[1]
def main():
    # The only labels read occur in this evaluator, never runtime.
    truth_path=ROOT/"artifacts/heldout_expected.json"
    if not truth_path.exists():truth_path=ROOT/"evaluations/fixed_expected.json"
    truth=json.loads(truth_path.read_text())
    mapped={"normal":"normal","wrong_endpoint":"address_mismatch","dependency_down":"dependency_unavailable","delay":"latency"}
    heldout=[x for x in truth if x["split"]=="heldout"]
    out=ROOT/"artifacts"/time.strftime("fixed-regression-%Y%m%dT%H%M%SZ",time.gmtime());out.mkdir(parents=True,exist_ok=True)
    store=Store(ROOT/"data/corpus.json",out/"evaluation.sqlite3")
    principal=store.session("B-reviewer")["principal"];results=[];samples=[];stop=threading.Event()
    def monitor():
        while not stop.is_set():samples.append(snapshot());stop.wait(1)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    print(subprocess.check_output(["nvidia-smi","--query-compute-apps=pid,process_name,used_memory","--format=csv,noheader"],text=True),flush=True)
    try:
        for case in heldout:
            item={"incident_id":case["incident_id"],"expected_category":mapped[case["expected"]]}
            for mode in ("baseline","model"):
                result=store.analyze(principal,case["incident_id"],"관측 근거를 분류하고 반증과 미확인을 보여주세요.",mode)
                correct=result["metrics"].get("assessment")==item["expected_category"]
                passed=result["gate"]["passed"] and correct and (mode=="baseline" or result["mode"]=="ollama")
                item[mode]={"passed":passed,"category_correct":correct,"analysis":result}
                print(json.dumps({"incident_id":case["incident_id"],"mode":mode,"passed":passed,"effective_mode":result["mode"],"category":result["metrics"].get("assessment"),"latency_ms":result["metrics"]["total_ms"]}),flush=True)
            results.append(item)
            (out/(case["incident_id"]+".json")).write_text(json.dumps(item,ensure_ascii=False,indent=2))
    finally:
        stop.set();thread.join(3);samples.append(snapshot());store.close()
        summary={"synthetic":True,"split":"fixed_synthetic_regression_previously_observed_not_independent_generalization","corpus_sha256":hashlib.sha256((ROOT/"data/corpus.json").read_bytes()).hexdigest(),"baseline_passed":sum(r["baseline"]["passed"] for r in results),"model_extraction_passed":sum(r["model"]["passed"] for r in results),"causal_labels_origin":"deterministic_provisional_rules","independent_model_diagnosis_validated":False,"total":len(results),"results":results,"peak_gpu_used_mib":max(int(s["gpu"].split(",")[0]) for s in samples),"minimum_mem_available_kib":min(s["meminfo"]["MemAvailable"] for s in samples)}
        (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
        (out/"resources.json").write_text(json.dumps(samples,indent=2))
        print(json.dumps({k:v for k,v in summary.items() if k!="results"}),flush=True)
if __name__=="__main__":main()
