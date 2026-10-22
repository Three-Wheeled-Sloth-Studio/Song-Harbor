"""Exit endpoint safety: the desktop X may only stop its own local backend."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import Request,HTTPException
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

TOKEN="x"*24

def req(origin=""):
    headers=[(b"origin",origin.encode())] if origin else []
    return Request({"type":"http","headers":headers})

class QuitSafetyTests(unittest.TestCase):
    def test_quit_schedules_only_current_instance(self):
        with patch.dict(os.environ,{"SONG_HARBOR_INSTANCE_TOKEN":TOKEN}),\
             patch.object(server,"runtime_status",return_value={"busy":False}),\
             patch.object(server.threading,"Thread") as thread:
            result=server.close_song_harbor(server.QuitRequest(instance_token=TOKEN),req())
            self.assertEqual(result["status"],"closing")
            thread.return_value.start.assert_called_once()
    def test_rejects_foreign_instance(self):
        with patch.dict(os.environ,{"SONG_HARBOR_INSTANCE_TOKEN":TOKEN}):
            with self.assertRaises(HTTPException) as err:
                server.close_song_harbor(server.QuitRequest(instance_token="y"*24),req())
            self.assertEqual(err.exception.status_code,403)
    def test_rejects_active_job(self):
        with patch.dict(os.environ,{"SONG_HARBOR_INSTANCE_TOKEN":TOKEN}),\
             patch.object(server,"runtime_status",return_value={"busy":True}):
            with self.assertRaises(HTTPException) as err:
                server.close_song_harbor(server.QuitRequest(instance_token=TOKEN),req())
            self.assertEqual(err.exception.status_code,409)
    def test_rejects_foreign_origin(self):
        with patch.dict(os.environ,{"SONG_HARBOR_INSTANCE_TOKEN":TOKEN}):
            with self.assertRaises(HTTPException) as err:
                server.close_song_harbor(server.QuitRequest(instance_token=TOKEN),
                                          req("https://example.com"))
            self.assertEqual(err.exception.status_code,403)

if __name__=="__main__":
    unittest.main()
