"""Company fundamentals for Pull: annual reports + concall transcripts (primary sources only).

To build in the Pull phase:
  - fetch_documents(ticker) → document links from screener.in/company/<TICKER>/ (Documents section)
  - download + text-extract PDFs (page numbers preserved for citations), cache on disk by URL hash
  - multi-year financial tables from screener.in for the trajectory / balance-sheet sections
"""
