import { useEffect, useMemo, useState } from "react";
import { Button, EditableTitle, IconButton, Menu } from "@tws-ui/core/react";

type Song = {id: string; legacy_job_id: string; title: string; imported_filename: string;
  created_at: number; version_count: number};
type Collection = {id: string; parent_id: string | null; title: string;
  sort_order: number; song_count: number};
type LibraryIndex = {songs: Song[]; collections: Collection[]};
const ROOT = "/api/library";

export function LibraryHome({onOpenSong, onImport}: {
  onOpenSong: (legacyId: string) => void;
  onImport: () => void;
}) {
  const [songs, setSongs] = useState<Song[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [newCollection, setNewCollection] = useState(false);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const response = await fetch(ROOT);
    if (!response.ok) throw new Error("Library is unavailable. Reopen Song Harbor to reconnect.");
    const result = await response.json() as LibraryIndex;
    setSongs(result.songs);
    setCollections(result.collections);
  }

  useEffect(() => { void refresh().catch(e => setError(String(e))); }, []);

  const visible = useMemo(() => songs.filter(song => {
    const text = (song.title + " " + song.imported_filename).toLowerCase();
    return text.includes(search.trim().toLowerCase());
  }), [songs, search]);
  const [members, setMembers] = useState<string[]>([]);
  useEffect(() => {
    if (!collection) {setMembers([]);return;}
    let active = true;
    void fetch(ROOT + "?collection_id=" + encodeURIComponent(collection))
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: LibraryIndex) => {if(active)setMembers(data.songs.map(x => x.id));})
      .catch(() => {if(active)setMembers([]);});
    return () => {active=false;};
  }, [collection, songs]);
  const displayed = collection ? visible.filter(song => members.includes(song.id)) : visible;

  async function rename(id: string, title: string) {
    setBusy(true); setError("");
    try {
      const response = await fetch(ROOT + "/songs/" + id, {
        method: "PATCH", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({title}),
      });
      if (!response.ok) {
        const result = await response.json() as {detail?: string};
        throw new Error(result.detail || "Rename failed");
      }
      await refresh();
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
    finally {setBusy(false);}
  }

  async function createCollection() {
    if (!newName.trim()) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(ROOT + "/collections", {
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({title:newName.trim(),parent_id:collection}),
      });
      if (!response.ok) throw new Error("Unable to create collection");
      setNewCollection(false); setNewName("");
      await refresh();
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
    finally {setBusy(false);}
  }

  async function assign(id: string, collectionId: string) {
    setBusy(true);setError("");
    try {
      const response = await fetch(ROOT + "/collections/" + collectionId + "/songs", {
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({song_id:id}),
      });
      if (!response.ok) throw new Error("Could not add song to collection");
      await refresh();
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
    finally {setBusy(false);}
  }

  function childrenOf(parent: string | null, depth = 0): React.ReactNode {
    return collections.filter(c => c.parent_id === parent).map(c =>
      <div key={c.id}>
        <button className={"lib-folder" + (collection === c.id ? " active" : "")}
          style={{paddingLeft: 9 + depth * 13}} title={c.title} onClick={() => setCollection(c.id)}>
          <span aria-hidden="true">▸</span><span>{c.title}</span>
          <small>{c.song_count}</small>
        </button>
        {depth < 5 && childrenOf(c.id, depth + 1)}
      </div>);
  }

  return <main className="library-home">
    <aside className="lib-sidebar" aria-label="Collections">
      <div className="lib-section-head">
        <span>COLLECTIONS</span>
        <IconButton icon="+" label="New collection" onClick={() => setNewCollection(v => !v)} />
      </div>
      <button className={"lib-folder" + (!collection ? " active" : "")}
        onClick={() => setCollection(null)}><span aria-hidden="true">♫</span>
        <span>All songs</span><small>{songs.length}</small></button>
      {childrenOf(null)}
      {newCollection && <form className="lib-new-folder" onSubmit={e => {e.preventDefault();void createCollection();}}>
        <input autoFocus value={newName} aria-label="New collection name" maxLength={120}
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => {if(e.key==="Escape"){setNewCollection(false);setNewName("");}}}/>
        <IconButton icon="✓" label="Create collection" disabled={busy} onClick={() => {void createCollection();}}/>
      </form>}
    </aside>
    <section className="lib-content">
      <div className="lib-topline">
        <h1>Library</h1>
        <div className="lib-actions">
          <input type="search" aria-label="Search songs" placeholder="Search songs"
            value={search} onChange={e => setSearch(e.target.value)}/>
          <IconButton icon="＋" label="Import song" onClick={onImport}/>
        </div>
      </div>
      <div className="lib-table-head"><span>SONG</span><span>VERSIONS</span><span>ACTIONS</span></div>
      <div className="lib-rows" role="list">
        {displayed.map(song =>
          <div role="listitem" key={song.id} className={"lib-song" + (selected === song.id?" selected":"")}
            onClick={() => setSelected(song.id)}
            onDoubleClick={() => onOpenSong(song.legacy_job_id)}>
            <div className="lib-song-main">
              <EditableTitle value={song.title} label={"Rename " + song.title}
                disabled={busy} onCommit={title => {void rename(song.id,title);}}/>
              <small title={song.imported_filename}>{song.imported_filename}</small>
            </div>
            <span className="lib-song-count">{song.version_count}</span>
            <div className="lib-song-actions">
              <IconButton icon="▶" label={"Open " + song.title}
                onClick={e => {e.stopPropagation();onOpenSong(song.legacy_job_id);}}/>
              <Menu label={"Actions for " + song.title} trigger={<button className="lib-kebab"
                aria-label={"Options for " + song.title} title="More actions">⋯</button>}
                items={[
                  {id:"open",label:"Open",onSelect:()=>onOpenSong(song.legacy_job_id)},
                  ...collections.map(folder => ({id:folder.id,label:"Add to " + folder.title,
                    onSelect:()=>{void assign(song.id,folder.id);}})),
                  {id:"help",label:"Help",onSelect:()=>window.open(
                    "https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/blob/main/docs/library-first-architecture.md",
                    "_blank","noopener,noreferrer")},
                ]}/>
            </div>
          </div>)}
      </div>
      {displayed.length === 0 && <div className="lib-empty">
        {songs.length ? "No matching songs." : "Your library is empty."}
        {!songs.length && <Button variant="primary" onClick={onImport}>Import song</Button>}
      </div>}
      {error && <p role="alert" className="error-message">{error}</p>}
    </section>
  </main>;
}
