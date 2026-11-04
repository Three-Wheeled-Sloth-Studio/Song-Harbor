"""Editorial catalogue of third-party SFZ packs.

These entries are not bundled or automatically downloaded. Users choose the
publisher's download, review the terms, then explicitly import local files.
Versioned official release asset URLs were checked on 2026-11-04.
VSCO 2 CE is intentionally deferred: its 2.3-GB archive exceeds the 768-MB
Song Harbor SFZ ZIP import limit.
"""

CURATED_SFZ = [
    {
        "id": "bigcat-cello", "name": "Karoryfer x Bigcat Cello",
        "family": "Strings", "priority": 1, "fit": "Infra Choir",
        "description": "Expressive solo cello for dark counterpoint, sustained lines and plucked accents.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.001",
        "approx_mb": 133, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer-bigcat.cello",
        "download_url": "https://github.com/sfzinstruments/karoryfer-bigcat.cello/releases/download/v1.001/Karoryfer_Bigcat_cello.v1.001.zip",
    },
    {
        "id": "growlybass", "name": "Karoryfer Growlybass",
        "family": "Bass", "priority": 2, "fit": "Infra Choir",
        "description": "Multisampled electric bass with dirty, aggressive and short articulations.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.002",
        "approx_mb": 167, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer.growlybass",
        "download_url": "https://github.com/sfzinstruments/karoryfer.growlybass/releases/download/v1.002/Karoryfer.Growlybass.v1.002.zip",
    },
    {
        "id": "bear-sax", "name": "Karoryfer Bear Sax",
        "family": "Brass/Reeds", "priority": 3, "fit": "Infra Choir",
        "description": "Vintage baritone sax growls, subtone and staccato for neo-swing and industrial brass lines.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.004",
        "approx_mb": 132, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer.bear-sax",
        "download_url": "https://github.com/sfzinstruments/karoryfer.bear-sax/releases/download/v1.004/Karoryfer.Bear_Sax.v1.004.zip",
    },
    {
        "id": "big-rusty-drums", "name": "Karoryfer Big Rusty Drums",
        "family": "Drums", "priority": 4, "fit": "Infra Choir",
        "description": "Characterful acoustic kit for industrial layers, aggressive kicks and snare textures.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.100",
        "approx_mb": 620, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer.big-rusty-drums",
        "download_url": "https://github.com/sfzinstruments/karoryfer.big-rusty-drums/releases/download/v1.100/Big_Rusty_Drums_1100.zip",
    },
    {
        "id": "string-cyborgs", "name": "Karoryfer String Cyborgs",
        "family": "Experimental strings", "priority": 5, "fit": "Infra Choir",
        "description": "Looped bowed strings shaped into haunting synthetic textures and evolving drones.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.001",
        "approx_mb": 64, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer.string-cyborgs",
        "download_url": "https://github.com/sfzinstruments/karoryfer.string-cyborgs/releases/download/v1.001/Karoryfer.String_Cyborgs.v1.001.zip",
    },
    {
        "id": "war-tuba", "name": "Karoryfer War Tuba",
        "family": "Low brass", "priority": 6, "fit": "Infra Choir",
        "description": "Raucous tuba articulations for marches, gothic brass hits and offbeat bass figures.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.002",
        "approx_mb": 109, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer.war-tuba",
        "download_url": "https://github.com/sfzinstruments/karoryfer.war-tuba/releases/download/v1.002/Karoryfer_War_Tuba_v1002.zip",
    },
    {
        "id": "caveman-cosmonaut", "name": "Karoryfer Caveman Cosmonaut",
        "family": "Vintage keys", "priority": 7, "fit": "Infra Choir",
        "description": "Characterful Polish analog keyboard tones for industrial hooks and ghostly interludes.",
        "source": "Karoryfer Samples", "license": "CC0-1.0", "version": "1.001",
        "approx_mb": 98, "status": "Import/render not yet QA-tested",
        "source_page": "https://github.com/sfzinstruments/karoryfer.caveman-cosmonaut",
        "download_url": "https://github.com/sfzinstruments/karoryfer.caveman-cosmonaut/releases/download/v1.001/Karoryfer.Caveman_Cosmonaut.v1.001.zip",
    },

]


def curated_catalogue(installed_packs: list[dict] | None = None) -> list[dict]:
    """Filter installed packs; use stable IDs when available and legacy names otherwise."""
    import re
    def normalized(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.casefold())
    installed_ids = {p.get("curated_id") for p in (installed_packs or [])}
    installed_names = {normalized(str(p.get("name", ""))) for p in (installed_packs or [])}
    return [
        dict(entry) for entry in CURATED_SFZ
        if entry["id"] not in installed_ids and
           normalized(entry["name"]) not in installed_names and
           not any(
               normalized(entry["id"]) in name
               for name in installed_names
               if len(normalized(entry["id"])) >= 6
           )
    ]
