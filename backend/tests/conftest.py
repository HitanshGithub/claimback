import os
import tempfile

# must run before claimback is imported: settings are read at import time
os.environ["CLAIMBACK_STEP_DELAY"] = "0"
os.environ["CLAIMBACK_LLM"] = "offline"
os.environ["CLAIMBACK_STORAGE"] = "local"
os.environ["CLAIMBACK_LOCAL_STORE"] = tempfile.mkdtemp(prefix="claimback-test-")
