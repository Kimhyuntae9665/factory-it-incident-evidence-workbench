import unittest
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch
from workbench import llm
class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.lock_root=Path(temporary.name)
        lease_patch=patch.object(llm,"INFERENCE_LOCK",self.lock_root/"inference.lock")
        lease_patch.start()
        self.addCleanup(lease_patch.stop)
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
    def test_default_lock_same_for_shallow_and_deep_clones(self):
        import importlib.util
        source=Path(llm.__file__).read_text(encoding="utf-8")
        home=self.lock_root/"user"
        paths=[]
        for relative in ("clone/workbench/llm.py","very/deep/projects/clone/workbench/llm.py"):
            clone=self.lock_root/relative
            clone.parent.mkdir(parents=True)
            clone.write_text(source,encoding="utf-8")
            spec=importlib.util.spec_from_file_location("clone_client",clone)
            module=importlib.util.module_from_spec(spec)
            with patch.dict(os.environ,{},clear=True),patch.object(Path,"home",return_value=home):
                spec.loader.exec_module(module)
            paths.append(module.INFERENCE_LOCK)
        self.assertEqual(paths[0],paths[1])
        self.assertEqual(paths[0],home/".cache/ax-lab/runtime/inference.lock")
        self.assertFalse(paths[0].exists())

    def test_default_user_cache_creation_private_and_writable(self):
        home=self.lock_root/"user"
        home.mkdir()
        lock=llm._configured_inference_lock({},home)
        with patch.object(llm,"INFERENCE_LOCK",lock):
            lease=llm._open_inference_lease()
            lease.write("synthetic lock test")
            lease.close()
        self.assertEqual(lock.read_text(),"synthetic lock test")
        self.assertEqual(stat.S_IMODE(lock.stat().st_mode),0o600)
        for directory in (home/".cache",home/".cache/ax-lab",lock.parent):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode),0o700)

    def test_absolute_lock_override_and_relative_rejection(self):
        configured=self.lock_root/"explicit"/"inference.lock"
        self.assertEqual(llm._configured_inference_lock({"AX_LAB_INFERENCE_LOCK":str(configured)},self.lock_root),configured)
        for value in ("relative/inference.lock","~/inference.lock",""):
            with self.subTest(value=value),self.assertRaisesRegex(RuntimeError,"inference_lock_configuration_invalid"):
                llm._configured_inference_lock({"AX_LAB_INFERENCE_LOCK":value},self.lock_root)
        with patch.object(llm,"INFERENCE_LOCK",Path("relative.lock")),patch.object(llm.urllib.request,"urlopen") as call:
            with self.assertRaisesRegex(RuntimeError,"inference_lock_configuration_invalid"):
                llm.request_json([],{})
        call.assert_not_called()

    def test_lock_permission_failure_is_safe_and_never_calls_network(self):
        with patch.object(llm.os,"open",side_effect=PermissionError("secret filesystem path")),patch.object(llm.urllib.request,"urlopen") as call:
            with self.assertRaisesRegex(RuntimeError,"^inference_lock_unavailable$"):
                llm.request_json([],{})
        call.assert_not_called()
        self.assertFalse(llm._lock.locked())

    def test_lock_symlink_refused_without_network_or_target_change(self):
        target=self.lock_root/"target"
        target.write_text("unchanged")
        lock=self.lock_root/"symlink.lock"
        lock.symlink_to(target)
        with patch.object(llm,"INFERENCE_LOCK",lock),patch.object(llm.urllib.request,"urlopen") as call:
            with self.assertRaisesRegex(RuntimeError,"inference_lock_unavailable"):
                llm.request_json([],{})
        call.assert_not_called()
        self.assertEqual(target.read_text(),"unchanged")

    def test_lock_directory_creation_bounded_and_private_parent_required(self):
        too_deep=self.lock_root/"one"/"two"/"three"/"four"/"lock"
        with patch.object(llm,"INFERENCE_LOCK",too_deep):
            with self.assertRaisesRegex(RuntimeError,"inference_lock_unavailable"):
                llm._open_inference_lease()
        self.assertFalse((self.lock_root/"one").exists())
        public=self.lock_root/"public"
        public.mkdir(mode=0o755)
        with patch.object(llm,"INFERENCE_LOCK",public/"lock"),patch.object(llm.urllib.request,"urlopen") as call:
            with self.assertRaisesRegex(RuntimeError,"inference_lock_unavailable"):
                llm.request_json([],{})
        call.assert_not_called()
        self.assertFalse((public/"lock").exists())

    def test_fifo_lock_fails_promptly_before_network(self):
        import subprocess
        import sys
        import time
        lock=self.lock_root/"fifo.lock"
        os.mkfifo(lock,0o600)
        # Subprocess timeout guards the regression itself against a blocking open.
        script=("from pathlib import Path; from unittest.mock import patch; "
                "from workbench import llm; import sys; llm.INFERENCE_LOCK=Path(sys.argv[1]); "
                "network=patch.object(llm.urllib.request,'urlopen'); call=network.start(); "
                "\ntry: llm.request_json([],{})"
                "\nexcept RuntimeError as error: assert str(error)=='inference_lock_unavailable'"
                "\nelse: raise AssertionError('FIFO lease accepted')"
                "\nassert not call.called")
        started=time.monotonic()
        result=subprocess.run([sys.executable,"-c",script,str(lock)],capture_output=True,text=True,timeout=3)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertLess(time.monotonic()-started,3)
        self.assertTrue(stat.S_ISFIFO(lock.stat().st_mode))

    def test_timeout_latches_and_prevents_duplicate_request(self):
        original=llm._disabled_reason;llm._disabled_reason=None
        try:
            with patch.object(llm.urllib.request,"urlopen",side_effect=TimeoutError("test")) as call:
                with self.assertRaises(TimeoutError):llm.request_json([],{})
                with self.assertRaisesRegex(RuntimeError,"inference_disabled"):llm.request_json([],{})
                self.assertEqual(call.call_count,1)
        finally:llm._disabled_reason=original
if __name__=="__main__":unittest.main()
