CURATED = ["Segoe UI", "Arial", "Verdana", "Tahoma", "Calibri", "Consolas", "Georgia"]


def caption_fonts(system_families):
    available = {f for f in system_families if not f.startswith("@")}
    curated = [f for f in CURATED if f in available]
    return curated + sorted(available - set(curated), key=str.lower)
