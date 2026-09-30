"""Claim fields and coverage are tested separately from source/span existence."""
import copy,unittest,json,tempfile
from pathlib import Path
from workbench.core import Store
from workbench.rules import evidence_result
class TypedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.docs=[
          {"id":"L1","logical_id":"L","revision":1,"site":"A","roles":["it","reviewer"],"incident_id":"I1","kind":"log","title":"log","timestamp":"2026-09-30T06:00:00Z","content":"code=INV_CONNECT http_status=503 duration_ms=0.4"},
          {"id":"C1","logical_id":"C","revision":1,"site":"A","roles":["it","reviewer"],"incident_id":"I1","kind":"configuration","title":"config","timestamp":"2026-09-30T06:00:00Z","content":"inventory.endpoint=http://127.0.0.1:19083/inventory expected_port=19082"},
          {"id":"H1","logical_id":"H","revision":1,"site":"A","roles":["it","reviewer"],"incident_id":"I1","kind":"trace","title":"health","timestamp":"2026-09-30T06:00:00Z","content":"inventory process status=active; health HTTP200"}]
        corpus={"incidents":[{"id":"I1","site":"A","title":"장애","ticket":"INV_CONNECT","service":"mes-orders","timestamp":"2026-09-30T06:00:00Z","status":"open"}],"documents":self.docs}
        path=root/"corpus.json";path.write_text(json.dumps(corpus));self.store=Store(path,root/"state.db")
        self.valid=evidence_result(self.docs)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def reject_mutation(self,mutate):
        output=copy.deepcopy(self.valid);mutate(output)
        result=self.store._validate_output(output,self.docs)
        self.assertFalse(result["gate"]["passed"])
        # Citations still exist: rejection is about claim support rather than absent spans.
        self.assertGreater(len(result["citations"]),0)
    def test_supported_typed_fields_and_coverage(self):
        result=self.store._validate_output(self.valid,self.docs)
        self.assertTrue(result["gate"]["passed"]);self.assertEqual(len(result["facts"]),7)
    def test_actual_quote_attached_to_false_claim(self):
        self.reject_mutation(lambda x:x["facts"][0].update(text="서비스 장애가 없다는 진단이 검증되었습니다."))
    def test_different_entity_rejected(self):
        self.reject_mutation(lambda x:x["facts"][0]["observation"].update(entity="other-service.code"))
    def test_numeric_inversion_rejected(self):
        self.reject_mutation(lambda x:next(f for f in x["facts"] if f["observation"]["entity"]=="mes-orders.http_status")["observation"].update(value=200))
    def test_negation_inversion_rejected(self):
        self.reject_mutation(lambda x:x["facts"][0]["observation"].update(polarity="denied"))
    def test_past_observation_time_rejected(self):
        self.reject_mutation(lambda x:x["facts"][0]["observation"].update(observed_at="2025-01-01T00:00:00Z"))
    def test_important_fact_coverage_rejected(self):
        self.reject_mutation(lambda x:x["facts"].pop())
    def test_no_input_evidence_allows_empty_facts(self):
        output=evidence_result([])
        self.assertEqual(output["facts"],[]);self.assertIn("근거가 부족",output["unknowns"][0])
        self.assertFalse(self.store._validate_output(output,[])["gate"]["passed"])
if __name__=="__main__":unittest.main()
