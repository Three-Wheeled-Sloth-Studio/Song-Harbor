import asyncio
import io
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import Request, UploadFile
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import projects
import stem_import
import library
import server


class ImportTracksTests(unittest.TestCase):
    def test_suggests_shared_filename_prefix(self):
        files=["Salt in the Circuit - Vocals.wav","Salt in the Circuit - Drums.mp3",
               "Salt in the Circuit - Bass.flac","Salt in the Circuit - Guitar.wav"]
        self.assertEqual(stem_import.guess_song_title(files),"Salt in the Circuit")
        self.assertEqual(stem_import.guess_song_title(["vocals.wav","drums.wav"]),"Imported song")
        self.assertEqual(stem_import.guess_song_title(["Some Piece - Vocals.wav","Different Piece - Drums.wav"]),"Imported song")

    def test_assigns_standard_and_extra_stems_without_collisions(self):
        stems=stem_import.assign_tracks(["demo vocals.wav","demo drums.wav","strings.wav",
                                         "synth.wav","chorus vocals.wav"])
        self.assertEqual([x["stem_alias"] for x in stems],
                         ["Vocals","Drums","Track01","Track02","Track03"])

    def test_recognizes_demucs_parenthesized_stems(self):
        names=["Song_(Vocals)_htdemucs_6s.wav","Song_(Drums)_htdemucs_6s.wav",
               "Song_(Guitar)_htdemucs_6s.wav","Song Guitarist Strings.wav"]
        self.assertEqual([item["stem_alias"] for item in stem_import.assign_tracks(names)],
                         ["Vocals","Drums","Guitar","Track01"])

    def test_import_endpoint_preserves_title_override_and_converts_tracks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            uploads=[UploadFile(filename="A Song - Vocals.mp3",file=io.BytesIO(b"VOCAL")),
                     UploadFile(filename="A Song - Drums.wav",file=io.BytesIO(b"DRUMS"))]
            request=Request({"type":"http","headers":[]})
            with patch.object(server,"DATA_ROOT",root),patch.object(server.dependencies,"resolve",return_value={"directory":str(root)}),patch.object(server,"run_track_import",lambda *args:None):
                job=asyncio.run(server.import_tracks(request,uploads,title="My override"))
            self.assertEqual(job["filename"],"My override.wav")
            self.assertEqual(job["status"],"queued")
            folder=root/"jobs"/job["id"]
            self.assertEqual((folder/"originals"/"A Song - Vocals.mp3").read_bytes(),b"VOCAL")
            self.assertEqual((folder/"originals"/"A Song - Drums.wav").read_bytes(),b"DRUMS")
            real_job=server.jobs.pop(job["id"])
            def fake_convert(command,**kwargs):
                Path(command[-1]).write_bytes(b"converted audio")
                return SimpleNamespace(returncode=0,stderr="")
            with patch.object(server,"DATA_ROOT",root),patch.object(server,"probe_duration",return_value=12.5),patch.object(server,"dependency_tool",return_value="ffmpeg"),patch.object(server.subprocess,"run",side_effect=fake_convert):
                server.run_track_import(real_job,["A Song - Vocals.mp3","A Song - Drums.wav"],"My override")
            self.assertEqual(real_job["status"],"complete")
            record=projects.read_project(root,job["id"])
            self.assertEqual(record["title"],"My override")
            self.assertEqual(record["source_duration_seconds"],12.5)
            self.assertEqual(record["files"],["01 (Vocals).wav","02 (Drums).wav"])
            self.assertTrue((folder/"stems"/"02 (Drums).wav").is_file())

    def test_imported_project_is_discoverable_and_daw_exportable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            ident="abcdef123456"
            folder=root/"jobs"/ident
            (folder/"stems").mkdir(parents=True)
            (folder/"originals").mkdir()
            original=folder/"originals"/"Song Vocals.wav"
            original.write_bytes(b"original unchanged")
            files=["01 (Vocals).wav","02 (Track01).wav"]
            for name in files:(folder/"stems"/name).write_bytes(b"mock wav")
            record={"version":projects.PROJECT_VERSION,"id":ident,"filename":"Song.wav",
                    "title":"Song","source_filename":original.name,"created_at":123,
                    "model":"imported tracks","imported_tracks":True,"files":files,
                    "source_tracks":[{"original_filename":"Song Vocals.wav","working_filename":files[0],"stem_alias":"Vocals"},
                                     {"original_filename":"Strings.wav","working_filename":files[1],"stem_alias":"Track01"}],
                    "stems":projects.default_settings(files),"source_duration_seconds":15}
            projects.write_project(root,record)
            self.assertEqual([p["id"] for p in projects.list_projects(root)],[ident])
            self.assertEqual([p.name for p in projects.validated_stems(record,folder)],files)
            bundle=projects.export_daw(root,record,"waveform")
            self.assertTrue((bundle/"01 - Vocals.wav").is_file())
            self.assertTrue((bundle/"02 - Track01.wav").is_file())
            self.assertIn('"track_count": 2',(bundle/"manifest.json").read_text())
            library.adopt_jobs(root)
            self.assertEqual(len(library.list_songs(root)),1)


if __name__=="__main__":
    unittest.main()
