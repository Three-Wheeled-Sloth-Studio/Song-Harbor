"""Editorial catalogue of third-party SFZ packs.

These entries are not bundled or automatically downloaded. Users choose the
publisher's download, review the terms, then explicitly import local files.
Versioned official release asset URLs were checked on 2026-11-04.
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
        "id": "vsco2", "name": "VSCO 2 Community Edition",
        "family": "Orchestra", "priority": 5, "fit": "Starter essentials",
        "description": "Chamber strings, brass, woodwinds and orchestral percussion with sampled articulations.",
        "source": "Versilian Studios", "license": "CC0-1.0", "version": "1.1.0",
        "approx_mb": None, "status": "Import/render not yet QA-tested; some SFZ directives may require an importer upgrade",
        "source_page": "https://versilian-studios.com/vsco-community/",
        "download_url": "https://github.com/sgossner/VSCO-2-CE/releases/tag/1.1.0",
    },
]


def curated_catalogue() -> list[dict]:
    return [dict(entry) for entry in CURATED_SFZ]
