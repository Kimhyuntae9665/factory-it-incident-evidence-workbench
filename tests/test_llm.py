import unittest
from unittest.mock import patch
from workbench import llm
class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.incident={"ticket":"합성 주문 오류"}
        self.docs=[{"id":"D1","revision":2,"title":"log","kind":"log","timestamp":"2026-09-30T06:00:00Z","content":"code=ORDER_OK"}]
        self.valid={"observations":{"code":"ORDER_OK","http_status":None,"duration_ms":None,"configured_port":None,"expected_port":None,"dependency_status":None,"health_http_status":None},"support":{"document_id":"D1","quote":"code=ORDER_OK"}}
    def analyze(self,value):
        with patch.object(llm,"request_json",return_value=(value,{}, {},{})):
            return llm.analyze_with_model(self.incident,self.docs,"원인 근거")
    def test_inline_citation_compiles_to_verified_source(self):
        result=self.analyze(self.valid)
        self.assertEqual(result["facts"][0]["source_ids"],["D1"])
        self.assertEqual(result["citations"][0]["revision"],2)
        self.assertEqual(result["citations"][0]["quote"],self.docs[0]["content"])
    def test_malformed_model_shapes_always_fail_closed(self):
        import copy
        values=[None,[],True,{},dict(self.valid,observations=None),dict(self.valid,support=None),dict(self.valid,support=[])]
        for field,value in (("document_id",[]),("quote",None),("quote","invented"),("document_id","B-private")):
            item=copy.deepcopy(self.valid);item["support"][field]=value;values.append(item)
        item=copy.deepcopy(self.valid);item["observations"]["code"]="INV_CONNECT";values.append(item)
        for value in values:
            with self.subTest(value=value),self.assertRaises(RuntimeError):self.analyze(value)
    def test_malformed_transport_envelopes_fail_closed(self):
        from unittest.mock import MagicMock
        import json
        for raw in (None, {"message":None}, {"message":{"content":"{}","thinking":None}}):
            response=MagicMock();response.__enter__.return_value=response;response.read.return_value=json.dumps(raw).encode()
            with self.subTest(raw=raw),patch.object(llm.urllib.request,"urlopen",return_value=response),self.assertRaises(RuntimeError):
                llm.request_json([],{})
    def test_budget_overflow_prevents_any_inference(self):
        with patch.object(llm,"request_json") as call,self.assertRaises(RuntimeError):
            llm.analyze_with_model(self.incident,self.docs,"x"*1201)
        call.assert_not_called()
    def test_single_flight_rejects_without_queue(self):
        llm._lock.acquire()
        try:
            with self.assertRaisesRegex(RuntimeError,"inference_busy"):llm.request_json([],{})
        finally:llm._lock.release()
    def test_cross_process_inference_lease_blocks_duplicate(self):
        import tempfile,subprocess,sys
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            lock=Path(temp)/"inference.lock"
            script="import fcntl,sys;f=open(sys.argv[1],\"a\");fcntl.flock(f,fcntl.LOCK_EX);print(\"ready\",flush=True);sys.stdin.read()"
            process=subprocess.Popen([sys.executable,"-c",script,str(lock)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(process.stdout.readline().strip(),"ready")
                with patch.object(llm,"INFERENCE_LOCK",lock),patch.object(llm.urllib.request,"urlopen") as call,self.assertRaisesRegex(RuntimeError,"inference_busy"):llm.request_json([],{})
                call.assert_not_called()
            finally:
                process.stdin.close();process.wait(timeout=5);process.stdout.close()
    def test_timeout_latches_and_prevents_duplicate_request(self):
        original=llm._disabled_reason;llm._disabled_reason=None
        try:
            with patch.object(llm.urllib.request,"urlopen",side_effect=TimeoutError("test")) as call:
                with self.assertRaises(TimeoutError):llm.request_json([],{})
                with self.assertRaisesRegex(RuntimeError,"inference_disabled"):llm.request_json([],{})
                self.assertEqual(call.call_count,1)
        finally:llm._disabled_reason=original
if __name__=="__main__":unittest.main()
