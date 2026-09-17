import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(__file__))
from manifest import MANIFEST
import pdfplumber

KEYWORDS = ["Quarterly", "Rankings", "Standings", "Breed", "Group", "Obedience",
            "Rally", "Agility", "Junior", "High Point", "Top Ten", "Top 10", "Conformation"]

outdir = "pdfs"
results = []
for label, fname, url, note in MANIFEST:
    path = os.path.join(outdir, fname)
    if not os.path.exists(path):
        results.append({"label": label, "file": fname, "error": "missing file"})
        continue
    bytes_ = os.path.getsize(path)
    entry = {"label": label, "file": fname, "url": url, "bytes": bytes_, "note": note}
    t0 = time.time()
    try:
        with pdfplumber.open(path) as pdf:
            npages = len(pdf.pages)
            entry["pages"] = npages
            page_texts = {}
            any_text = False
            kw_pages = {k: [] for k in KEYWORDS}
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    txt = page.extract_text() or ""
                except Exception as e:
                    txt = ""
                if txt.strip():
                    any_text = True
                page_texts[i] = txt
                for kw in KEYWORDS:
                    if re.search(re.escape(kw), txt, re.IGNORECASE):
                        kw_pages[kw].append(i)
            entry["text_extractable"] = any_text
            entry["keyword_pages"] = kw_pages
            # save full extracted text for later grep (compact)
            full_text_path = os.path.join("extracted_text", fname.replace(".pdf", ".txt"))
            os.makedirs("extracted_text", exist_ok=True)
            with open(full_text_path, "w") as f:
                for i in range(1, npages+1):
                    f.write(f"\n=== PAGE {i} ===\n")
                    f.write(page_texts.get(i, ""))
    except Exception as e:
        entry["error"] = str(e)
    entry["elapsed_sec"] = round(time.time() - t0, 1)
    results.append(entry)
    print(label, entry.get("pages"), entry.get("text_extractable"), entry.get("elapsed_sec"))

json.dump(results, open("analysis.json", "w"), indent=2)
