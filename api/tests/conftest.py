import os
import tempfile

# Tests run against an empty store → the digest uses synthetic fixtures (deterministic, offline).
os.environ["FINN_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
